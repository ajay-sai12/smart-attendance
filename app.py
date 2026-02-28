from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from bson.objectid import ObjectId
import bcrypt
from datetime import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)

mongo = PyMongo(app)
jwt = JWTManager(app)

# ---------------- UI ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ---------------- AUTH ----------------

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not all([name, email, password, role]):
        return jsonify({"message": "All fields are required"}), 400

    if mongo.db.users.find_one({"email": email}):
        return jsonify({"message": "User already exists"}), 400

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    mongo.db.users.insert_one({
        "name": name,
        "email": email,
        "password": hashed_pw,
        "role": role
    })

    return jsonify({"message": "Registered successfully"}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = mongo.db.users.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    if not bcrypt.checkpw(password.encode(), user["password"]):
        return jsonify({"message": "Invalid password"}), 401

    token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={"role": user["role"]}
    )

    return jsonify({"token": token, "role": user["role"]})

# ---------------- CREATE CLASS ----------------

@app.route("/api/class/create", methods=["POST"])
@jwt_required()
def create_class():
    user_id = get_jwt_identity()
    role = get_jwt().get("role")

    if role != "faculty":
        return jsonify({"message": "Only faculty allowed"}), 403

    data = request.get_json()
    name = data.get("name")

    class_id = mongo.db.classes.insert_one({
        "name": name,
        "facultyId": user_id,
        "createdAt": datetime.utcnow()
    }).inserted_id

    return jsonify({
        "message": "Class created successfully",
        "classId": str(class_id)
    }), 201

# ---------------- ADMIN DASHBOARD ----------------

@app.route("/api/admin/dashboard", methods=["GET"])
@jwt_required()
def admin_dashboard():
    role = get_jwt().get("role")

    if role != "admin":
        return jsonify({"message": "Only admin allowed"}), 403

    return jsonify({
        "total_users": mongo.db.users.count_documents({}),
        "total_classes": mongo.db.classes.count_documents({}),
        "total_attendance": mongo.db.attendance.count_documents({})
    })

# ---------------- MARK ATTENDANCE ----------------

@app.route("/api/attendance/mark", methods=["POST"])
@jwt_required()
def mark_attendance():
    user_id = get_jwt_identity()
    role = get_jwt().get("role")

    if role != "student":
        return jsonify({"message": "Only students allowed"}), 403

    data = request.get_json()
    class_id = data.get("classId")

    if not class_id:
        return jsonify({"message": "Class ID required"}), 400

    try:
        class_object_id = ObjectId(class_id)
    except:
        return jsonify({"message": "Invalid Class ID"}), 400

    if not mongo.db.classes.find_one({"_id": class_object_id}):
        return jsonify({"message": "Class not found"}), 404

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    if mongo.db.attendance.find_one({
        "studentId": user_id,
        "classId": class_id,
        "timestamp": {"$gte": today_start}
    }):
        return jsonify({"message": "Already marked today"}), 400

    mongo.db.attendance.insert_one({
        "studentId": user_id,
        "classId": class_id,
        "timestamp": datetime.utcnow()
    })

    return jsonify({"message": "Attendance marked successfully"}), 201
#------------------FETCH CLASSES---------------
@app.route("/api/classes", methods=["GET"])
@jwt_required()
def get_classes():
    classes = list(mongo.db.classes.find({}))

    result = []
    for c in classes:
        result.append({
            "id": str(c["_id"]),
            "name": c["name"]
        })

    return jsonify(result)
# ---------------- ATTENDANCE STATUS ----------------

@app.route("/api/attendance/status", methods=["GET"])
@jwt_required()
def attendance_status():
    user_id = get_jwt_identity()
    role = get_jwt().get("role")

    if role != "student":
        return jsonify({"message": "Only students allowed"}), 403

    total = mongo.db.attendance.count_documents({
        "studentId": user_id
    })

    return jsonify({
        "total_present_days": total
    })


if __name__ == "__main__":
    app.run(debug=True)