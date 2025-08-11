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
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fdbfufjdhvjbaijnvjhbrbakvndvavnvpopzacdr"


# ---------------- DB ----------------
class Database:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.con = None
        self.cur = None

    def __enter__(self):
        self.con = sqlite3.connect(self.db_name)
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        return self.cur

    def __exit__(self, exc_type, exec_val, exc_tb):
        self.con.commit()
        self.con.close()


# --------- Глобальная защита + g.user ---------
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

    with Database("finance.db") as cursor:
        cursor.execute(
            "SELECT id, name, surname, email, password FROM users WHERE email = ? AND password = ?",
            (email, password),
        )
        user = cursor.fetchone()

    if user is None:
        return render_template(
            "login.html", title="Login", error="Invalid email or password"
        )

    session["user"] = {
        "id": user["id"],
        "name": user["name"],
        "surname": user["surname"],
        "email": user["email"],
    }
    flash("Logged in successfully.")
    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    if "user" in session:
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
    name = request.form.get("name")
    surname = request.form.get("surname")
    email = request.form.get("email")
    password = request.form.get("password")

    if not all([name, surname, email, password]):
        return render_template(
            "register.html",
            title="Register",
            error="All fields are required",
            name=name,
            surname=surname,
            email=email,
        )

    with Database("finance.db") as cursor:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        exists = cursor.fetchone()
        if exists:
            return render_template(
                "register.html",
                title="Register",
                error="Email already exists",
                name=name,
                surname=surname,
                email=email,
            )
        cursor.execute(
            "INSERT INTO users (name, surname, email, password) VALUES (?, ?, ?, ?)",
            (name, surname, email, password),
        )
        user_id = cursor.lastrowid

    session["user"] = {"id": user_id, "name": name, "surname": surname, "email": email}
    flash("Registration successful. You are now logged in.")
    return redirect(url_for("dashboard"))


# --- форматтеры для шаблонов ---
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
    """ теперь для value в <input type=datetime-local> """
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


# --- dashboard ---
@app.route("/dashboard")
def dashboard():
    uid = g.user["id"]

    with Database("finance.db") as cur:
         # Категории: системные (owner_id=1) + пользовательские
        cur.execute(
            """
            SELECT id, name, owner_id
            FROM categories
            WHERE owner_id IN (1, ?)
            ORDER BY CASE WHEN owner_id=1 THEN 0 ELSE 1 END, name
            """,
            (uid,),
        )
        categories = [dict(r) for r in cur.fetchall()]

        # INCOME
        cur.execute(
            """
            SELECT ut.id, datetime(ut.date/1000, 'unixepoch', 'localtime') AS date_str, ut.description, ut.amount,
                   c.name AS category
            FROM user_transactions ut
            LEFT JOIN categories c ON c.id = ut.category_id
            WHERE ut.owner_id = ? AND ut.type = 'income'
            ORDER BY ut.date DESC
            """,
            (uid,),
        )
        incomes = [dict(r) for r in cur.fetchall()]

        # SPEND
        cur.execute(
            """
            SELECT ut.id, datetime(ut.date/1000, 'unixepoch', 'localtime') AS date_str, ut.description, ut.amount,
                   c.name AS category
            FROM user_transactions ut
            LEFT JOIN categories c ON c.id = ut.category_id
            WHERE ut.owner_id = ? AND ut.type = 'spend'
            ORDER BY ut.date DESC
            """,
            (uid,),
        )
        spends = [dict(r) for r in cur.fetchall()]

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


# income------------------------------------------------
@app.route("/income", methods=["GET"])
def get_income():
    uid = g.user["id"]
    with Database("finance.db") as cur:
        # системные + пользовательские категории
        cur.execute("SELECT id, name FROM categories WHERE owner_id = 1 ORDER BY name")
        sys_categories = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT id, name FROM categories WHERE owner_id = ? ORDER BY name", (uid,))
        user_categories = [dict(r) for r in cur.fetchall()]

    return render_template(
        "income_form.html",
        title="Add Income",
        sys_categories=sys_categories,
        user_categories=user_categories,
        now_value=now_local_input(),
    )


@app.route("/income", methods=["POST"])
def post_income():
    uid = g.user["id"]
    f = request.form
    category_id = int(f.get("category_id"))
    amount = float(f.get("amount", 0) or 0)
    description = (f.get("description") or "").strip()
    date_ms = parse_datetime_local(f.get("date")) or int(datetime.now().timestamp() * 1000)

    with Database("finance.db") as cur:
        cur.execute(
            """
            INSERT INTO user_transactions (amount, description, category_id, date, owner_id, type)
            VALUES (?, ?, ?, ?, ?, 'income')
            """,
            (amount, description, category_id, date_ms, uid),
        )
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


# spend-------------------------------------------------
@app.route("/spend", methods=["GET"])
def get_spend():
    uid = g.user["id"]
    with Database("finance.db") as cur:
        cur.execute("SELECT id, name FROM categories WHERE owner_id = 1 ORDER BY name")
        sys_categories = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT id, name FROM categories WHERE owner_id = ? ORDER BY name", (uid,))
        user_categories = [dict(r) for r in cur.fetchall()]

    return render_template(
        "spend_form.html",
        title="Add Spend",
        sys_categories=sys_categories,
        user_categories=user_categories,
        now_value=now_local_input(),
    )


@app.route("/spend", methods=["POST"])
def post_spend():
    uid = g.user["id"]
    f = request.form
    category_id = int(f.get("category_id"))
    amount = float(f.get("amount", 0) or 0)
    description = (f.get("description") or "").strip()
    date_ms = parse_datetime_local(f.get("date")) or int(datetime.now().timestamp() * 1000)

    with Database("finance.db") as cur:
        cur.execute(
            """
            INSERT INTO user_transactions (amount, description, category_id, date, owner_id, type)
            VALUES (?, ?, ?, ?, ?, 'spend')
            """,
            (amount, description, category_id, date_ms, uid),
        )
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
