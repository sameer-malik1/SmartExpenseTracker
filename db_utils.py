# db_utils.py
import sqlite3
from datetime import date

def init_db(db_path="expenses.db"):
    """Initialize the SQLite database and create the expenses table if it doesn't exist."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        note TEXT,
        date TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
    """)
    conn.commit()
    return conn

def add_expense(conn, amount, category, note=None, date_str=None):
    """Insert a new expense into the database."""
    if date_str is None:
        date_str = date.today().isoformat()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (amount, category, note, date) VALUES (?, ?, ?, ?)",
        (amount, category, note, date_str)
    )
    conn.commit()
    return cur.lastrowid

def list_expenses(conn, start_date, end_date):
    """Retrieve expenses between two dates (inclusive)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, amount, category, note, date FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date",
        (start_date, end_date)
    )
    rows = cur.fetchall()
    return [dict(zip(["id", "amount", "category", "note", "date"], row)) for row in rows]
