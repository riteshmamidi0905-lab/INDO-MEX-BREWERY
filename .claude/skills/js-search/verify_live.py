#!/usr/bin/env python3
"""verify_live.py - is a posting still open? Uses each ATS's PUBLIC posting endpoint (Greenhouse, Lever,
Ashby) or a plain page GET. One request per URL, 1s apart, identifies itself, no login, no scraping of
LinkedIn (LinkedIn URLs are refused). Needs open outbound HTTPS: it does NOT work inside the Claude cloud
sandbox (egress policy blocks these hosts); run it on your own machine.
Usage: python3 verify_live.py URL [URL...]   -> OPEN | CLOSED | UNKNOWN per URL, with the reason."""
import json, re, sys, time, urllib.error, urllib.request
UA = {"User-Agent": "job-liveness-check/1.0 (personal use)"}
CLOSED_WORDS = re.compile(r"no longer (?:available|accepting|open)|position (?:has been )?(?:filled|closed)|job (?:is )?(?:closed|expired)|this posting has been removed|page not found", re.I)

def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)

def check(url, get=fetch):
    if "linkedin.com" in url:
        return "UNKNOWN", "LinkedIn is not checked (platform rules); open it yourself"
    m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)", url) or re.search(r"greenhouse\.io/.*?[?&]for=([\w-]+).*?token=(\d+)", url)
    if m:
        s, b = get(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}")
        return ("OPEN", "greenhouse API 200") if s == 200 else ("CLOSED", "greenhouse API 404") if s == 404 else ("UNKNOWN", f"status {s}")
    m = re.search(r"jobs\.lever\.co/([\w-]+)/([0-9a-f-]{36})", url)
    if m:
        s, b = get(f"https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}")
        return ("OPEN", "lever API 200") if s == 200 else ("CLOSED", "lever API 404") if s == 404 else ("UNKNOWN", f"status {s}")
    m = re.search(r"jobs\.ashbyhq\.com/([\w.-]+)/([0-9a-f-]{36})", url)
    if m:
        s, b = get(f"https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}")
        if s != 200: return "UNKNOWN", f"status {s}"
        ids = {j.get("id") for j in json.loads(b).get("jobs", [])}
        return ("OPEN", "listed on ashby board") if m.group(2) in ids else ("CLOSED", "not on ashby board")
    s, b = get(url)
    if s is None: return "UNKNOWN", b
    if s in (404, 410): return "CLOSED", f"HTTP {s}"
    if s == 200: return ("CLOSED", "page says closed") if CLOSED_WORDS.search(b) else ("UNKNOWN", "page loads; no closed text found (not proof it is open)")
    return "UNKNOWN", f"HTTP {s}"

if __name__ == "__main__":
    for u in sys.argv[1:]:
        st, why = check(u); print(f"{st}\t{u}\t{why}"); time.sleep(1)
