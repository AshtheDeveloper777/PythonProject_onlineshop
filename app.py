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
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///shop.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ========================
# USER MODEL
# ========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


# ========================
# PRODUCT MODEL
# ========================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship("Product", backref="cart_items")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    shipping_address = db.Column(db.Text, nullable=True)
    payment_status = db.Column(db.String(20), default="pending")
    payment_method = db.Column(db.String(20), default="mock")
    razorpay_order_id = db.Column(db.String(255), nullable=True)
    razorpay_payment_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship("Product", backref="order_items")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========================
# SUPABASE CONFIG
# ========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========================
# RAZORPAY CONFIG
# ========================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_ENABLED = bool(
    RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and RAZORPAY_KEY_ID.startswith("rzp_")
)
razorpay_client = None
if RAZORPAY_ENABLED:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ========================
# HOME ROUTE
# ========================
@app.route("/")
def index():
    products = Product.query.limit(8).all()
    return render_template("index.html", products=products)

# ========================
# REGISTER ROUTE
# ========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already exists!")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, password_hash=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful!")
        return redirect(url_for("login"))

    return render_template("register.html")

# ========================
# LOGIN ROUTE
# ========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid credentials!")

    return render_template("login.html")
# ========================
# PRODUCTS ROUTE (list)
# ========================
@app.route("/products")
def products():
    category = request.args.get("category")
    search = request.args.get("search")
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            Product.name.contains(search) | Product.description.contains(search)
        )
    products = query.all()
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    return render_template(
        "Products.html",
        products=products,
        categories=categories,
        current_category=category,
    )


# ========================
# PRODUCT DETAIL ROUTE (single product)
# ========================
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", product=product)

# ========================
# LOGOUT ROUTE
# ========================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# ========================
# CART ROUTES
# ========================
@app.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get("quantity", 1))
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash(f"{product.name} added to cart!", "success")
    return redirect(request.referrer or url_for("products"))


@app.route("/update_cart/<int:cart_item_id>", methods=["POST"])
@login_required
def update_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        quantity = int(request.form.get("quantity", 1))
        if quantity > 0:
            cart_item.quantity = quantity
            db.session.commit()
        else:
            db.session.delete(cart_item)
            db.session.commit()
    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<int:cart_item_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Item removed from cart", "info")
    return redirect(url_for("cart"))


# ========================
# CHECKOUT & ORDERS
# ========================
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty", "warning")
        return redirect(url_for("cart"))
    total = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == "POST":
        shipping_address = request.form.get("shipping_address")
        order = Order(
            user_id=current_user.id,
            total_amount=total,
            shipping_address=shipping_address,
            status="pending",
        )
        db.session.add(order)
        db.session.flush()
        for cart_item in cart_items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                )
            )
        razorpay_order_id = None
        razorpay_amount_paise = None
        if RAZORPAY_ENABLED and razorpay_client:
            try:
                amount_paise = int(round(total * 100))  # INR paise (or cents if you use USD)
                rz_order = razorpay_client.order.create(
                    data={
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": f"order_{order.id}",
                    }
                )
                razorpay_order_id = rz_order["id"]
                razorpay_amount_paise = amount_paise
                order.razorpay_order_id = razorpay_order_id
            except Exception as e:
                flash(f"Razorpay error: {str(e)}. You can place order with mock payment.", "warning")
        db.session.commit()

        return render_template(
            "checkout.html",
            order=order,
            cart_items=cart_items,
            total=total,
            stripe_publishable_key="",
            stripe_enabled=False,
            razorpay_key_id=RAZORPAY_KEY_ID,
            razorpay_enabled=RAZORPAY_ENABLED,
            razorpay_order_id=razorpay_order_id,
            razorpay_amount=razorpay_amount_paise,
            razorpay_currency="INR",
            client_secret=None,
        )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total,
        order=None,
        stripe_publishable_key="",
        stripe_enabled=False,
        razorpay_key_id=RAZORPAY_KEY_ID,
        razorpay_enabled=RAZORPAY_ENABLED,
        client_secret=None,
        razorpay_order_id=None,
        razorpay_amount=None,
        razorpay_currency="INR",
    )


@app.route("/razorpay_payment_success", methods=["POST"])
@login_required
def razorpay_payment_success():
    """Verify Razorpay payment and complete order."""
    if not RAZORPAY_ENABLED or not razorpay_client:
        return jsonify({"success": False, "error": "Razorpay not configured"}), 400
    data = request.get_json() or {}
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({"success": False, "error": "Missing payment details"}), 400

    order = Order.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not order or order.user_id != current_user.id:
        return jsonify({"success": False, "error": "Order not found or access denied"}), 403

    try:
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": "Invalid payment signature"}), 400

    order.payment_status = "completed"
    order.status = "processing"
    order.payment_method = "razorpay"
    order.razorpay_payment_id = razorpay_payment_id
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})


@app.route("/mock_payment/<int:order_id>", methods=["POST"])
@login_required
def mock_payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Access denied", "error")
        return redirect(url_for("orders"))
    order.payment_status = "completed"
    order.status = "processing"
    order.payment_method = "mock"
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Order placed successfully!", "success")
    return redirect(url_for("orders"))


@app.route("/orders")
@login_required
def orders():
    user_orders = (
        Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    )
    return render_template("orders.html", orders=user_orders)


@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Access denied", "error")
        return redirect(url_for("orders"))
    return render_template("order_detail.html", order=order)


# ========================
# FILE UPLOAD ROUTE
# ========================
@app.route("/upload", methods=["POST"])
def upload_file():
    if not supabase:
        return jsonify({"error": "Storage not configured"}), 500

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename
    file_bytes = file.read()

    try:
        supabase.storage.from_("uploads").upload(filename, file_bytes)
        public_url = supabase.storage.from_("uploads").get_public_url(filename)

        return jsonify({
            "message": "File uploaded successfully",
            "url": public_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================
# RUN APP
# ========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Create sample products if database is empty
        if Product.query.count() == 0:
            sample_products = [
                Product(name="MacBook Pro 16\"", description="Powerful laptop for professionals.", price=2499.99, image_url="https://via.placeholder.com/800x800/1e293b/ffffff?text=MacBook", stock=10, category="Electronics"),
                Product(name="Wireless Gaming Mouse", description="Ergonomic mouse with RGB lighting.", price=49.99, image_url="https://via.placeholder.com/800x800/1e293b/ffffff?text=Mouse", stock=50, category="Electronics"),
                Product(name="Mechanical RGB Keyboard", description="Cherry MX switches, programmable keys.", price=129.99, image_url="https://via.placeholder.com/800x800/1e293b/ffffff?text=Keyboard", stock=30, category="Electronics"),
                Product(name="Premium Gaming Headset", description="7.1 surround sound, noise cancellation.", price=89.99, image_url="https://via.placeholder.com/800x800/1e293b/ffffff?text=Headset", stock=25, category="Electronics"),
            ]
            for p in sample_products:
                db.session.add(p)
            db.session.commit()
            print("Sample products created.")

    app.run(debug=True)