"""
Export storm events from hist_hurr_2010_2025_merged.txt to JSON format
for use in the Hydrological Modeling frontend.

Output: frontend/data/storms_data.json
Each storm has: id, name, startDate, endDate, displayLabel
Multi-point storms (e.g. HENRI) get min/max date range from all points.
"""
import json
import os
from collections import defaultdict
from datetime import datetime

INPUT = os.path.join(os.path.dirname(__file__), "..", "events", "hist_hurr_2010_2025_merged.txt")
OUTPUT_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "data", "storms_data.json")
OUTPUT_DOCS = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "storms_data.json")

# Nominal duration in days for single-point events (used when only one date exists)
SINGLE_POINT_DAYS = 2

# Known multi-day event ranges from ri_ma_ct_storms (used to override when merged has single point)
OVERRIDES = {
    ("MARCH_NOREASTER", 2010): ("2010-03-12", "2010-03-16"),
    ("SANDY", 2012): ("2012-10-29", "2012-10-30"),
    ("MARCH_NOREASTER", 2013): ("2013-03-06", "2013-03-07"),
    ("JOAQUIN", 2015): ("2015-10-02", "2015-10-05"),
    ("JANUARY_BLIZZARD", 2016): ("2016-01-22", "2016-01-24"),
    ("JOSE", 2017): ("2017-09-19", "2017-09-22"),
    ("PHILIPPE", 2017): ("2017-10-29", "2017-10-30"),
    ("MARCH_NOREASTER", 2018): ("2018-03-01", "2018-03-03"),
    ("MELISSA", 2019): ("2019-10-11", "2019-10-13"),
    ("ZETA", 2020): ("2020-10-30", "2020-10-30"),
    ("WINTER_STORM", 2020): ("2020-12-16", "2020-12-17"),
    ("WINTER_STORM", 2021): ("2021-02-01", "2021-02-07"),  # Combine Feb 1-2 and Feb 7
    ("LEE", 2023): ("2023-09-15", "2023-09-16"),
    ("FEBRUARY_NOREASTER", 2024): ("2024-02-10", "2024-02-18"),
    ("ERIN", 2025): ("2025-08-21", "2025-08-22"),
}


def parse_row(line):
    parts = line.strip().split("\t")
    if len(parts) < 10:
        return None
    name = parts[0].strip()
    try:
        year = int(parts[4])
        month = int(parts[5])
        day = int(parts[6])
        hour = int(parts[7]) if parts[7] else 0
        minute = int(parts[8]) if parts[8] else 0
    except (ValueError, IndexError):
        return None
    dt = datetime(year, month, day, hour, minute)
    return {"name": name, "year": year, "date": dt}


def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Group by (name, year) to handle multi-point storms
    groups = defaultdict(list)
    for line in lines[1:]:  # skip header
        row = parse_row(line)
        if not row:
            continue
        key = (row["name"], row["year"])
        groups[key].append(row["date"])

    storms = []
    seen_ids = set()

    for (name, year), dates in sorted(groups.items(), key=lambda x: (x[0][1], min(d.date() for d in x[1]))):
        # Unique id: name_year, handle duplicates like MARCH_NOREASTER 2010 vs 2013
        base_id = f"{name}_{year}"
        idx = 0
        storm_id = base_id
        while storm_id in seen_ids:
            idx += 1
            storm_id = f"{base_id}_{idx}"
        seen_ids.add(storm_id)

        # Check overrides first
        override = OVERRIDES.get((name, year))
        if override:
            start_str, end_str = override
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        else:
            start_d = min(d.date() for d in dates)
            end_d = max(d.date() for d in dates)
            if start_d == end_d:
                from datetime import timedelta
                end_d = start_d + timedelta(days=SINGLE_POINT_DAYS)
            start_date = start_d
            end_date = end_d

        display_label = f"{name} ({year})"
        storms.append({
            "id": storm_id,
            "name": name,
            "year": year,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "displayLabel": display_label,
        })

    # Sort by start date
    storms.sort(key=lambda s: s["startDate"])

    out = {"storms": storms}
    os.makedirs(os.path.dirname(OUTPUT_FRONTEND), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_DOCS), exist_ok=True)
    with open(OUTPUT_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(OUTPUT_DOCS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Exported {len(storms)} storms to {OUTPUT_FRONTEND}")


if __name__ == "__main__":
    main()
