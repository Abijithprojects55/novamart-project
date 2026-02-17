from datetime import datetime
import os

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------
# App + DB setup
# -------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# ✅ Hosting fix:
# On Render (or any Linux host), writing to project directory may fail.
# Use /tmp which is writable. Locally, use project folder.
if os.environ.get("RENDER") == "1":
    db_path = "/tmp/ecom.db"
else:
    db_path = os.path.join(BASE_DIR, "ecom.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "auth"
login_manager.init_app(app)

# -------------------------
# Models
# -------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, default="User")
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), nullable=False, default="")
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(30), nullable=False, default="ORDERED")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False, index=True)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# Seed products (10)
# -------------------------
def seed_products():
    if Product.query.count() > 0:
        return

    demo = [
        ("Wireless Headphones", "Comfortable over-ear headphones with crisp audio.", 59.99, 12,
         "https://images.unsplash.com/photo-1518441902117-f0a4c2f8e245?auto=format&fit=crop&w=900&q=60"),
        ("Smart Watch", "Track your fitness, notifications, and daily routine.", 89.00, 7,
         "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=60"),
        ("Minimal Desk Lamp", "Warm light, clean design, perfect for study sessions.", 29.50, 18,
         "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?auto=format&fit=crop&w=900&q=60"),
        ("Coffee Grinder", "Fresh grind for better coffee — simple and consistent.", 42.00, 9,
         "https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=900&q=60"),
        ("Travel Backpack", "Durable, roomy, and comfortable for commuting.", 64.99, 15,
         "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=60"),
        ("Portable Speaker", "Loud, clear audio in a compact size.", 34.99, 20,
         "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=900&q=60"),
        ("Mechanical Keyboard", "Tactile typing with a clean, minimalist look.", 79.99, 5,
         "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=60"),
        ("Ceramic Mug Set", "Simple mugs that look good on any desk.", 18.99, 25,
         "https://images.unsplash.com/photo-1511920170033-f8396924c348?auto=format&fit=crop&w=900&q=60"),
        ("Wireless Mouse", "Smooth tracking, ergonomic design, long battery.", 24.99, 22,
         "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=60"),
        ("Notebook Pack", "Premium notebooks for planning and productivity.", 14.50, 40,
         "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=900&q=60"),
    ]

    for name, desc, price, stock, img in demo:
        db.session.add(Product(name=name, description=desc, price=price, stock=stock, image_url=img))
    db.session.commit()

# -------------------------
# DB init (✅ hosting fix)
# Gunicorn won't execute __main__. So we init on import safely.
# -------------------------
_DB_INITIALIZED = False

def init_db_once():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    with app.app_context():
        db.create_all()
        seed_products()
    _DB_INITIALIZED = True

# -------------------------
# Cart helpers (session-based)
# -------------------------
def get_cart():
    return session.get("cart", {})  # {"product_id_as_string": qty}

def save_cart(cart):
    session["cart"] = cart
    session.modified = True

def cart_preview(cart_data):
    items = []
    total = 0.0
    for pid, qty in cart_data.items():
        p = Product.query.get(int(pid))
        if not p:
            continue
        line = p.price * qty
        total += line
        items.append({"p": p, "qty": qty, "line": line})
    return items, total

# -------------------------
# Routes
# -------------------------
@app.get("/")
def home():
    init_db_once()
    return redirect(url_for("products"))

@app.route("/auth", methods=["GET", "POST"])
def auth():
    init_db_once()
    mode = request.args.get("mode", "login")

    if request.method == "POST":
        mode = request.form.get("mode", "login")
        email = (request.form.get("email", "") or "").strip().lower()
        password = request.form.get("password", "") or ""
        name = (request.form.get("name", "User") or "User").strip()

        if mode == "register":
            if not email or "@" not in email:
                flash("Invalid email", "error")
                return redirect(url_for("auth", mode="register"))
            if len(password) < 6:
                flash("Password must be at least 6 characters", "error")
                return redirect(url_for("auth", mode="register"))
            if User.query.filter_by(email=email).first():
                flash("Email already exists", "error")
                return redirect(url_for("auth", mode="register"))

            u = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(u)
            db.session.commit()
            flash("Account created. Please sign in.", "ok")
            return redirect(url_for("auth", mode="login"))

        # login
        u = User.query.filter_by(email=email).first()
        if not u or not check_password_hash(u.password_hash, password):
            flash("Invalid credentials", "error")
            return redirect(url_for("auth", mode="login"))

        login_user(u)
        flash("Signed in successfully ✅", "ok")
        return redirect(url_for("products"))

    return render_template("auth.html", mode=mode, title="Sign in")

@app.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "ok")
    return redirect(url_for("auth", mode="login"))

@app.get("/products")
def products():
    init_db_once()
    q = (request.args.get("q", "") or "").strip().lower()
    items = Product.query.order_by(Product.id.asc()).all()
    if q:
        items = [p for p in items if q in p.name.lower()]
    return render_template("products.html", products=items, q=q, title="Products")

@app.get("/products/<int:pid>")
def product_details(pid):
    init_db_once()
    p = Product.query.get(pid)
    if not p:
        return "Not found", 404
    return render_template("product_details.html", p=p, title=p.name)

@app.post("/cart/add")
def cart_add():
    init_db_once()
    pid = str(request.form.get("product_id", "") or "")
    qty = int(request.form.get("quantity", "1") or 1)
    if not pid:
        return redirect(url_for("products"))
    if qty < 1:
        qty = 1

    p = Product.query.get(int(pid))
    if not p:
        flash("Product not found", "error")
        return redirect(url_for("products"))
    if p.stock <= 0:
        flash("Out of stock", "error")
        return redirect(url_for("products"))

    cart = get_cart()
    cart[pid] = cart.get(pid, 0) + qty
    save_cart(cart)
    flash("Added to cart ✅", "ok")
    return redirect(url_for("cart"))

@app.post("/cart/remove")
def cart_remove():
    init_db_once()
    pid = str(request.form.get("product_id", "") or "")
    cart = get_cart()
    cart.pop(pid, None)
    save_cart(cart)
    flash("Removed from cart", "ok")
    return redirect(url_for("cart"))

@app.get("/cart")
def cart():
    init_db_once()
    items, total = cart_preview(get_cart())
    return render_template("cart.html", items=items, total=total, title="Cart")

# ✅ Checkout page (GET) endpoint name is "checkout"
@app.get("/checkout")
@login_required
def checkout():
    init_db_once()
    cart_data = get_cart()
    if not cart_data:
        flash("Cart is empty", "error")
        return redirect(url_for("cart"))

    items, total = cart_preview(cart_data)
    return render_template("checkout.html", items=items, total=total, title="Checkout")

# ✅ Checkout submit (POST) endpoint name is "checkout_submit"
@app.post("/checkout")
@login_required
def checkout_submit():
    init_db_once()

    name_on_card = (request.form.get("name_on_card", "") or "").strip()
    card_number = (request.form.get("card_number", "") or "").strip().replace(" ", "")
    expiry = (request.form.get("expiry", "") or "").strip()
    cvv = (request.form.get("cvv", "") or "").strip()

    if not name_on_card or len(card_number) < 12 or not expiry or len(cvv) < 3:
        flash("Payment details invalid (demo). Please fill all fields.", "error")
        return redirect(url_for("checkout"))

    cart_data = get_cart()
    if not cart_data:
        flash("Cart is empty", "error")
        return redirect(url_for("cart"))

    # Validate stock + compute total
    items = []
    total = 0.0
    for pid, qty in cart_data.items():
        p = Product.query.get(int(pid))
        if not p:
            flash("Invalid cart item", "error")
            return redirect(url_for("cart"))
        if qty > p.stock:
            flash(f"Insufficient stock for {p.name}", "error")
            return redirect(url_for("cart"))

        items.append((p, qty))
        total += p.price * qty

    # Create order
    o = Order(user_id=current_user.id, total_amount=total, status="ORDERED")
    db.session.add(o)
    db.session.commit()

    # Create order items + reduce stock
    for p, qty in items:
        db.session.add(OrderItem(
            order_id=o.id,
            product_id=p.id,
            product_name=p.name,
            quantity=qty,
            unit_price=p.price,
        ))
        p.stock -= qty

    db.session.commit()

    save_cart({})
    last4 = card_number[-4:] if len(card_number) >= 4 else "0000"
    flash(f"Payment approved (demo) ✅ Order placed! (Card •••• {last4})", "ok")
    return redirect(url_for("orders"))

@app.get("/orders")
@login_required
def orders():
    init_db_once()
    orders_list = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    enriched = []
    for o in orders_list:
        lines = OrderItem.query.filter_by(order_id=o.id).all()
        enriched.append({"o": o, "lines": lines})
    return render_template("orders.html", orders=enriched, title="Orders")


# ✅ Ensure DB is initialized when the app is imported (gunicorn)
init_db_once()

if __name__ == "__main__":
    # Render (and most hosts) provide PORT; bind to 0.0.0.0 so it’s publicly reachable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


