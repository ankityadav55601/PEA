from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = (
    "super_secret_key_for_college_project"  # Required for login sessions
)


def init_db():
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  # Users table
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
  # Transactions table linked with user_id
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
  conn.commit()
  conn.close()


@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "POST":
    username = request.form["username"]
    password = generate_password_hash(request.form["password"])

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
      cursor.execute(
          "INSERT INTO users (username, password) VALUES (?, ?)",
          (username, password),
      )
      conn.commit()
      conn.close()
      return redirect(url_for("login"))
    except sqlite3.IntegrityError:
      conn.close()
      return render_template(
          "register.html", error="Username already exists!"
      )

  return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):
      session["user_id"] = user[0]
      session["username"] = user[1]
      return redirect(url_for("index"))
    else:
      return render_template("login.html", error="Invalid username or password")

  return render_template("login.html")


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
  if "user_id" not in session:
    return redirect(url_for("login"))

  user_id = session["user_id"]
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()

  if request.method == "POST":
    title = request.form["title"]
    amount = float(request.form["amount"])
    category = request.form["category"]
    date = request.form["date"] or datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "INSERT INTO transactions (user_id, title, amount, category, date)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, title, amount, category, date),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

  # Fetch ONLY current user's transactions
  cursor.execute(
      "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC",
      (user_id,),
  )
  transactions = cursor.fetchall()

  # Calculate metrics for current user only
  cursor.execute(
      "SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,)
  )
  total_spent = cursor.fetchone()[0] or 0.0

  # Category breakdown for current user only
  cursor.execute(
      "SELECT category, SUM(amount) FROM transactions WHERE user_id = ? GROUP"
      " BY category",
      (user_id,),
  )
  category_data = cursor.fetchall()
  categories = [row[0] for row in category_data]
  amounts = [row[1] for row in category_data]

  conn.close()

  return render_template(
      "index.html",
      transactions=transactions,
      total_spent=total_spent,
      categories=categories,
      amounts=amounts,
      username=session["username"],
  )


@app.route("/delete/<int:id>")
def delete_transaction(id):
  if "user_id" not in session:
    return redirect(url_for("login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  # Ensure user can only delete their own transactions
  cursor.execute(
      "DELETE FROM transactions WHERE id = ? AND user_id = ?",
      (id, session["user_id"]),
  )
  conn.commit()
  conn.close()
  return redirect(url_for("index"))


if __name__ == "__main__":
  init_db()
  app.run(debug=True)