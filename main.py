from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)


# DB--------------------------------------------------
class Database:
    def __init__(self, db_name):
        self.db_name = db_name

    def __enter__(self):
        self.con = sqlite3.connect(self.db_name)
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        return self.cur

    def __exit__(self, exc_type, exec_val, exc_tb):
        self.con.commit()
        self.con.close()


# index-------------------------------------------------
@app.route("/")
def get_index():
    return render_template("index.html", title="Home")


# user--------------------------------------------------
@app.route("/user", methods=["GET"])
def get_user():
    return "<h1>This is a user page (GET)</h1>"


@app.route("/user", methods=["POST"])
def post_user():
    return "<h1>This is a user page (POST)</h1>"


@app.route("/user/delete", methods=["POST"])
def delete_user():
    return "<h1>User was deleted</h1>"


# login-------------------------------------------------
@app.route("/login", methods=["GET"])
def get_login():
    return render_template("login.html", title="Login")


@app.route("/login", methods=["POST"])
def auth_user():
    email = request.form.get("email")
    password = request.form.get("password")

    with Database("finance.db") as cursor:
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password),
        )
        user = cursor.fetchone()
        if user is None:
            return render_template(
                "login.html", title="Login", error="Invalid email or password"
            )

    return render_template("dashboard.html", name=user["name"], surname=user["surname"])


# register----------------------------------------------
@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html", title="Register")


@app.route("/register/user", methods=["POST"])
def register_user():
    name = request.form.get("name")
    surname = request.form.get("surname")
    email = request.form.get("email")
    password = request.form.get("password")

    with Database("finance.db") as cursor:
        cursor.execute(
            "INSERT INTO users (name, surname, email, password) VALUES (?, ?, ?, ?)",
            (name, surname, email, password),
        )

    return render_template(
        "register_success.html",
        title="Success",
        name=name,
        surname=surname,
    )


# dashboard----------------------------------------------
@app.route("/dashboard")
def dashboard():
    name = request.args.get("name")
    surname = request.args.get("surname")
    return render_template("dashboard.html", name=name, surname=surname)


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
    return "<h1>This is an income page (GET)</h1>"


@app.route("/income", methods=["POST"])
def post_income():
    return "<h1>This is an income page (POST)</h1>"


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
    return "<h1>This is a spend page (GET)</h1>"


@app.route("/spend", methods=["POST"])
def post_spend():
    return "<h1>This is a spend page (POST)</h1>"


@app.route("/spend/<spend_id>", methods=["GET"])
def get_spend_id(spend_id):
    return f"<h1>This is page for spend id: {spend_id} (GET)</h1>"


@app.route("/spend/<spend_id>/patch", methods=["POST"])
def patch_spend_id(spend_id):
    return f"<h1>Patch for spend with id: {spend_id}</h1>"


@app.route("/spend/<spend_id>/delete", methods=["POST"])
def delete_spend_id(spend_id):
    return f"<h1>The spend with id: {spend_id} was deleted</h1>"


if __name__ == "__main__":
    app.run()
