from fastmcp import FastMCP
from db_utils import ( init_db, add_expense as db_add, list_expenses as db_list,
                      delete_expense as db_delete,
                    update_expense as db_update,
                        get_expense_analytics as db_analytics)
from datetime import datetime
from typing import Optional, Dict, List
import logging

# Set up logging to suppress unnecessary warnings
logging.basicConfig(level=logging.WARNING)

mcp = FastMCP(name="Expense Tracker")
conn = init_db("expenses.db")

@mcp.tool()
def add_expense(user_id: int, amount: float, category: str, note: Optional[str] = None, date: Optional[str] = None) -> Dict:
    """Add a new expense for a user.
    
    Args:
        user_id: The ID of the user adding the expense
        amount: The amount of the expense (must be positive)
        category: The category of the expense (e.g., 'food', 'travel', 'entertainment')
        note: Optional note or description for the expense
        date: Optional date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Dictionary with 'ok' status, 'id' of created expense, and a message
    """
    try:
        if not date:
            date = datetime.utcnow().date().isoformat()
        
        if amount <= 0:
            return {"ok": False, "message": "Amount must be positive."}

        eid = db_add(user_id, amount, category, note, date)
        return {
            "ok": True, 
            "id": eid, 
            "message": f"Successfully added expense: ${amount:.2f} for {category}"
        }
    except Exception as e:
        return {"ok": False, "message": f"Error adding expense: {str(e)}"}


@mcp.tool()
def list_expenses(user_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    """List expenses for a specific user between two dates.
    
    Args:
        user_id: The ID of the user whose expenses to retrieve
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Dictionary with 'ok' status, 'expenses' list, and summary information
    """
    try:
        expenses = db_list(user_id, start_date, end_date)
        
        total = sum(exp['amount'] for exp in expenses)
        
        # Group by category
        by_category = {}
        for exp in expenses:
            cat = exp['category']
            by_category[cat] = by_category.get(cat, 0) + exp['amount']
        
        return {
            "ok": True,
            "expenses": expenses,
            "total": total,
            "count": len(expenses),
            "by_category": by_category,
            "message": f"Found {len(expenses)} expense(s) totaling ${total:.2f}"
        }
    except Exception as e:
        return {"ok": False, "message": f"Error listing expenses: {str(e)}"}
    
@mcp.tool()
def delete_expense(user_id: int, expense_id: int) -> Dict:
    """Delete an expense by ID.
    
    Args:
        user_id: The ID of the user who owns the expense
        expense_id: The ID of the expense to delete
    
    Returns:
        Dictionary with 'ok' status and a message
    """
    try:
        result = db_delete(user_id, expense_id)
        return result
    except Exception as e:
        return {"ok": False, "message": f"Error deleting expense: {str(e)}"}


@mcp.tool()
def edit_expense(
    user_id: int, 
    expense_id: int, 
    amount: Optional[float] = None, 
    category: Optional[str] = None, 
    note: Optional[str] = None, 
    date: Optional[str] = None
) -> Dict:
    """Edit an existing expense. Only provide the fields you want to update.
    
    Args:
        user_id: The ID of the user who owns the expense
        expense_id: The ID of the expense to edit
        amount: Optional new amount (must be positive if provided)
        category: Optional new category
        note: Optional new note
        date: Optional new date in YYYY-MM-DD format
    
    Returns:
        Dictionary with 'ok' status and a message
    """
    try:
        if amount is not None and amount <= 0:
            return {"ok": False, "message": "Amount must be positive."}
        
        result = db_update(user_id, expense_id, amount, category, note, date)
        return result
    except Exception as e:
        return {"ok": False, "message": f"Error editing expense: {str(e)}"}


@mcp.tool()
def get_expense_analysis(
    user_id: int, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    group_by: Optional[str] = "category"
) -> Dict:
    print("get_expense_analysis called with:", user_id, start_date, end_date, group_by)
    """Get detailed analytics and statistics for expenses.
    
    Args:
        user_id: The ID of the user
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        group_by: How to group the data - 'category', 'date', or 'month' (default: 'category')
    
    Returns:
        Dictionary with statistics including mean, median, total, min, max, and grouped data
    """
    try:
        result = db_analytics(user_id, start_date, end_date, group_by)
        return result
    except Exception as e:
        return {"ok": False, "message": f"Error generating analysis: {str(e)}"}



if __name__ == "__main__":
    import sys
    
    # Suppress Windows-specific asyncio warnings
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    print("Starting Expense Tracker MCP Server on http://0.0.0.0:8000")
    print("Press Ctrl+C to stop")
    
    try:
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")