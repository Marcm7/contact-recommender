import csv
import os
from app import app, db, Doctor

CSV_PATH = os.path.join("data", "hospitals.csv")

def import_doctors():
    if not os.path.exists(CSV_PATH):
        print("CSV not found at:", CSV_PATH)
        return

    with app.app_context():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            count_added = 0

            for row in reader:
                name = row.get("Name", "").strip()
                city = row.get("City", "").strip()

                if not name:
                    continue

                # avoid duplicates
                existing = Doctor.query.filter_by(name=name, city=city).first()
                if existing:
                    continue

                doctor = Doctor(
                    name=name,
                    specialty=row.get("Specialty", "").strip(),
                    city=city,
                    country="Lebanon",
                    clinic=row.get("Clinic", "").strip(),
                    phone=row.get("Phone", "").strip(),
                    fee=int(float(row.get("Fee", 0))),
                    rating=float(row.get("Rating", 0)),
                )

                db.session.add(doctor)
                count_added += 1

            db.session.commit()
            print(f"✅ Imported {count_added} doctors into contacts.db")

if __name__ == "__main__":
    import_doctors()
