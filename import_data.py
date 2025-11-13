import csv
import os

from app import app, db, Doctor


def import_contacts(csv_path: str):
    # Ensure path is absolute
    csv_path = os.path.abspath(csv_path)

    with app.app_context():
        # Make sure tables exist
        db.create_all()

        # Optional: clear existing doctors before import
        # Doctor.query.delete()
        # db.session.commit()

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Convert fee and rating safely
                fee = int(row["fee"]) if row.get("fee") else None
                rating = float(row["rating"]) if row.get("rating") else None

                doctor = Doctor(
                    name=row["name"],
                    specialty=row["specialty"],
                    city=row["city"],
                    address=row.get("address"),
                    fee=fee,
                    rating=rating,
                )
                db.session.add(doctor)
                count += 1

            db.session.commit()
            print(f"Imported {count} contacts from {csv_path}")


if __name__ == "__main__":
    csv_file = os.path.join("data", "contacts.csv")
    import_contacts(csv_file)
