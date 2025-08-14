from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g,
    request as req,
)
import sqlite3
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, case
from sqlalchemy.orm import relationship
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fdbfufjdhvjbaijnvjhbrbakvndvavnvpopzacdr"

# ---------- SQLAlchemy setup ----------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "finance.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    __tablename__ = "users"
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String, nullable=False)
    surname  = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    email    = db.Column(db.String, nullable=False)

    categories   = relationship("Category", back_populates="owner")
    transactions = relationship("UserTransaction", back_populates="owner")


class Category(db.Model):
    __tablename__ = "categories"
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String, nullable=False)
    owner_id = db.Column(db.Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="categories")
    transactions = relationship("UserTransaction", back_populates="category")


class UserTransaction(db.Model):
    __tablename__ = "user_transactions"
    id          = db.Column(db.Integer, primary_key=True)
    amount      = db.Column(db.Float,   nullable=False)
    description = db.Column(db.String,  nullable=True)
    category_id = db.Column(db.Integer, ForeignKey("categories.id"), nullable=True)
    date        = db.Column(db.Integer, nullable=False)  # epoch ms
    owner_id    = db.Column(db.Integer, ForeignKey("users.id"), nullable=False)
    type        = db.Column(db.String,  nullable=False)  # 'income' | 'spend'

    category = relationship("Category", back_populates="transactions")
    owner    = relationship("User", back_populates="transactions")


# Create tables if not present (safe for existing DB)
with app.app_context():
    db.create_all()

# # ---------------- DB ----------------
# class DB:
#     def __init__(self, db_name: str):
#         self.db_name = db_name
#         self.con = None
#         self.cur = None

#     def __enter__(self):
#         self.con = sqlite3.connect(self.db_name)
#         self.con.row_factory = sqlite3.Row
#         self.cur = self.con.cursor()
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.con.commit()
#         self.con.close()

#     # ---------- public ----------
#     def select(
#         self,
#         table: str,
#         columns="*",
#         where: dict | str | None = None,
#         joins: str | None = None,
#         order_by: str | None = None,
#         limit: int | None = None,
#         one: bool = False,
#     ):
#         cols = (
#             ", ".join(columns) if isinstance(columns, (list, tuple)) else str(columns)
#         )
#         sql = f"SELECT {cols} FROM {table}"
#         if joins:
#             sql += f" {joins}"
#         where_sql, params = self._build_where(where)
#         if where_sql:
#             sql += f" WHERE {where_sql}"
#         if order_by:
#             sql += f" ORDER BY {order_by}"
#         if limit is not None:
#             sql += " LIMIT ?"
#             params.append(int(limit))

#         self.cur.execute(sql, params)
#         if one:
#             row = self.cur.fetchone()
#             return dict(row) if row else None
#         return [dict(r) for r in self.cur.fetchall()]

#     def insert(self, table: str, data: dict) -> int:
#         keys = list(data.keys())
#         placeholders = ",".join(["?"] * len(keys))
#         sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})"
#         self.cur.execute(sql, [data[k] for k in keys])
#         return self.cur.lastrowid

#     # ---------- helpers ----------
#     def _build_where(self, where):
#         if not where:
#             return "", []
#         if isinstance(where, str):
#             # используйте осторожно; лучше передавать dict
#             return where, []
#         clauses, params = [], []
#         for key, val in where.items():
#             # ('>=', 10) / ('LIKE', '%abc%') / ('IN', [1,2,3])
#             if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], str):
#                 op, v = val[0].upper(), val[1]
#                 if op == "IN" and isinstance(v, (list, tuple, set)):
#                     ph = ",".join("?" for _ in v)
#                     clauses.append(f"{key} IN ({ph})")
#                     params.extend(v)
#                 else:
#                     clauses.append(f"{key} {op} ?")
#                     params.append(v)
#             elif isinstance(val, (list, tuple, set)):
#                 ph = ",".join("?" for _ in val)
#                 clauses.append(f"{key} IN ({ph})")
#                 params.extend(val)
#             else:
#                 clauses.append(f"{key} = ?")
#                 params.append(val)
#         return " AND ".join(clauses), params


# ------------ Auth gate ------------
@app.before_request
def auth_gate():
    g.user = session.get("user")

    allow_anon = {
        "get_index",
        "get_login",
        "auth_user",
        "register",
        "register_user",
        "static",
    }

    if g.user is None and (req.endpoint not in allow_anon):
        return redirect(url_for("get_index"))


# ---------------- Index ----------------
@app.route("/")
def get_index():
    return render_template("index.html", title="Home")


# -------- Login / Logout --------
@app.route("/login", methods=["GET"])
def get_login():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("login.html", title="Login")


@app.route("/login", methods=["POST"])
def auth_user():
    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email, password=password).first()
    if not user:
        return render_template("login.html", title="Login", error="Invalid email or password")

    session["user"] = {"id": user.id, "name": user.name, "surname": user.surname, "email": user.email}
    flash("Logged in successfully.")
    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    flash("Logged out.")
    return redirect(url_for("get_index"))


# -------- Register --------
@app.route("/register", methods=["GET"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("register.html", title="Register")


@app.route("/register/user", methods=["POST"])
def register_user():
    name = (request.form.get("name") or "").strip()
    surname = (request.form.get("surname") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    if not all([name, surname, email, password]):
        return render_template("register.html", title="Register",
                               error="All fields are required", name=name, surname=surname, email=email)

    exists = User.query.filter_by(email=email).first()
    if exists:
        return render_template("register.html", title="Register",
                               error="Email already exists", name=name, surname=surname, email=email)

    new_user = User(name=name, surname=surname, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    session["user"] = {"id": new_user.id, "name": name, "surname": surname, "email": email}
    flash("Registration successful. You are now logged in.")
    return redirect(url_for("dashboard"))


# -------- Filters & helpers --------
@app.template_filter("fmtdate")
def fmtdate(value, tz="local"):
    if value in (None, "", "0"):
        return ""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return str(value)
    # авто-определение: секунды vs миллисекунды
    if v > 10**12:
        v = v / 1000.0
    dt = datetime.fromtimestamp(v) if tz == "local" else datetime.utcfromtimestamp(v)
    return dt.strftime("%Y-%m-%d")


def parse_datetime_local(s: str) -> int | None:
    """
    Принимает 'YYYY-MM-DDTHH:MM' из <input type="datetime-local">
    Возвращает epoch в миллисекундах.
    """
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%dT%H:%M")
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def now_local_input() -> str:
    """теперь для value в <input type=datetime-local>"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


# --------------- Dashboard ---------------
@app.route("/dashboard")
def dashboard():
    uid = g.user["id"]

    # Categories: system (owner_id=1) + user's; order system first by name
    categories = (
        Category.query
        .filter(Category.owner_id.in_([1, uid]))
        .order_by(case((Category.owner_id == 1, 0), else_=1), Category.name)
        .all()
    )

    incomes = (
        UserTransaction.query
        .filter_by(owner_id=uid, type="income")
        .order_by(UserTransaction.date.desc())
        .all()
    )
    spends = (
        UserTransaction.query
        .filter_by(owner_id=uid, type="spend")
        .order_by(UserTransaction.date.desc())
        .all()
    )

    return render_template(
        "dashboard.html",
        title="Dashboard",
        name=g.user["name"],
        surname=g.user["surname"],
        categories=categories,
        incomes=incomes,
        spends=spends,
    )


# category----------------------------------------------
@app.route("/category", methods=["GET"])
def get_category():
    return "<h1>This is a category page (GET)</h1>"


@app.route("/category", methods=["POST"])
def post_category():
    return "<h1>This is a category page (POST)</h1>"


@app.route("/category/<category_id>", methods=["GET"])
def get_category_id(category_id):
    return f"<h1>This is page for category id: {category_id} (GET)</h1>"


@app.route("/category/<category_id>/patch", methods=["POST"])
def patch_category_id(category_id):
    return f"<h1>Patch for category with id: {category_id}</h1>"


@app.route("/category/<category_id>/delete", methods=["POST"])
def delete_category_id(category_id):
    return f"<h1>The category with id: {category_id} was deleted</h1>"


# ------------------ Income -----------------------
@app.route("/income", methods=["GET"])
def get_income():
    uid = g.user["id"]
    sys_categories  = Category.query.filter_by(owner_id=1).order_by(Category.name).all()
    user_categories = Category.query.filter_by(owner_id=uid).order_by(Category.name).all()
    return render_template("income_form.html", title="Add Income",
                           sys_categories=sys_categories, user_categories=user_categories,
                           now_value=now_local_input())

@app.route("/income", methods=["POST"])
def post_income():
    uid = g.user["id"]
    f = request.form
    tx = UserTransaction(
        amount=float(f.get("amount", 0) or 0),
        description=(f.get("description") or "").strip(),
        category_id=int(f.get("category_id")) if f.get("category_id") else None,
        date=parse_datetime_local(f.get("date")) or int(datetime.now().timestamp() * 1000),
        owner_id=uid,
        type="income",
    )
    db.session.add(tx)
    db.session.commit()
    flash("Income added.")
    return redirect(url_for("dashboard"))


@app.route("/income/<income_id>", methods=["GET"])
def get_income_id(income_id):
    return f"<h1>This is page for income id: {income_id} (GET)</h1>"


@app.route("/income/<income_id>/patch", methods=["POST"])
def patch_income_id(income_id):
    return f"<h1>Patch for income with id: {income_id}</h1>"


@app.route("/income/<income_id>/delete", methods=["POST"])
def delete_income_id(income_id):
    return f"<h1>The income with id: {income_id} was deleted</h1>"


# ------------------------ Spend ----------------------------
@app.route("/spend", methods=["GET"])
def get_spend():
    uid = g.user["id"]
    sys_categories  = Category.query.filter_by(owner_id=1).order_by(Category.name).all()
    user_categories = Category.query.filter_by(owner_id=uid).order_by(Category.name).all()
    return render_template("spend_form.html", title="Add Spend",
                           sys_categories=sys_categories, user_categories=user_categories,
                           now_value=now_local_input())

@app.route("/spend", methods=["POST"])
def post_spend():
    uid = g.user["id"]
    f = request.form
    tx = UserTransaction(
        amount=float(f.get("amount", 0) or 0),
        description=(f.get("description") or "").strip(),
        category_id=int(f.get("category_id")) if f.get("category_id") else None,
        date=parse_datetime_local(f.get("date")) or int(datetime.now().timestamp() * 1000),
        owner_id=uid,
        type="spend",
    )
    db.session.add(tx)
    db.session.commit()
    flash("Spend added.")
    return redirect(url_for("dashboard"))


@app.route("/spend/<spend_id>", methods=["GET"])
def get_spend_id(spend_id):
    return f"<h1>This is page for spend id: {spend_id} (GET)</h1>"


@app.route("/spend/<spend_id>/patch", methods=["POST"])
def patch_spend_id(spend_id):
    return f"<h1>Patch for spend with id: {spend_id}</h1>"


@app.route("/spend/<spend_id>/delete", methods=["POST"])
def delete_spend_id(spend_id):
    return f"<h1>The spend with id: {spend_id} was deleted</h1>"


# ---------------- Main ----------------
if __name__ == "__main__":
    app.run(debug=True)
