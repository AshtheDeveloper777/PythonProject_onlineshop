from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from supabase import create_client
import os
import stripe
import razorpay
import hmac
import hashlib
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# ========================
# BASIC CONFIG
# ========================
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ========================
# SUPABASE CONFIG (for storage only)
# ========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========================
# STRIPE CONFIG
# ========================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

STRIPE_ENABLED = bool(
    STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY
)

if STRIPE_ENABLED:
    stripe.api_key = STRIPE_SECRET_KEY

# ========================
# RAZORPAY CONFIG
# ========================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

RAZORPAY_ENABLED = bool(
    RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
)

razorpay_client = None
if RAZORPAY_ENABLED:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
@app.route("/upload", methods=["POST"])
def upload_file():
    if not supabase:
        return jsonify({"error": "Storage not configured"}), 500

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename
    file_bytes = file.read()

    supabase.storage.from_("uploads").upload(filename, file_bytes)

    public_url = supabase.storage.from_("uploads").get_public_url(filename)

    return jsonify({
        "message": "File uploaded successfully",
        "url": public_url
    })

#if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)