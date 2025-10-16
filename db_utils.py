# db_utils.py
import sqlite3
from datetime import date
import bcrypt
import statistics



def init_db(db_path="expenses.db"):
    """Initialize the SQLite database and create the expenses table if it doesn't exist."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()
    # Enable foreign key support
    cur.execute("PRAGMA foreign_keys = ON;")

    cur.executescript("""
    -- Table for user accounts
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        created_at TEXT DEFAULT (DATE('now'))
    );

    -- Table for tracking expenses
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        note TEXT,
        date TEXT NOT NULL,
        created_at TEXT DEFAULT (DATETIME('now')),
        updated_at TEXT DEFAULT (DATETIME('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Useful indexes
    CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
    CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
    CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
    """)
    conn.commit()
    return conn

def hash_password(password: str) -> str:
    """Hash a password for storage."""
    byte = password.encode('utf-8')
    hashed = bcrypt.hashpw(byte, bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Check if a plaintext password matches the stored hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

conn = init_db("expenses.db")

def register_user(name, email, password):
    """Register a new user."""
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hash_password(password))
        )
        conn.commit()
        return {"ok": True, "message": "User registered successfully."}
    except sqlite3.IntegrityError:
        return {"ok": False, "message": "Email already exists."}

def login_user(email, password):
    """Authenticate a user by email and password."""
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    print('login user:', user)
    if not user:
        return {"ok": False, "message": "User not found."}
    if not verify_password(password, user[3]):
        print('user[password]',user[3])
        print('hashed password',hash_password(password))
        return {"ok": False, "message": "Incorrect password."}
    return {"ok": True, "user": {"id": user[0], "name": user[1], "email": user[2]}}

def add_expense(user_id, amount, category, note=None, date_str=None):
    """Insert a new expense into the database for a specific user."""
    if date_str is None:
        date_str = date.today().isoformat()

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO expenses (user_id, amount, category, note, date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, category, note, date_str)
    )
    conn.commit()
    return cur.lastrowid


def list_expenses(user_id, start_date=None, end_date=None):
    """Retrieve all expenses for a specific user between dates."""
    cur = conn.cursor()

    query = """
        SELECT id, amount, category, note, date
        FROM expenses
        WHERE user_id = ?
    """
    params = [user_id]

    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [start_date, end_date]
    elif start_date:
        query += " AND date >= ?"
        params.append(start_date)
    elif end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date"
    cur.execute(query, params)

    rows = cur.fetchall()
    return [dict(zip(["id", "amount", "category", "note", "date"], row)) for row in rows]

def delete_expense(user_id, expense_id):
    """Delete an expense if it belongs to the user."""
    cur = conn.cursor()
    
    # First check if the expense exists and belongs to the user
    cur.execute(
        "SELECT id, amount, category FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    expense = cur.fetchone()
    
    if not expense:
        return {"ok": False, "message": f"Expense {expense_id} not found or does not belong to you."}
    
    # Delete the expense
    cur.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    conn.commit()
    
    return {
        "ok": True, 
        "message": f"Successfully deleted expense #{expense_id} (${expense[1]:.2f} for {expense[2]})"
    }


def update_expense(user_id, expense_id, amount=None, category=None, note=None, date_str=None):
    """Update an expense if it belongs to the user."""
    cur = conn.cursor()
    
    # First check if the expense exists and belongs to the user
    cur.execute(
        "SELECT id FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    expense = cur.fetchone()
    
    if not expense:
        return {"ok": False, "message": f"Expense {expense_id} not found or does not belong to you."}
    
    # Build update query dynamically based on provided fields
    updates = []
    params = []
    
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if note is not None:
        updates.append("note = ?")
        params.append(note)
    if date_str is not None:
        updates.append("date = ?")
        params.append(date_str)
    
    if not updates:
        return {"ok": False, "message": "No fields to update."}
    
    updates.append("updated_at = DATETIME('now')")
    params.extend([expense_id, user_id])
    
    query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
    cur.execute(query, params)
    conn.commit()
    
    return {"ok": True, "message": f"Successfully updated expense #{expense_id}"}


def get_expense_analytics(user_id, start_date=None, end_date=None, group_by="category"):
    print('get_expense_analytics called with:', user_id, start_date, end_date, group_by)
    """Get detailed analytics for user expenses."""
    cur = conn.cursor()
    
    # Get all expenses in the date range
    query = "SELECT amount, category, date FROM expenses WHERE user_id = ?"
    params = [user_id]
    
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [start_date, end_date]
    elif start_date:
        query += " AND date >= ?"
        params.append(start_date)
    elif end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    cur.execute(query, params)
    expenses = cur.fetchall()
    
    if not expenses:
        return {
            "ok": True,
            "message": "No expenses found for the given period.",
            "count": 0,
            "total": 0
        }
    
    amounts = [exp[0] for exp in expenses]
    
    # Calculate statistics
    total = sum(amounts)
    mean = statistics.mean(amounts)
    median = statistics.median(amounts)
    
    # Standard deviation (only if we have more than 1 expense)
    std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0
    
    # Group by the specified field
    grouped = {}
    if group_by == "category":
        for amount, category, _ in expenses:
            grouped[category] = grouped.get(category, 0) + amount
    elif group_by == "date":
        for amount, _, exp_date in expenses:
            grouped[exp_date] = grouped.get(exp_date, 0) + amount
    elif group_by == "month":
        for amount, _, exp_date in expenses:
            month = exp_date[:7]  # YYYY-MM
            grouped[month] = grouped.get(month, 0) + amount
    
    # Sort grouped data by value (descending)
    grouped_sorted = dict(sorted(grouped.items(), key=lambda x: x[1], reverse=True))
    
    # Find most expensive category/period
    top_category = max(grouped.items(), key=lambda x: x[1]) if grouped else None
    
    return {
        "ok": True,
        "count": len(expenses),
        "total": round(total, 2),
        "mean": round(mean, 2),
        "median": round(median, 2),
        "std_dev": round(std_dev, 2),
        "min": round(min(amounts), 2),
        "max": round(max(amounts), 2),
        "grouped_by": group_by,
        "grouped_data": {k: round(v, 2) for k, v in grouped_sorted.items()},
        "top_spending": {
            "category": top_category[0] if top_category else None,
            "amount": round(top_category[1], 2) if top_category else 0
        },
        "message": f"Analysis complete: {len(expenses)} expenses, ${total:.2f} total, ${mean:.2f} average"
    }

