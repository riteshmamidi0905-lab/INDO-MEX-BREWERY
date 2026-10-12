#!/usr/bin/env python3
"""screen.py - deterministic screen of ONE job posting's text. Local only, no network.
Usage: python3 screen.py posting.txt [--status UNSET|us_citizen|permanent_resident|
        authorized_no_sponsorship_now_will_need_later|needs_sponsorship_now] [--json]
It reports what the posting SAYS about authorization/location/clearance and what that means for
the stated status. It never guesses the status: UNSET => authorization_fit=UNKNOWN.
Regex screening misses nuance; always read the posting's own words (quoted in 'evidence')."""
import argparse, json, re, sys

NO_SPONSOR = [r"(?:will|does|do) not (?:provide|offer|sponsor)[^.]{0,40}(?:sponsorship|visa)", r"unable to sponsor", r"no (?:visa )?sponsorship",
              r"without (?:the need for )?(?:current or future )?(?:visa )?sponsorship", r"not (?:able|eligible) to sponsor", r"cannot (?:offer|provide) sponsorship"]
CITIZEN_ONLY = [r"u\.?s\.? citizens? only", r"must be a u\.?s\.? citizen", r"citizenship (?:is )?required", r"itar", r"export[- ]control"]
CLEARANCE = [r"(?:secret|top secret|ts/sci|public trust) (?:security )?clearance", r"active (?:security )?clearance", r"security clearance (?:is )?required"]
SPONSOR_OK = [r"(?:will|can|do|does) (?:provide|offer|consider)[^.]{0,30}(?:visa )?sponsorship", r"visa sponsorship (?:is )?available", r"h-?1b (?:sponsorship )?(?:available|supported)", r"sponsorship (?:is )?(?:available|provided)"]
AUTH_REQ = [r"authorized to work in the (?:u\.?s\.?|united states)", r"legally authorized to work", r"eligible to work in the (?:u\.?s\.?|united states)"]
US_LOC = r"\b(?:united states|u\.?s\.?a?\.?|remote[- ](?:us|usa|u\.s\.)|us[- ]remote|new york|san francisco|austin|seattle|boston|chicago|los angeles|denver|atlanta|texas|california|washington,? d\.?c\.?)\b"
NON_US = r"\b(?:london|toronto|canada|india|bangalore|berlin|dublin|singapore|emea|apac|united kingdom|europe)\b"

def hits(pats, t):
    out = []
    for p in pats:
        for m in re.finditer(p, t, re.I):
            s = max(0, m.start() - 60); out.append(t[s:m.end() + 60].replace("\n", " ").strip())
    return out[:3]

def screen(text, status="UNSET"):
    ev = {"no_sponsorship": hits(NO_SPONSOR, text), "citizen_only": hits(CITIZEN_ONLY, text),
          "clearance": hits(CLEARANCE, text), "sponsorship_offered": hits(SPONSOR_OK, text), "work_auth_required": hits(AUTH_REQ, text)}
    flags = sorted(k for k, v in ev.items() if v)
    if status == "UNSET":
        fit = "UNKNOWN"; why = "work_authorization is UNSET in profile; posting terms shown for you to judge"
    elif ev["clearance"] or ev["citizen_only"]:
        fit = "EXCLUDE" if status != "us_citizen" else ("CHECK" if ev["clearance"] else "OK"); why = "citizen-only / clearance language"
        if status == "us_citizen" and ev["clearance"]: why = "clearance required; confirm you hold one"
    elif status == "needs_sponsorship_now":
        fit = "EXCLUDE" if ev["no_sponsorship"] else ("OK" if ev["sponsorship_offered"] else "UNCLEAR"); why = "needs sponsorship now"
    elif status == "authorized_no_sponsorship_now_will_need_later":
        fit = "CAUTION" if ev["no_sponsorship"] else "OK"; why = "'no sponsorship' language may cover future sponsorship"
    elif status in ("us_citizen", "permanent_resident"):
        fit = "OK"; why = "no authorization barrier found"
    else:
        fit = "UNKNOWN"; why = "unrecognised status value"
    loc = "US" if re.search(US_LOC, text, re.I) and not re.search(NON_US, text, re.I) else ("NON-US?" if re.search(NON_US, text, re.I) else "UNCLEAR")
    if loc == "NON-US?" and fit != "UNKNOWN":
        fit, why = "EXCLUDE", "non-US location signal (this search is US-only)"
    return {"authorization_fit": fit, "reason": why, "flags": flags, "evidence": ev, "location_signal": loc}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("file", nargs="?", default="-"); ap.add_argument("--status", default="UNSET"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(); t = sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read()
    r = screen(t, a.status); print(json.dumps(r, indent=2) if a.json else f"authorization_fit={r['authorization_fit']} ({r['reason']}) flags={r['flags']} location={r['location_signal']}")
