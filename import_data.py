import csv
import os

from app import app, db, Doctor

# Column names for the CORGIS hospitals dataset:
# "Facility.Name","Facility.City","Facility.State","Facility.Type",
# "Rating.Overall", "Procedure.Heart Attack.Cost", ...
COLUMN_MAP = {
    "name": ["Facility.Name", "name", "doctor_name", "full_name"],
    "specialty": ["Facility.Type", "specialty", "specialisation", "specialization"],
    "city": ["Facility.City", "city", "town"],
    "country": ["Facility.State", "country"],
    "clinic": ["Facility.Name", "clinic", "hospital_name", "facility"],
    "address": ["address", "street_address"],
    "phone": ["phone", "telephone", "mobile"],
    "email": ["email", "e_mail"],
    # Use heart attack cost as a sample "fee"
    "fee": ["Procedure.Heart Attack.Cost", "fee", "consultation_fee", "price"],
    "rating": ["Rating.Overall", "rating", "score"],
}


def get_value(row, possible_keys):
    """Return the first non-empty value from the possible_keys list."""
    for key in possible_keys:
        if key in row and row[key].strip() != "":
            return row[key].strip()
    return None


def import_contacts(csv_path: str):
    csv_path = os.path.abspath(csv_path)

    with app.app_context():
        # Make sure tables exist
        db.create_all()

        # Clear existing doctors before import
        Doctor.query.delete()
        db.session.commit()

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = get_value(row, COLUMN_MAP["name"])
                if not name:
                    continue  # skip rows without a name

                specialty = get_value(row, COLUMN_MAP["specialty"])
                city = get_value(row, COLUMN_MAP["city"])
                country = get_value(row, COLUMN_MAP["country"])
                clinic = get_value(row, COLUMN_MAP["clinic"])
                address = get_value(row, COLUMN_MAP["address"])
                phone = get_value(row, COLUMN_MAP["phone"])
                email = get_value(row, COLUMN_MAP["email"])

                fee_raw = get_value(row, COLUMN_MAP["fee"])
                rating_raw = get_value(row, COLUMN_MAP["rating"])

                fee = int(float(fee_raw)) if fee_raw not in (None, "") else None
                rating = float(rating_raw) if rating_raw not in (None, "") else None

                doctor = Doctor(
                    name=name,
                    specialty=specialty,
                    city=city,
                    country=country,
                    clinic=clinic,
                    address=address,
                    phone=phone,
                    email=email,
                    fee=fee,
                    rating=rating,
                )
                db.session.add(doctor)
                count += 1

            db.session.commit()
            print(f"Imported {count} contacts from {csv_path}")


if __name__ == "__main__":
    csv_file = os.path.join("data", "hospitals.csv")
    import_contacts(csv_file)
