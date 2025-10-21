#!/usr/bin/env python3
"""
ransom_live_pull.py

Fetch ransomware.live recentvictims, filter US in last N days... export a single CSV named:
  ransom_live_pull_YYYYMMDD.csv (America/Chicago local date)

Usage:
  python3 ransom_live_pull.py            # writes ransom_live_pull_YYYYMMDD.csv in cwd
  python3 ransom_live_pull.py --days 7   # last 7 days
  python3 ransom_live_pull.py --out-dir ./exports

Requires: requests beautifulsoup4 dateutil 
####pip install requests python-dateutil beautifulsoup4####
"""
from __future__ import annotations
import requests
import csv
import argparse
import time
import os
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from typing import Optional

API_RECENT = "https://api.ransomware.live/v2/recentvictims"
HEADERS = {"User-Agent": "ransom_live_pull/1.0"}

CSV_FIELDS = [
    "id_base64",
    "victim",
    "domain",
    "country",
    "group",
    "activity",
    "attackdate",
    "discovered",
    "description",
    "claim_url",
    "detail_url",
    "screenshot_url",
    "press_urls",
    "duplicates_count",
]

# shitty date parser: try try try again 
def parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    # handles "2025-10-13 13:17:14.652100" and "2025-10-13T13:17:14"
    try:
        # handle Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # API datetimes without tz are UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    # try common formats
    fmts = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

def extract_id_from_detail_url(url: str) -> str:
    if not url:
        return ""
    try:
        return url.rstrip("/").split("/")[-1]
    except Exception:
        return ""
        # fuck thats a lot of shit just for time 
def flatten_record(rec: dict) -> dict:
    out = {}
    out["id_base64"] = extract_id_from_detail_url(rec.get("url", "") or "")
    out["victim"] = rec.get("victim") or ""
    out["domain"] = rec.get("domain") or ""
    out["country"] = rec.get("country") or ""
    out["group"] = rec.get("group") or ""
    out["activity"] = rec.get("activity") or ""
    out["attackdate"] = rec.get("attackdate") or ""
    out["discovered"] = rec.get("discovered") or ""
    out["description"] = rec.get("description") or ""
    out["claim_url"] = rec.get("claim_url") or ""
    out["detail_url"] = rec.get("url") or ""
    out["screenshot_url"] = rec.get("screenshot") or ""
    press = rec.get("press")
    if press is None:
        out["press_urls"] = ""
    elif isinstance(press, list):
        out["press_urls"] = "|".join([p for p in press if isinstance(p, str)])
    else:
        out["press_urls"] = str(press)
    out["duplicates_count"] = len(rec.get("duplicates", []) or [])
    return out

def fetch_recent() -> list:
    r = requests.get(API_RECENT, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError("Unexpected response shape from API")
    return data

def get_chicago_date_str(ts: Optional[datetime] = None) -> str:
    if ZoneInfo:
        tz = ZoneInfo("America/Chicago")
        now = (ts or datetime.now(timezone.utc)).astimezone(tz)
    else:
        # fallback use UTC date if shits too fucked 
        now = (ts or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return now.strftime("%Y%m%d")

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=14, help="lookback window in days")
    p.add_argument("--out-dir", default=".", help="output directory (default cwd)")
    p.add_argument("--out", default=None, help="explicit output filename (overrides auto-name)")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    if args.verbose:
        print("Cutoff (UTC):", cutoff.isoformat())

    recs = fetch_recent()
    if args.verbose:
        print("Total records fetched:", len(recs))

    filtered = []
    for rec in recs:
        country = (rec.get("country") or "").upper()
        if country not in ("US", "UNITED STATES", "USA"):
            continue
        date_s = rec.get("discovered") or rec.get("attackdate") or rec.get("date")
        dt = parse_date(date_s)
        if not dt:
            continue
        if dt < cutoff:
            continue
        filtered.append(rec)

    # sort oldest to newest by discovered/attackdate
    filtered.sort(key=lambda r: parse_date(r.get("discovered") or r.get("attackdate") or "") or datetime.max.replace(tzinfo=timezone.utc))

    # prepare output file path
    os.makedirs(args.out_dir, exist_ok=True)
    if args.out:
        out_path = os.path.join(args.out_dir, args.out)
    else:
        date_str = get_chicago_date_str()
        filename = f"ransom_live_pull_{date_str}.csv"
        out_path = os.path.join(args.out_dir, filename)

    # write CSV 
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in filtered:
            writer.writerow(flatten_record(rec))

    print(f"Wrote {len(filtered)} records to {out_path}")

if __name__ == "__main__":
    main()

