import json
import csv
from pathlib import Path

# ---- Config ----
TYPE_QID = "Q225"  # Change this to whatever QID you want for "type" in QuickStatements

# ---- Load JSON ----
with open("artists.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ---- Output paths ----
csv_path = Path("artists.csv")
qs_path = Path("artists_quickstatements.txt")

# ---- Extract artist data ----
artists = data["associations"]

# ---- CSV columns ----
fields = [
    "id",
    "name",
    "is_artist",
    "is_defunct",
    "is_instructor",
    "is_organizer",
    "cover"
]

# ---- Write CSV ----
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    writer.writeheader()

    for a in artists:
        writer.writerow({
            "id": a.get("id"),
            "name": a.get("name"),
            "is_artist": a.get("is_artist"),
            "is_defunct": a.get("is_defunct"),
            "is_instructor": a.get("is_instructor"),
            "is_organizer": a.get("is_organizer"),
            "cover": a.get("cover")
        })

print(f"✅ CSV file saved as: {csv_path.resolve()}")

# ---- Write QuickStatements v1 ----
with open(qs_path, "w", encoding="utf-8") as qs:
    for a in artists:
        label_sv = a.get("name")
        response = input(f"ta med '{label_sv}'? (y/n)")
        if response != "n":
            qs.write(f'CREATE\n')
            qs.write(f'LAST\tLsv\t"{label_sv}"\n')
            qs.write(f'LAST\tDsv\t"artist"\n')
            qs.write(f'LAST\tP1\t{TYPE_QID}\n')  # Use config variable here
            qs.write(f'LAST\tP26\t"{a.get("id")}"\n\n')

print(f"✅ QuickStatements file saved as: {qs_path.resolve()}")
