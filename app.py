# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
from datetime import datetime
from mongodb import db, save_user_to_database, get_user_by_patient_id_and_password

app = Flask(__name__)

# Set a secret key to enable session functionality
app.secret_key = 'test'  # Replace with a random, secure key

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


def create_patient_id():
    # Access the users collection from MongoDB
    users_collection = db['users']

    # Find the maximum current patient_id and start from 100
    last_user = users_collection.find_one({}, sort=[("patient_id", -1)])  # Get the last user sorted by patient_id

    if last_user and 'patient_id' in last_user:
        # Increment the last patient_id by 1
        new_patient_id = int(last_user['patient_id']) + 1
    else:
        # If no users exist, start from 100
        new_patient_id = 100

    return str(new_patient_id)


@app.route('/signup', methods=['POST'])
def signup():
    full_name = request.form.get('full_name')
    gender = request.form.get('gender')
    age = request.form.get('age')
    email = request.form.get('email')
    mobile_number = request.form.get('mobile_number')

    patient_id = create_patient_id()  # Generate a patient ID
    password = mobile_number  # Set password to mobile number for now

    # Save user to database
    save_user_to_database(full_name, gender, age, email, mobile_number, password, patient_id)

    # Return JSON response for modal popup
    return jsonify({
        'message': f'Patient ID: {patient_id} created. Please sign in to proceed.'
    })


@app.route('/login', methods=['POST'])
def login():
    patient_id = request.form.get('patient_id')
    password = request.form.get('password')

    # Retrieve user from database
    user = get_user_by_patient_id_and_password(patient_id, password)

    if user:
        return jsonify({'message': 'Login successful'})
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    user_id = session.get('user_id')
    appointment_data = {
        'user_id': user_id,
        'date': request.form['date'],
        'time': request.form['time'],
        'doctor': request.form['doctor'],
        'status': 'Pending'
    }

    # Insert into MongoDB
    db.appointments.insert_one(appointment_data)

    return redirect(url_for('appointments'))

def log_chat(user_id, message, response):
    log_data = {
        'user_id': user_id,
        'message': message,
        'response': response,
        'timestamp': datetime.now()
    }

    db.chat_logs.insert_one(log_data)


@app.route("/dashboard")
def dashboard():
    if 'user' in session:
        user = session['user']
        return render_template("dashboard.html", user=user)
    else:
        # If user isn't logged in, redirect to log in
        return redirect(url_for('login'))  # Redirect to log in if no user is logged in

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        # Logic for sending password reset (via email or phone)
        email_or_phone = request.form.get("email_or_phone")
        return redirect(url_for("password_reset_confirmation"))
    return render_template("forgot_password.html")

@app.get("/password-reset-confirmation")
def password_reset_confirmation():
    return render_template("password_reset.html")


# Placeholder routes for social login
@app.get("/login/google")
def login_google():
    return render_template("google.html")

@app.get("/login/github")
def login_github():
    return render_template("github.html")


if __name__ == "__main__":
    app.run(debug=True)