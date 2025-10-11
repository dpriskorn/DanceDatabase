import json
import csv
from pathlib import Path

# ---- Load JSON ----
with open("organizers.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ---- Output paths ----
csv_path = Path("organizers.csv")
qs_path = Path("organizers_quickstatements.txt")

# ---- Extract artist data ----
organizers = data["associations"]

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

    for a in organizers:
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
    for a in organizers:
        label_sv = a.get("name")
        response = input(f"ta med '{label_sv}'? (y/n)")
        if response != "n":

            # Determine P1 and description
            is_teacher = a.get("is_instructor")
            is_organizer = a.get("is_organizer")

            if is_teacher and is_organizer:
                P1 = "Q7"  # Organizer
                description_sv = "arrangör och instruktör"
            elif is_teacher:
                P1 = "Q297"  # Teacher
                description_sv = "dansinstruktör"
            elif is_organizer:
                P1 = "Q7"  # Organizer
                description_sv = "dansarrangör"
            else:
                P1 = "Q20"  # fallback
                description_sv = ""

            qs.write("CREATE\n")
            qs.write(f'LAST\tLsv\t"{label_sv}"\n')
            if description_sv:
                qs.write(f'LAST\tDsv\t"{description_sv}"\n')
            qs.write(f'LAST\tP1\t{P1}\n')
            qs.write(f'LAST\tP29\t"{a.get("id")}"\n\n')

print(f"✅ QuickStatements file saved as: {qs_path.resolve()}")
