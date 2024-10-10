# mongodb.py

from pymongo import MongoClient
from bson.objectid import ObjectId
import hashlib

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # Adjust if necessary
db = client['healthcare_bot']

# Collection references
users_collection = db.users
doctors_collection = db.doctors
appointments_collection = db.appointments
chat_logs_collection = db.chat_logs

doctors_collection.insert_one({"name": "Dr. Smith", "specialty": "Cardiology"})
doctors_collection.insert_one({"name": "Dr. Johnson", "specialty": "Neurology"})
doctors_collection.insert_one({"name": "Dr. Jay", "specialty": "Brain"})
doctors_collection.insert_one({"name": "Dr. Edith", "specialty": "homeopathy"})
doctors_collection.insert_one({"name": "Dr. Carson", "specialty": "Joints"})
doctors_collection.insert_one({"name": "Dr. Edward", "specialty": "Dentist"})
doctors_collection.insert_one({"name": "Dr. Steven", "specialty": "Routine Check UP"})

# Save user to database
def save_user_to_database(full_name, gender, age, email, mobile_number, password, patient_id):
    # Hash the password (in this case, using mobile number, but you can enhance it)
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # Create user document
    user = {
        "patient_id": patient_id,
        "full_name": full_name,
        "gender": gender,
        "age": age,
        "email": email,
        "mobile_number": mobile_number,
        "password": hashed_password  # Store the hashed password
    }

    # Insert user into the users collection
    result = users_collection.insert_one(user)
    return result.inserted_id, patient_id


# Retrieve user by patient_id and password for login
def get_user_by_patient_id_and_password(patient_id, password):

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # Query the users collection
    user = users_collection.find_one({
        "patient_id": patient_id,
        "password": hashed_password  # Match hashed password
    })

    return user

# Fetch user details by patient_id
def get_user_data(patient_id):
    return db.users.find_one({'patient_id': patient_id})

# Fetch all appointments by patient_id
def get_appointments(patient_id):
    return list(db.appointments.find({'patient_id': patient_id}).sort('date', 1))  # Sort by date

# Fetch prescriptions by patient_id
def get_prescriptions(patient_id):
    return list(db.prescriptions.find({'patient_id': patient_id}))

# Fetch medical records by patient_id
def get_medical_records(patient_id):
    return list(db.medical_records.find({'patient_id': patient_id}))
