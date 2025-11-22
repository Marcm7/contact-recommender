from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import json
import requests
import google.generativeai as genai

RECOMMENDER_URL = "http://localhost:8000/api/recommend-doc"

# Configure Gemini with your API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = "change_me"  # needed for flash() messages

# --- Database configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "contacts.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- Model: one contact = one doctor ---
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    clinic = db.Column(db.String(200), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    fee = db.Column(db.Integer, nullable=True)      # integer fee
    rating = db.Column(db.Float, nullable=True)     # rating 1–5

    def __repr__(self):
        return f"<Doctor {self.name} ({self.specialty})>"
    
def call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Call Gemini 2.5 Flash and return CLEAN, SAFE JSON text.
    Handles:
    - Markdown fences
    - Extra commentary
    - Incorrect formatting
    """

    model_name = "models/gemini-2.5-flash"
    print(f"Using Gemini model: {model_name}")

    model = genai.GenerativeModel(model_name)

    full_prompt = (
        system_prompt
        + "\n\n"
        + "Return ONLY valid JSON. No explanations, no extra text.\n"
        + user_prompt
    )

    response = model.generate_content(full_prompt)

    raw = response.text or ""
    print("\n=== RAW GEMINI OUTPUT ===\n", raw, "\n==========================\n")

    # -----------------------------------------------------
    # 1) Remove markdown fences if Gemini used ```json ... ```
    # -----------------------------------------------------
    raw = raw.replace("```json", "").replace("```", "").strip()

    # -----------------------------------------------------
    # 2) Extract JSON object even if text surrounds it
    # -----------------------------------------------------
    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        print("❌ ERROR: Could not find JSON in Gemini output.")
        return "{}"   # fail safe

    json_text = raw[start:end + 1]

    # -----------------------------------------------------
    # 3) Validate JSON before returning
    # -----------------------------------------------------
    import json
    try:
        json.loads(json_text)  # validate
    except Exception as e:
        print("❌ JSON PARSE ERROR:", e)
        # try last-resort cleaning
        json_text = json_text.replace("\n", " ").replace("\t", " ")
        try:
            json.loads(json_text)
        except:
            return "{}"

    return json_text





def get_doctors_by_specialties(specialties: list[str], limit: int = 10) -> list[Doctor]:
    """Return doctors whose specialty is in the given list, ordered by rating."""
    if not specialties:
        return []

    # Clean empty strings
    clean_specs = [s for s in {s.strip() for s in specialties} if s]
    if not clean_specs:
        return []

    # Order by rating descending (best rated first)
    return (
        Doctor.query
        .filter(Doctor.specialty.in_(clean_specs))
        .order_by(Doctor.rating.desc().nullslast())
        .limit(limit)
        .all()
    )

@app.route("/")
def home():
    doctors_count = Doctor.query.count()
    return render_template("index.html", doctors_count=doctors_count)




# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/doctors")
def list_doctors():
    doctors = Doctor.query.all()
    return render_template("doctors.html", doctors=doctors)


@app.route("/doctors/new", methods=["GET", "POST"])
def add_doctor():
    if request.method == "POST":
        name = request.form["name"]
        specialty = request.form.get("specialty")
        city = request.form.get("city")
        country = request.form.get("country")
        clinic = request.form.get("clinic")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")

        # fee: integer, no negatives
        fee_raw = request.form.get("fee")
        if fee_raw not in (None, ""):
            fee = int(fee_raw)
            if fee < 0:
                fee = 0
        else:
            fee = None

        # rating: optional float
        rating_raw = request.form.get("rating")
        rating = float(rating_raw) if rating_raw not in (None, "") else None

        new_doc = Doctor(
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
        db.session.add(new_doc)
        db.session.commit()
        return redirect(url_for("list_doctors"))

    return render_template("new_doctor.html")


@app.route("/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == "POST":
        doctor.name = request.form["name"]
        doctor.specialty = request.form.get("specialty")
        doctor.city = request.form.get("city")
        doctor.country = request.form.get("country")
        doctor.clinic = request.form.get("clinic")
        doctor.address = request.form.get("address")
        doctor.phone = request.form.get("phone")
        doctor.email = request.form.get("email")

        # fee: integer, no negatives
        fee_raw = request.form.get("fee")
        if fee_raw not in (None, ""):
            fee = int(fee_raw)
            if fee < 0:
                fee = 0
        else:
            fee = None
        doctor.fee = fee

        # rating: optional float
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

@app.route("/symptom-checker", methods=["GET", "POST"])
def symptom_checker():
    symptoms = ""
    recommendations = []   # list of dicts: {"Condition": "Specialty"}
    doctors = []
    advice = ""
    disclaimer = ""

    # ✅ NEW: variables your template expects
    conditions_list = None
    specialties_list = None

    if request.method == "POST":
        symptoms = request.form.get("symptoms", "").strip()

        if not symptoms:
            flash("Please describe your symptoms before requesting a recommendation.")
            return redirect(url_for("symptom_checker"))

        system_prompt = """
You are a medical guidance assistant (NOT a doctor).
Your job:
- Read the user's symptoms.
- Suggest a few POSSIBLE conditions (not a diagnosis).
- For each condition, suggest ONE main medical specialty.
- Give short general advice.
- Give a strong disclaimer.

You MUST return VALID JSON ONLY, in exactly this structure:

{
  "conditions": [
    {"name": "Condition 1", "specialty": "Specialty 1"},
    {"name": "Condition 2", "specialty": "Specialty 2"}
  ],
  "advice": "Short paragraph of general advice.",
  "disclaimer": "Strong disclaimer that this is not a diagnosis and the user must see a doctor. Mention when to go to emergency services."
}

Rules:
- No extra text outside the JSON.
- Condition and specialty names should be short.
"""

        user_prompt = f"""
User symptoms (free text):

\"\"\"{symptoms}\"\"\"
"""

        try:
            raw = call_gemini(system_prompt, user_prompt)
            print("RAW GEMINI OUTPUT:", raw)

            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("Gemini did not return a JSON object")

            json_text = raw[start:end + 1]
            data = json.loads(json_text)

            conditions = data.get("conditions", [])

            recommendations = []
            specialties_list = []     # ✅ for template
            conditions_list = []      # ✅ for template

            for cond in conditions:
                name = cond.get("name", "").strip()
                spec = cond.get("specialty", "").strip()
                if name and spec:
                    recommendations.append({name: spec})
                    conditions_list.append(name)   # ✅ only names
                    specialties_list.append(spec)  # ✅ only specialties

            advice = data.get("advice", "")
            disclaimer = data.get("disclaimer", "")

            doctors = get_doctors_by_specialties(specialties_list, limit=10)

        except Exception as e:
            print("AI error in symptom_checker:", repr(e))
            flash("There was a problem generating the AI recommendation. Please try again.")

            recommendations = []
            doctors = []
            advice = ""
            disclaimer = ""
            conditions_list = []
            specialties_list = []

    return render_template(
        "symptom_checker.html",
        symptoms=symptoms,
        recommendations=recommendations,
        doctors=doctors,
        advice=advice,
        disclaimer=disclaimer,

        # ✅ now your upgraded UI will show results
        conditions=conditions_list,
        specialties=specialties_list
    )


# Create tables as soon as the app is imported (works on Azure + locally)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

