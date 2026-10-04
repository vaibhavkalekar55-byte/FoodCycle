from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime
from functools import wraps
import os


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "foodcycle-dev-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///"
    + os.path.join(
        app.instance_path,
        "foodcycle.db"
    )
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Create instance folder
os.makedirs(
    app.instance_path,
    exist_ok=True
)


# Database
db = SQLAlchemy(app)


# ============================================================
# USER MODEL
# ============================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(160),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        nullable=False,
        default="donor"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    donations = db.relationship(
        "Donation",
        backref="donor",
        lazy=True
    )


# ============================================================
# DONATION MODEL
# ============================================================

class Donation(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    food_name = db.Column(
        db.String(150),
        nullable=False
    )

    food_type = db.Column(
        db.String(80),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    servings = db.Column(
        db.Integer,
        nullable=False
    )

    expiry = db.Column(
        db.DateTime,
        nullable=False
    )

    address = db.Column(
        db.String(255),
        nullable=False
    )

    notes = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(30),
        default="available"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    donor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


# ============================================================
# NGO MODEL
# ============================================================

class NGO(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(180),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    address = db.Column(
        db.String(255),
        nullable=False
    )

    phone = db.Column(
        db.String(30)
    )

    latitude = db.Column(
        db.Float,
        default=12.9716
    )

    longitude = db.Column(
        db.Float,
        default=77.5946
    )

    accepting = db.Column(
        db.Boolean,
        default=True
    )


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "info"
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# ROLE REQUIRED
# ============================================================

def role_required(*roles):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:

                return redirect(
                    url_for("login")
                )

            if session.get("role") not in roles:

                flash(
                    "You don't have permission to access this page.",
                    "error"
                )

                return redirect(
                    url_for("dashboard")
                )

            return function(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================
# GLOBAL TEMPLATE DATA
# ============================================================

@app.context_processor
def inject_globals():

    return {
        "current_year": datetime.now().year
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    donation_count = Donation.query.count()

    total_servings = (
        db.session.query(
            db.func.sum(Donation.servings)
        ).scalar()
        or 0
    )

    ngo_count = NGO.query.count()

    donor_count = User.query.filter_by(
        role="donor"
    ).count()

    stats = {
        "donations": donation_count,
        "servings": total_servings,
        "ngos": ngo_count,
        "donors": donor_count
    }

    return render_template(
        "index.html",
        stats=stats
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        role = request.form.get(
            "role",
            "donor"
        )

        # Validation
        if not name:

            flash(
                "Please enter your name.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not email:

            flash(
                "Please enter your email.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not password:

            flash(
                "Please enter a password.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # Allow only valid roles
        if role not in [
            "donor",
            "ngo"
        ]:

            role = "donor"

        # Check existing email
        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "An account with this email already exists.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # ====================================================
        # IMPORTANT:
        # method belongs INSIDE generate_password_hash()
        # ====================================================

        hashed_password = generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )

        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role=role
        )

        try:

            db.session.add(user)
            db.session.commit()

        except Exception:

            db.session.rollback()

            flash(
                "Unable to create account. Please try again.",
                "error"
            )

            return render_template(
                "register.html"
            )

        flash(
            "Account created successfully! Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        if user:

            try:

                password_correct = check_password_hash(
                    user.password,
                    password
                )

            except Exception:

                password_correct = False

        else:

            password_correct = False

        if user and password_correct:

            session["user_id"] = user.id
            session["name"] = user.name
            session["role"] = user.role

            flash(
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = db.session.get(
        User,
        session["user_id"]
    )

    if user is None:

        session.clear()

        return redirect(
            url_for("login")
        )

    if user.role == "donor":

        donations = (
            Donation.query
            .filter_by(
                donor_id=user.id
            )
            .order_by(
                Donation.created_at.desc()
            )
            .all()
        )

    else:

        donations = (
            Donation.query
            .order_by(
                Donation.created_at.desc()
            )
            .limit(20)
            .all()
        )

    return render_template(
        "dashboard.html",
        user=user,
        donations=donations
    )


# ============================================================
# DONATE FOOD
# ============================================================

@app.route(
    "/donate",
    methods=["GET", "POST"]
)
@role_required("donor")
def donate():

    if request.method == "POST":

        try:

            food_name = request.form.get(
                "food_name",
                ""
            ).strip()

            food_type = request.form.get(
                "food_type",
                ""
            ).strip()

            quantity = int(
                request.form.get(
                    "quantity",
                    "0"
                )
            )

            servings = int(
                request.form.get(
                    "servings",
                    "0"
                )
            )

            expiry_text = request.form.get(
                "expiry",
                ""
            )

            expiry = datetime.fromisoformat(
                expiry_text
            )

            address = request.form.get(
                "address",
                ""
            ).strip()

            notes = request.form.get(
                "notes",
                ""
            ).strip()

            # Validation

            if not food_name:

                raise ValueError(
                    "Food name is required."
                )

            if not food_type:

                raise ValueError(
                    "Food type is required."
                )

            if quantity <= 0:

                raise ValueError(
                    "Quantity must be greater than zero."
                )

            if servings <= 0:

                raise ValueError(
                    "Servings must be greater than zero."
                )

            if not address:

                raise ValueError(
                    "Pickup address is required."
                )

            donation = Donation(
                food_name=food_name,
                food_type=food_type,
                quantity=quantity,
                servings=servings,
                expiry=expiry,
                address=address,
                notes=notes,
                status="available",
                donor_id=session["user_id"]
            )

            db.session.add(donation)
            db.session.commit()

            flash(
                "Food donation published successfully! 🌱",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        except ValueError as error:

            flash(
                str(error),
                "error"
            )

        except Exception as error:

            db.session.rollback()

            print(
                "Donation error:",
                error
            )

            flash(
                "Unable to create donation.",
                "error"
            )

    return render_template(
        "donate.html"
    )


# ============================================================
# NGO DIRECTORY
# ============================================================

@app.route("/ngos")
def ngos():

    ngo_list = NGO.query.filter_by(
        accepting=True
    ).all()

    return render_template(
        "ngos.html",
        ngos=ngo_list
    )


# ============================================================
# NGO API
# ============================================================

@app.route("/api/ngos")
def api_ngos():

    ngo_list = NGO.query.all()

    return jsonify([

        {
            "id": ngo.id,
            "name": ngo.name,
            "description": ngo.description,
            "city": ngo.city,
            "address": ngo.address,
            "phone": ngo.phone,
            "latitude": ngo.latitude,
            "longitude": ngo.longitude,
            "accepting": ngo.accepting
        }

        for ngo in ngo_list

    ])


# ============================================================
# ADD DEMO NGOs
# ============================================================

@app.route("/seed-demo-data")
def seed_demo_data():

    if NGO.query.count() > 0:

        flash(
            "NGO demo data already exists.",
            "info"
        )

        return redirect(
            url_for("ngos")
        )

    demo_ngos = [

        NGO(
            name="FoodCycle Community Kitchen",
            description="Community food rescue organization.",
            city="Bengaluru",
            address="Indiranagar, Bengaluru, Karnataka",
            phone="+91 90000 00001",
            latitude=12.9784,
            longitude=77.6408,
            accepting=True
        ),

        NGO(
            name="Hope Meal Foundation",
            description="Accepts safe surplus meals.",
            city="Bengaluru",
            address="Koramangala, Bengaluru, Karnataka",
            phone="+91 90000 00002",
            latitude=12.9352,
            longitude=77.6245,
            accepting=True
        ),

        NGO(
            name="Annapoorna Food Rescue",
            description="Food rescue and redistribution.",
            city="Bengaluru",
            address="Jayanagar, Bengaluru, Karnataka",
            phone="+91 90000 00003",
            latitude=12.9250,
            longitude=77.5838,
            accepting=True
        )

    ]

    try:

        db.session.add_all(
            demo_ngos
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "NGO seed error:",
            error
        )

        flash(
            "Unable to add demo NGOs.",
            "error"
        )

        return redirect(
            url_for("ngos")
        )

    flash(
        "Demo NGOs added successfully!",
        "success"
    )

    return redirect(
        url_for("ngos")
    )


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return render_template(
        "404.html"
    ), 404


# ============================================================
# 500 ERROR
# ============================================================

@app.errorhandler(500)
def server_error(error):

    db.session.rollback()

    return """
    <h1>FoodCycle Server Error</h1>
    <p>Something went wrong. Please check the terminal for details.</p>
    """, 500


# ============================================================
# CREATE DATABASE
# ============================================================

with app.app_context():

    db.create_all()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )