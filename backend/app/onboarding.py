"""Config-driven onboarding: the same JSON drives the UI (rendered generically in the browser) and the
server-side validation below, so adding a discipline or a question is a config change, not new code."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from . import config

MIN_AGE = 16


@lru_cache(maxsize=1)
def load() -> dict:
    with open(config.ONBOARDING_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def _visible(field: dict, data: dict) -> bool:
    cond = field.get("showIf")
    if not cond:
        return True
    v = data.get(cond["field"])
    if "equals" in cond:
        return v == cond["equals"]
    if "in" in cond:
        return v in cond["in"]
    if "includes" in cond:
        return isinstance(v, list) and cond["includes"] in v
    return bool(v)


def _parse_date(v: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None


def _clean_value(field: dict, v: Any, data: dict) -> Tuple[Any, Optional[str]]:
    """Return (cleaned value, error). Empty values come back as None."""
    t = field["type"]
    if v in (None, "", []):
        return None, None
    opts = [o["value"] for o in field.get("options", [])]
    if t == "number":
        try:
            n = float(v)
        except (TypeError, ValueError):
            return None, "must be a number"
        if "min" in field and n < field["min"]:
            return None, f"must be at least {field['min']}"
        if "max" in field and n > field["max"]:
            return None, f"must be at most {field['max']}"
        return (int(n) if n.is_integer() else round(n, 2)), None
    if t in ("select", "radio", "cards"):
        v = str(v)
        return (v, None) if v in opts else (None, "is not one of the allowed options")
    if t == "multiselect":
        if not isinstance(v, list):
            return None, "must be a list"
        vals = []
        for x in v:
            if str(x) not in opts:
                return None, f"contains an unknown option '{x}'"
            if str(x) not in vals:
                vals.append(str(x))
        excl = field.get("excludeField")
        if excl:
            vals = [x for x in vals if x != data.get(excl)]
        if "maxItems" in field and len(vals) > field["maxItems"]:
            return None, f"choose at most {field['maxItems']}"
        return vals or None, None
    if t == "boolean":
        if not isinstance(v, bool):
            return None, "must be true or false"
        return v, None
    if t == "date":
        d = _parse_date(v)
        if not d:
            return None, "must be a valid date"
        if field.get("future") and d <= date.today():
            return None, "must be in the future"
        if field.get("maxWeeks") and d > date.today() + timedelta(weeks=field["maxWeeks"]):
            return None, f"must be within {field['maxWeeks']} weeks"
        return d.isoformat(), None
    if t in ("text", "textarea"):
        s = str(v).strip()
        if len(s) > field.get("maxLength", 500):
            return None, f"must be at most {field.get('maxLength', 500)} characters"
        if field.get("pattern") and s and not re.match(field["pattern"], s):
            return None, "has the wrong format"
        return s or None, None
    return None, "unsupported field"


def _fields_for(step: dict, data: dict, cfg: dict) -> List[Tuple[str, dict, dict]]:
    """(container key, field, container dict) for every field a step contains."""
    if step.get("dynamic") == "disciplines":
        out = []
        for d in data.get("disciplines") or []:
            for f in cfg["disciplines"].get(d, {}).get("fields", []):
                out.append((d, f, {}))
        return out
    return [("", f, {}) for f in step["fields"]]


def validate(raw: dict, complete: bool) -> Tuple[dict, Dict[str, str]]:
    """Clean a submitted profile against the config.

    complete=False (draft autosave): keep valid values, drop invalid ones, report errors.
    complete=True (finish onboarding): additionally enforce required fields and cross-field rules."""
    cfg = load()
    raw = raw if isinstance(raw, dict) else {}
    out: dict = {}
    errors: Dict[str, str] = {}
    # pass 1: flat fields in step order (later showIf conditions depend on earlier cleaned values)
    for step in cfg["steps"]:
        if step.get("dynamic"):
            continue
        for f in step["fields"]:
            if not _visible(f, out):
                continue
            val, err = _clean_value(f, raw.get(f["id"]), out)
            if err:
                errors[f["id"]] = f"{f['label']} {err}."
            elif val is None and f.get("required") and complete:
                errors[f["id"]] = f"{f['label']} is required."
            elif f.get("mustBeTrue") and complete and val is not True:
                errors[f["id"]] = "Please confirm to continue."
            if val is not None:
                out[f["id"]] = val
    # pass 2: per-discipline answers
    details_in = raw.get("disciplineDetails") if isinstance(raw.get("disciplineDetails"), dict) else {}
    details: dict = {}
    for d in out.get("disciplines") or []:
        answers = details_in.get(d) if isinstance(details_in.get(d), dict) else {}
        clean = {}
        for f in cfg["disciplines"].get(d, {}).get("fields", []):
            val, err = _clean_value(f, answers.get(f["id"]), answers)
            if err:
                errors[f"{d}.{f['id']}"] = f"{f['label']} {err}."
            elif val is not None:
                clean[f["id"]] = val
        if clean:
            details[d] = clean
    if details:
        out["disciplineDetails"] = details
    # cross-field rules
    dob = _parse_date(out.get("dateOfBirth")) if out.get("dateOfBirth") else None
    if dob:
        age = age_from_dob(dob)
        if age < MIN_AGE:
            errors["dateOfBirth"] = f"FitPulse is for people aged {MIN_AGE} and over."
            out.pop("dateOfBirth")
        elif age > 100:
            errors["dateOfBirth"] = "Please check your date of birth."
            out.pop("dateOfBirth")
    if out.get("preferredDays") and out.get("daysPerWeek") and len(out["preferredDays"]) < int(out["daysPerWeek"]) and complete:
        errors["preferredDays"] = "Pick at least as many preferred days as training days, or leave this blank."
    return out, errors


def age_from_dob(dob: date) -> int:
    t = date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))


def programme_weeks(profile: dict) -> Optional[float]:
    tl = profile.get("timeline")
    if tl is not None:
        tl = str(tl).strip()
    if tl in ("4", "8", "12", "16"):
        return float(tl)
    if tl == "custom" and profile.get("targetDate"):
        d = _parse_date(profile["targetDate"])
        if d:
            return round(max((d - date.today()).days, 7) / 7, 1)
    return None


def label(field_id: str, value: Any) -> Any:
    """Human label for an option value (used in summaries). Works for both top-level and discipline-specific fields."""
    cfg = load()
    fields = []
    for step in cfg["steps"]:
        for f in step.get("fields", []):
            if f.get("id") == field_id:
                fields.append(f)
    for meta in cfg.get("disciplines", {}).values():
        for f in meta.get("fields", []):
            if f.get("id") == field_id:
                fields.append(f)
    for field in fields:
        m = {str(o["value"]): o["label"] for o in field.get("options", [])}
        if isinstance(value, list):
            return [m.get(str(x), x) for x in value]
        return m.get(str(value), value)
    return value
