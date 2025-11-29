# mcp_tools.py
"""
MCP tools for the customer support system.

Implements the required tools:
- get_customer(customer_id)
- list_customers(status, limit)
- update_customer(customer_id, data)
- create_ticket(customer_id, issue, priority)
- get_customer_history(customer_id)

All tools operate on the SQLite database initialized by data_setup.py (support.db).
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_PATH = "support.db"


# ---------------------------------------------------------
# Helper: Create a database connection with foreign keys ON
# ---------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """
    Create a SQLite connection with foreign key constraints enabled.

    Returns:
        sqlite3.Connection object
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # return rows as dict-like objects
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------
# Tool 1: get_customer
# ---------------------------------------------------------
def get_customer(customer_id: int) -> Dict[str, Any]:
    """
    Retrieve a customer's record by ID.

    Args:
        customer_id: ID of the customer in the customers table.

    Returns:
        A dictionary with customer info:
        {
            "found": True/False,
            "id": ...,
            "name": ...,
            "email": ...,
            ...
        }
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, email, phone, status, created_at, updated_at
            FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        )
        row = cur.fetchone()

    if row is None:
        return {"found": False, "message": f"Customer {customer_id} not found."}

    return {
        "found": True,
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------
# Tool 2: list_customers
# ---------------------------------------------------------
def list_customers(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List customers, optionally filtered by status.

    Args:
        status: Optional status filter ('active' or 'disabled')
        limit: Maximum number of rows to return

    Returns:
        List of customer dictionaries
    """
    query = """
        SELECT id, name, email, phone, status, created_at, updated_at
        FROM customers
    """
    params: List[Any] = []

    # Add WHERE clause only if status is provided
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)

    query += " ORDER BY id LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

    customers = []
    for r in rows:
        customers.append({
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "phone": r["phone"],
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    return customers


# ---------------------------------------------------------
# Tool 3: update_customer
# ---------------------------------------------------------

ALLOWED_CUSTOMER_FIELDS = {"name", "email", "phone", "status"}

def update_customer(customer_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update allowed fields of a customer record.

    Args:
        customer_id: ID of the customer to update
        data: Dictionary of fields to update (name, email, phone, status)

    Returns:
        Dict indicating success/failure
    """
    if not data:
        return {"success": False, "message": "No fields provided to update."}

    # Filter input to allowed fields only
    fields = [k for k in data.keys() if k in ALLOWED_CUSTOMER_FIELDS]
    if not fields:
        return {
            "success": False,
            "message": f"No valid fields to update. Allowed: {ALLOWED_CUSTOMER_FIELDS}",
        }

    # Validate status field when provided
    if "status" in data and data["status"] not in ("active", "disabled"):
        return {"success": False, "message": "Invalid status (must be 'active' or 'disabled')."}

    # Build SET clause dynamically
    set_clause = ", ".join(f"{f} = ?" for f in fields)
    values = [data[f] for f in fields]

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE customers SET {set_clause} WHERE id = ?",
            (*values, customer_id),
        )
        conn.commit()
        rows_affected = cur.rowcount

    if rows_affected == 0:
        return {"success": False, "message": f"Customer {customer_id} not found."}

    return {"success": True, "rows_affected": rows_affected}


# ---------------------------------------------------------
# Tool 4: create_ticket
# ---------------------------------------------------------
def create_ticket(customer_id: int, issue: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Create a new support ticket for a specific customer.

    Args:
        customer_id: The customer ID this ticket belongs to
        issue: Text description of the issue
        priority: One of: 'low', 'medium', 'high'

    Returns:
        Dict with success flag and new ticket ID
    """
    if priority not in ("low", "medium", "high"):
        return {
            "success": False,
            "message": "Priority must be one of: low, medium, high",
        }

    # Check if customer exists before inserting
    customer = get_customer(customer_id)
    if not customer.get("found"):
        return {
            "success": False,
            "message": f"Customer {customer_id} does not exist.",
        }

    created_at = datetime.utcnow().isoformat()

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tickets (customer_id, issue, status, priority, created_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (customer_id, issue, priority, created_at),
        )
        ticket_id = cur.lastrowid
        conn.commit()

    return {
        "success": True,
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "priority": priority,
        "created_at": created_at,
    }


# ---------------------------------------------------------
# Tool 5: get_customer_history
# ---------------------------------------------------------
def get_customer_history(customer_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve all tickets belonging to a given customer.

    Args:
        customer_id: ID of the customer

    Returns:
        List of ticket dictionaries (most recent first)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, issue, status, priority, created_at
            FROM tickets
            WHERE customer_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (customer_id,),
        )
        rows = cur.fetchall()

    history = []
    for r in rows:
        history.append({
            "ticket_id": r["id"],
            "issue": r["issue"],
            "status": r["status"],
            "priority": r["priority"],
            "created_at": r["created_at"],
        })

    return history


# ---------------------------------------------------------
# Local test runner (optional)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("Testing MCP tools using support.db\n")

    print("1) get_customer(1)")
    print(get_customer(1))

    print("\n2) list_customers('active', limit=3)")
    print(list_customers(status="active", limit=3))

    print("\n3) update_customer(1, {'email': 'new.email@example.com'})")
    print(update_customer(1, {"email": "new.email@example.com"}))

    print("\n4) create_ticket(1, 'Test issue created by MCP tool', 'high')")
    print(create_ticket(1, "Test issue created by MCP tool", "high"))

    print("\n5) get_customer_history(1)")
    print(get_customer_history(1))
