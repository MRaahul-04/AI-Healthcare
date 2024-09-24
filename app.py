# app.py

from flask import Flask, render_template, request, redirect, url_for
import random

app = Flask(__name__)

# Mock user database (replace with actual database implementation)
users = {}  # Dictionary to store user data
patient_id_counter = 1  # Counter for generating Patient IDs

# List of medical quotes for random selection
medical_quotes = [
    "The greatest medicine of all is to teach people how not to need it.",
    "Good health is not something we can buy. However, it can be an extremely valuable savings account.",
    "It is health that is real wealth and not pieces of gold and silver.",
    "A good laugh and a long sleep are the best cures in the doctor’s book."
]

@app.route("/", methods=["GET", "POST"])
def index():
    quote = random.choice(medical_quotes)  # Get a random quote
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        password = request.form.get("password")
        # Dummy authentication logic
        if patient_id in users and users[patient_id]["password"] == password:
            return redirect(url_for("dashboard"))
        else:
            return render_template("index.html", error="Invalid credentials", quote=quote)

    return render_template("index.html", quote=quote)


@app.route("/signup", methods=["POST"])
def signup():
    global patient_id_counter  # Access global counter
    full_name = request.form.get("full_name")
    gender = request.form.get("gender")
    age = request.form.get("age")
    email = request.form.get("email")
    mobile_no = request.form.get("mobile_no")

    # Create a new user with auto-generated Patient ID and set password as mobile number
    if full_name and gender and age and email and mobile_no:
        patient_id = str(patient_id_counter)
        users[patient_id] = {
            "full_name": full_name,
            "gender": gender,
            "age": age,
            "email": email,
            "mobile_no": mobile_no,
            "password": mobile_no  # Set password as mobile number
        }
        patient_id_counter += 1  # Increment the Patient ID counter
        return redirect(url_for("dashboard"))
    else:
        return render_template("index.html", signup_error="Error in signup details", quote=random.choice(medical_quotes))


@app.get("/dashboard")
def dashboard():
    return "<h1>Welcome to the Dashboard</h1>"


# Placeholder routes for social login
@app.route("/login/google")
def login_google():
    return "<h1>Login via Google</h1>"

@app.route("/login/github")
def login_github():
    return "<h1>Login via GitHub</h1>"

@app.route("/login/twitter")
def login_twitter():
    return "<h1>Login via X (Twitter)</h1>"


if __name__ == "__main__":
    app.run(debug=True)