import sqlite3
import hashlib
import os
import pandas as pd
from datetime import datetime



DB_NAME = "finsecure.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL,
        password_hash TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        category TEXT,
        amount REAL NOT NULL,
        note TEXT,
        date TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        value REAL NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        interest_rate REAL NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS login_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        login_time TEXT NOT NULL)""")
    conn.commit()
    conn.close()


# ---------- Users and passwords ----------
def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 100_000
    ).hex()


def create_user(username, password):
    salt = os.urandom(16).hex()
    pw_hash = _hash_password(password, salt)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
            (username, salt, pw_hash),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # username already exists
    finally:
        conn.close()


def verify_user(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, salt, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    if row and _hash_password(password, row[1]) == row[2]:
        return row[0]
    return None


# ---------- Transactions ----------
def add_transaction(user_id, kind, category, amount, note, date):
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions (user_id, kind, category, amount, note, date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, kind, category, amount, note, date),
    )
    conn.commit()
    conn.close()


def get_transactions(user_id):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, date, kind, category, amount, note FROM transactions "
        "WHERE user_id = ? ORDER BY date DESC",
        conn, params=(user_id,),
    )
    conn.close()
    return df


# ---------- Assets ----------
def add_asset(user_id, name, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO assets (user_id, name, value) VALUES (?, ?, ?)",
        (user_id, name, value),
    )
    conn.commit()
    conn.close()


def get_assets(user_id):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, name, value FROM assets WHERE user_id = ?",
        conn, params=(user_id,),
    )
    conn.close()
    return df


# ---------- Loans ----------
def add_loan(user_id, name, amount, interest_rate):
    conn = get_connection()
    conn.execute(
        "INSERT INTO loans (user_id, name, amount, interest_rate) VALUES (?, ?, ?, ?)",
        (user_id, name, amount, interest_rate),
    )
    conn.commit()
    conn.close()


def get_loans(user_id):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, name, amount, interest_rate FROM loans WHERE user_id = ?",
        conn, params=(user_id,),
    )
    conn.close()
    return df


# ---------- Delete ----------
def delete_record(table, record_id, user_id):
    if table not in ("transactions", "assets", "loans"):
        return
    conn = get_connection()
    conn.execute(
        f"DELETE FROM {table} WHERE id = ? AND user_id = ?",
        (record_id, user_id),
    )
    conn.commit()
    conn.close()
    # ---------- Login tracking ----------
def record_login(user_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO login_log (user_id, login_time) VALUES (?, ?)",
        (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_login_stats():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d") + "%"
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_logins = conn.execute("SELECT COUNT(*) FROM login_log").fetchone()[0]
    logins_today = conn.execute(
        "SELECT COUNT(*) FROM login_log WHERE login_time LIKE ?", (today,)
    ).fetchone()[0]
    users_today = conn.execute(
        "SELECT COUNT(DISTINCT user_id) FROM login_log WHERE login_time LIKE ?",
        (today,),
    ).fetchone()[0]
    recent = pd.read_sql_query(
        "SELECT users.username, login_log.login_time FROM login_log "
        "JOIN users ON users.id = login_log.user_id "
        "ORDER BY login_log.id DESC LIMIT 20",
        conn,
    )
    conn.close()
    return total_users, total_logins, logins_today, users_today, recent
