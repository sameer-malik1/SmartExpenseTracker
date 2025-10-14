from fastmcp import FastMCP
from db_utils import init_db, add_expense as db_add, list_expenses as db_list
from datetime import datetime
from typing import Optional, Dict, List

mcp = FastMCP(name="Expense Tracker")
conn = init_db("expenses.db")

@mcp.tool()
def add_expense(amount: float, category: str, note: Optional[str] = None, date: Optional[str] = None) -> Dict:
    if not date:
        date = datetime.utcnow().date().isoformat()
    if amount <= 0:
        return {"ok": False, "message": "Amount must be positive."}
    eid = db_add(conn, amount, category, note, date)
    return {"ok": True, "id": eid, "message": f"Added {amount} to {category}"}

@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> List[Dict]:
    return db_list(conn, start_date, end_date)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
