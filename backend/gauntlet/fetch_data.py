"""One-shot real-data fetcher. The ONLY module that touches the network.

Downloads into data/real/ and never runs at sim time:
- Open-Meteo previous-runs API: shortwave radiation as forecast ONE DAY AHEAD
  (what a day-ahead trader actually had) per park location.
- Open-Meteo archive API: shortwave radiation that actually happened.
- SMARD public JSON API: German day-ahead prices (DE-LU), hourly.

Auto mode scans a recent window and picks two days:
- sunny: high actual radiation, small forecast error (base for S2/S3)
- cloudy: largest real day-ahead forecast bust over Munich (makes S1 real)

Usage:
  python -m gauntlet.fetch_data --auto
  python -m gauntlet.fetch_data --sunny 2026-06-03 --cloudy 2026-05-27
"""

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import requests

from .config import PARKS

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DIR = REPO_ROOT / "data" / "real"

PREVRUNS = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
SMARD_INDEX = "https://www.smard.de/app/chart_data/4169/DE/index_hour.json"
SMARD_DATA = "https://www.smard.de/app/chart_data/4169/DE/4169_DE_hour_{ts}.json"
TZ_PARAM = "Europe/Berlin"  # UTC+2 in summer, matches the sim's fixed CEST


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_radiation(lat: float, lon: float, start: str, end: str) -> tuple[list, list]:
    """Returns (forecast_day_ahead, actual) hourly W/m2 lists for [start, end]."""
    fc = _get(PREVRUNS, {
        "latitude": lat, "longitude": lon, "timezone": TZ_PARAM,
        "start_date": start, "end_date": end,
        "hourly": "shortwave_radiation_previous_day1",
    })["hourly"]["shortwave_radiation_previous_day1"]
    ac = _get(ARCHIVE, {
        "latitude": lat, "longitude": lon, "timezone": TZ_PARAM,
        "start_date": start, "end_date": end,
        "hourly": "shortwave_radiation",
    })["hourly"]["shortwave_radiation"]
    clean = lambda xs: [0.0 if x is None else float(x) for x in xs]
    return clean(fc), clean(ac)


def scan_days(start: dt.date, end: dt.date) -> tuple[str, str, list]:
    """Pick (sunny_day, cloudy_day) from the window using Munich + Zaragoza."""
    days = [(start + dt.timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    mun = PARKS["munich"]
    zar = PARKS["zaragoza"]
    fc_m, ac_m = fetch_radiation(mun["lat"], mun["lon"], days[0], days[-1])
    fc_z, ac_z = fetch_radiation(zar["lat"], zar["lon"], days[0], days[-1])
    report = []
    for i, day in enumerate(days):
        sl = slice(24 * i, 24 * (i + 1))
        fm, am = np.array(fc_m[sl]), np.array(ac_m[sl])
        fz, az = np.array(fc_z[sl]), np.array(ac_z[sl])
        bust = float(np.sum(np.clip(fm - am, 0, None)))  # over-forecast over Munich, W/m2*h
        err = float(np.sum(np.abs(fm - am)) + np.sum(np.abs(fz - az)))
        sun = float(np.sum(am) + np.sum(az))
        report.append({"day": day, "munich_bust": round(bust), "abs_err": round(err), "sun": round(sun)})
    cloudy = max(report, key=lambda r: r["munich_bust"])["day"]
    sunny = max((r for r in report if r["day"] != cloudy), key=lambda r: r["sun"] - 3 * r["abs_err"])["day"]
    return sunny, cloudy, report


def fetch_prices(day: str) -> list:
    """24 hourly DE-LU day-ahead prices (EUR/MWh) for the given date from SMARD."""
    day_start = dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone(dt.timedelta(hours=2)))
    target_ms = int(day_start.timestamp() * 1000)
    index = _get(SMARD_INDEX)["timestamps"]
    week_ts = max(t for t in index if t <= target_ms)
    series = _get(SMARD_DATA.format(ts=week_ts))["series"]
    by_ts = {int(t): v for t, v in series if v is not None}
    prices = []
    for h in range(24):
        ts = target_ms + h * 3600 * 1000
        if ts not in by_ts:
            raise RuntimeError(f"SMARD missing hour {h} of {day}; pick another day")
        prices.append(float(by_ts[ts]))
    return prices


def fetch_day(day: str) -> dict:
    out = {"day": day, "prices_eur_mwh": fetch_prices(day), "parks": {}}
    for pid, p in PARKS.items():
        fc, ac = fetch_radiation(p["lat"], p["lon"], day, day)
        out["parks"][pid] = {"forecast_ghi": fc, "actual_ghi": ac}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="scan a recent window and pick days")
    ap.add_argument("--sunny", help="YYYY-MM-DD base day for S2/S3")
    ap.add_argument("--cloudy", help="YYYY-MM-DD real forecast-bust day for S1")
    ap.add_argument("--window-days", type=int, default=21)
    ap.add_argument("--end-lag-days", type=int, default=5, help="archive completeness buffer")
    args = ap.parse_args()

    if args.auto:
        end = dt.date.today() - dt.timedelta(days=args.end_lag_days)
        start = end - dt.timedelta(days=args.window_days - 1)
        sunny, cloudy, report = scan_days(start, end)
        print(f"scanned {start} .. {end}")
        for r in report:
            marks = ("  <- SUNNY" if r["day"] == sunny else "") + ("  <- CLOUDY" if r["day"] == cloudy else "")
            print(f"  {r['day']}  sun={r['sun']:>6}  munich_bust={r['munich_bust']:>5}  abs_err={r['abs_err']:>6}{marks}")
    else:
        if not (args.sunny and args.cloudy):
            ap.error("either --auto or both --sunny and --cloudy")
        sunny, cloudy = args.sunny, args.cloudy

    REAL_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"sunny_day": sunny, "cloudy_day": cloudy,
            "source": "Open-Meteo previous-runs (day-ahead fc) + archive (actual); SMARD 4169 DE-LU day-ahead",
            "price_zone_assumption": "whole portfolio settles at DE-LU prices"}
    for role, day in (("sunny", sunny), ("cloudy", cloudy)):
        data = fetch_day(day)
        (REAL_DIR / f"{role}.json").write_text(json.dumps(data))
        pr = data["prices_eur_mwh"]
        print(f"{role} = {day}: prices min {min(pr):.2f} max {max(pr):.2f} EUR/MWh, saved")
    (REAL_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"written to {REAL_DIR}")


if __name__ == "__main__":
    main()
