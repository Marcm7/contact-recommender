from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# --- Database configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "contacts.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- Model: one contact = one doctor ---
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    fee = db.Column(db.Integer, nullable=True)     # integer fee
    rating = db.Column(db.Float, nullable=True)    # rating 1–5

    def __repr__(self):
        return f"<Doctor {self.name} ({self.specialty})>"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/doctors")
def list_doctors():
    doctors = Doctor.query.all()
    return render_template("doctors.html", doctors=doctors)


@app.route("/doctors/new", methods=["GET", "POST"])
def create_doctor():
    if request.method == "POST":
        name = request.form["name"]
        specialty = request.form["specialty"]
        city = request.form["city"]
        address = request.form.get("address")

        # ---- Fee: integer, no negatives ----
        fee_raw = request.form.get("fee")
        if fee_raw not in (None, ""):
            fee = int(fee_raw)
            if fee < 0:
                fee = 0
        else:
            fee = None

        # ---- Rating: optional float ----
        rating_raw = request.form.get("rating")
        rating = float(rating_raw) if rating_raw not in (None, "") else None

        new_doc = Doctor(
            name=name,
            specialty=specialty,
            city=city,
            address=address,
            fee=fee,
            rating=rating,
        )
        db.session.add(new_doc)
        db.session.commit()
        return redirect(url_for("list_doctors"))

    return render_template("new_doctor.html")
@app.route("/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == "POST":
        doctor.name = request.form["name"]
        doctor.specialty = request.form["specialty"]
        doctor.city = request.form["city"]
        doctor.address = request.form.get("address")

        # fee: same logic as before (integer, no negatives)
        fee_raw = request.form.get("fee")
        if fee_raw not in (None, ""):
            fee = int(fee_raw)
            if fee < 0:
                fee = 0
        else:
            fee = None
        doctor.fee = fee

        # rating
        rating_raw = request.form.get("rating")
        doctor.rating = float(rating_raw) if rating_raw not in (None, "") else None

        db.session.commit()
        return redirect(url_for("list_doctors"))

    return render_template("edit_doctor.html", doctor=doctor)


@app.route("/doctors/<int:doctor_id>/delete", methods=["POST"])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    return redirect(url_for("list_doctors"))

@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    doctors = []
    applied_filters = {}

    if request.method == "POST":
        city = request.form.get("city") or None
        specialty = request.form.get("specialty") or None
        max_fee_raw = request.form.get("max_fee")
        min_rating_raw = request.form.get("min_rating")

        query = Doctor.query

        if city:
            # case-insensitive partial match
            query = query.filter(Doctor.city.ilike(f"%{city}%"))
            applied_filters["city"] = city

        if specialty:
            query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
            applied_filters["specialty"] = specialty

        if max_fee_raw:
            max_fee = int(max_fee_raw)
            query = query.filter(Doctor.fee.isnot(None), Doctor.fee <= max_fee)
            applied_filters["max_fee"] = max_fee

        if min_rating_raw:
            min_rating = float(min_rating_raw)
            query = query.filter(Doctor.rating.isnot(None), Doctor.rating >= min_rating)
            applied_filters["min_rating"] = min_rating

        # Sort: highest rating first, then lowest fee
        doctors = query.order_by(Doctor.rating.desc(), Doctor.fee.asc()).all()

    return render_template("recommend.html",
                           doctors=doctors,
                           filters=applied_filters)




if __name__ == "__main__":
    # Create DB tables if they don't exist yet
    with app.app_context():
        db.create_all()
    app.run(debug=True)
