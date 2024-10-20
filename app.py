# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import random
from datetime import datetime
from flask_mail import Message, Mail
from bson import ObjectId
from mongodb import db, save_user_to_database, get_user_by_patient_id_and_password, get_user_data, get_appointments, \
    get_prescriptions, get_medical_records
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.contrib.google import make_google_blueprint, google

app = Flask(__name__)

# Secret keys for your app
app.secret_key = 'key'  # Set a secret key for session
app.config['SECRET_KEY'] = 'key'
app.config['GOOGLE_OAUTH_CLIENT_ID'] = 'your-google-client-id'
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = 'your-google-client-secret'
app.config['GITHUB_OAUTH_CLIENT_ID'] = 'your-github-client-id'
app.config['GITHUB_OAUTH_CLIENT_SECRET'] = 'your-github-client-secret'

# Google OAuth setup
google_bp = make_google_blueprint(scope=["profile", "email"])
app.register_blueprint(google_bp, url_prefix='/google_login')

# GitHub OAuth setup
github_bp = make_github_blueprint(scope=["user:email"])
app.register_blueprint(github_bp, url_prefix='/github_login')

# List of medical quotes for random selection
medical_quotes = [
    "The greatest medicine of all is to teach people how not to need it.",
    "Good health is not something we can buy. However, it can be an extremely valuable savings account.",
    "It is health that is real wealth and not pieces of gold and silver.",
    "A good laugh and a long sleep are the best cures in the doctor’s book."
]


@app.route('/')
def index():
    quote = random.choice(medical_quotes)  # Get a random quote
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        password = request.form.get("password")

        # Query the 'users' collection to get the user document by 'patient_id'
        user = db.users.find_one({'patient_id': patient_id})  # Adjust the field name if necessary

        if user and user.get("password") == password:
            # Assuming patient_id is unique and exists
            session['user_id'] = user['_id']  # Store user ID in session
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
    password = request.form.get('password')  # Get a custom password from form

    # Save user to database
    save_user_to_database(full_name, gender, age, email, mobile_number, password, patient_id)

    # Return JSON response for modal popup
    return jsonify({
        'message': f'Patient ID: {patient_id} created. Please sign in to proceed.'
    })

@app.route('/login', methods=['POST'])
def login():
    # Get form data
    patient_id = request.form['patient_id']
    password = request.form['password']

    # Example authentication logic
    user = get_user_by_patient_id_and_password(patient_id, password)

    if user:
        # Convert ObjectId to string before saving to session
        session['user_id'] = str(user['_id'])
        session['patient_id'] = user['patient_id']
        session['full_name'] = user['full_name']
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid Patient ID or Password', 'error')
        return render_template('index.html')

# else:
#     # If the method is GET, just render the login page
#     return render_template('index.html')

# @app.route('/dashboard', methods=['GET', 'POST'])
# def dashboard():
#     if 'user_id' in session:
#         user_id = session['user_id']
#         user = db.users.find_one({'_id': user_id})
#
#     else:
#         # If user isn't logged in, redirect to log in
#         return redirect(url_for('login'))  # Redirect to log in if no user is logged in

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Ensure user is logged in

    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})  # Fetch user by MongoDB ObjectId

    if not user:
        flash("User not found!", "error")
        return redirect(url_for('login'))

    patient_id = user.get('patient_id')
    user_data = get_user_data(patient_id)  # Fetch user data
    medical_records = get_medical_records(patient_id)
    appointments = get_appointments(patient_id)  # Get appointments
    prescriptions = get_prescriptions(patient_id)  # Get prescriptions

    health_insight = "Stay hydrated and eat a balanced diet!"  # Example health insight

    last_appointment = appointments[0] if appointments else {}
    upcoming_appointments = appointments[1:] if len(appointments) > 1 else []

    return render_template(
        'dashboard.html',
        user=user_data,
        appointments=appointments,
        last_appointment=last_appointment,
        upcoming_appointments=upcoming_appointments,
        health_insight=health_insight,
        medical_records=medical_records,
        prescriptions=prescriptions,
        medication_reminder="Take your medication as prescribed!"
    )

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')  # Render your chatbot page

@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    user_id = session.get('user_id')

    # Fetch upcoming appointments for the user
    appointment = db.appointments.find({'user_id': user_id}).sort('date', 1)  # Sorting by date
    appointments_list = list(appointment)  # Convert to a list

    # Fetch the list of doctors
    doctors = db.doctors.find()  # Fetch doctors from the database

    return render_template('appointment.html', appointments=appointments_list, doctors=doctors)


mail = Mail(app)


def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    user_id = session['user_id']
    doctor_name = request.form['doctor']
    date = request.form['date']
    time = request.form['time']

    # Fetch user email for confirmation
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'message': 'User not found.'}), 404

    # Check for conflicts
    conflict = db.appointments.find_one({'doctor': doctor_name, 'date': date, 'time': time})
    if conflict:
        return jsonify({'message': 'Time slot already booked.'}), 400

    # Book the appointment
    db.appointments.insert_one({
        'user_id': ObjectId(user_id),
        'doctor': doctor_name,
        'date': date,
        'time': time,
        'status': 'Pending'
    })

    send_email(
        "Appointment Confirmation",
        user['email'],
        f"Your appointment with Dr. {doctor_name} on {date} at {time} is confirmed."
    )

    return redirect(url_for('appointments'))


@app.route('/get_events', methods=['GET'])
@app.route('/get_events', methods=['GET'])
def get_events():
    events = get_appointments(session['patient_id'])  # Fetch appointments for the logged-in patient
    events_list = [{
        'title': f"Appointment with Dr. {event['doctor']}",
        'start': event['date'] + 'T' + event['time'],  # Assuming date and time are in a suitable format
        'end': event['date'] + 'T' + event['time']
    } for event in events]

    return jsonify(events_list)


def log_chat(user_id, message, response):
    log_data = {
        'user_id': user_id,
        'message': message,
        'response': response,
        'timestamp': datetime.now()
    }

    db.chat_logs.insert_one(log_data)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        # Logic for sending password reset (via email or phone)
        request.form.get("email_or_phone")
        return redirect(url_for("password_reset_confirmation"))
    return render_template("forgot_password.html")


@app.get("/password-reset-confirmation")
def password_reset_confirmation():
    return render_template("password_reset.html")


# Placeholder routes for social login
@app.route('/google_login')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))

    # Fetch user info from Google
    google_info = google.get('/plus/v1/people/me')
    google_user_info = google_info.json()
    user_email = google_user_info.get("emails")[0].get("value")
    google_user_info.get("displayName")

    # Check if user already exists in the database
    user = db.users.find_one({'email': user_email})

    if user:
        session['user_id'] = user['_id']  # Store the user's MongoDB ID in session
        return redirect(url_for('dashboard'))  # Redirect to the dashboard
    else:
        # If user doesn't exist, redirect to the signup page
        return redirect(url_for('signup'))  # Redirect to signup page


@app.route('/github_login')
def github_login():
    if not github.authorized:
        return redirect(url_for('github.login'))

    # Fetch user info from GitHub
    github_info = github.get('/user')
    github_user_info = github_info.json()
    user_name = github_user_info["login"]
    user_email = github_user_info.get("email")

    # Check if user already exists in the database
    user = db.users.find_one({'email': user_email, 'login': user_name})

    if user:
        session['user_id'] = user['_id']  # Store the user's MongoDB ID in session
        return redirect(url_for('dashboard'))  # Redirect to the dashboard
    else:
        # If user doesn't exist, redirect to the signup page
        return redirect(url_for('signup'))  # Redirect to signup page


if __name__ == "__main__":
    app.run(debug=True)
