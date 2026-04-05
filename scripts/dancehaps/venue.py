import json
import csv
from pathlib import Path

# Load JSON data
with open("venues.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Prepare output paths
csv_path = Path("venues.csv")
qs_path = Path("venues_quickstatements.txt")

# Extract venue data
venues = data["venues"]

# Define CSV columns
fields = [
    "id",
    "name",
    "country",
    "region",
    "town",
    "lat",
    "lng",
    "is_closed",
    "cover"
]

# ---- Write CSV ----
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    writer.writeheader()

    for v in venues:
        writer.writerow({
            "id": v["id"],
            "name": v["name"],
            "country": v["country"],
            "region": v["region"],
            "town": v["town"],
            "lat": v["coords"]["lat"],
            "lng": v["coords"]["lng"],
            "is_closed": v["is_closed"],
            "cover": v["cover"]
        })

print(f"✅ CSV file saved as: {csv_path.resolve()}")

# ---- Write QuickStatements v1 ----
with open(qs_path, "w", encoding="utf-8") as qs:
    count = 0
    for v in venues:
        count += 1
        if count == 1:
            # skip the first
            continue
        label_sv = v["name"]
        lat = v["coords"]["lat"]
        lng = v["coords"]["lng"]

        qs.write(f'CREATE\n')
        qs.write(f'LAST\tLsv\t"{label_sv}"\n')
        qs.write(f'LAST\tP1\tQ20\n')
        qs.write(f'LAST\tP4\t@{lat}/{lng}\n')
        qs.write(f'LAST\tP26\t"{v["id"]}"\n\n')

print(f"✅ QuickStatements file saved as: {qs_path.resolve()}")
