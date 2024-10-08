# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
from datetime import datetime
from flask_mail import Message, Mail
from mongodb import db, save_user_to_database, get_user_by_patient_id_and_password
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
    patient_id = request.form.get('patient_id')
    password = request.form.get('password')

    # Retrieve user from database
    user = get_user_by_patient_id_and_password(patient_id, password)

    if user:
        return jsonify({'message': 'Login successful'})
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    user_id = session.get('user_id')

    # Fetch upcoming appointments for the user
    appointments = db.appointments.find({'user_id': user_id}).sort('date', 1)  # Sorting by date
    appointments_list = list(appointments)  # Convert to a list

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
    user_id = session.get('user_id')
    doctor_name = request.form['doctor']
    date = request.form['date']
    time = request.form['time']

    # Fetch the user's email from the database
    user = db.users.find_one({'_id': user_id})  # Assuming '_id' is the user ID field
    if user:
        user_email = user.get('email')  # Get the email field from the user document
    else:
        return jsonify({'message': 'User not found.'}), 404

    # Check for appointment conflicts (same doctor, date, and time)
    existing_appointment = db.appointments.find_one({
        'doctor': doctor_name,
        'date': date,
        'time': time
    })

    if existing_appointment:
        return jsonify({'message': 'This time slot is already taken.'}), 400

    # Insert appointment into MongoDB
    appointment_data = {
        'user_id': user_id,
        'doctor': doctor_name,
        'date': date,
        'time': time,
        'status': 'Pending'
    }

    db.appointments.insert_one(appointment_data)

    # Send email notification
    send_email(
        "Appointment Confirmation",
        user_email,  # Send the user's email
        f"Your appointment with Dr. {doctor_name} on {date} at {time} has been confirmed."
    )

    return redirect(url_for('appointments'))  # Redirect to appointments page


@app.route('/get_events', methods=['GET'])
def get_events():
    # Fetch events (appointments) from the database for calendar
    events = db.appointments.find()
    events_list = []
    for event in events:
        events_list.append({
            'title': event['doctor'],
            'start': event['date'] + 'T' + event['time'],  # Assuming date and time are stored in a suitable format
            'end': event['date'] + 'T' + event['time'],
        })
    return jsonify(events_list)


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
    if 'user_id' in session:
        user_id = session['user_id']
        user = db.users.find_one({'_id': user_id})
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
@app.route('/google_login')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))

    # Fetch user info from Google
    google_info = google.get('/plus/v1/people/me')
    google_user_info = google_info.json()
    user_email = google_user_info.get("emails")[0].get("value")
    user_name = google_user_info.get("displayName")

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
    user = db.users.find_one({'email': user_email})

    if user:
        session['user_id'] = user['_id']  # Store the user's MongoDB ID in session
        return redirect(url_for('dashboard'))  # Redirect to the dashboard
    else:
        # If user doesn't exist, redirect to the signup page
        return redirect(url_for('signup'))  # Redirect to signup page


if __name__ == "__main__":
    app.run(debug=True)
