# agents/mcp_client.py
"""
Thin client wrapper for MCP tools.

For now, this module directly imports and calls the local mcp_tools functions.
In a real MCP-based deployment, you would replace these calls with
remote tool invocations over the MCP protocol.
"""

from typing import Any, Dict, List, Optional

from mcp_tools import (
    get_customer as _get_customer,
    list_customers as _list_customers,
    update_customer as _update_customer,
    create_ticket as _create_ticket,
    get_customer_history as _get_customer_history,
)


def mcp_get_customer(customer_id: int) -> Dict[str, Any]:
    """Wrapper for MCP get_customer tool."""
    return _get_customer(customer_id)


def mcp_list_customers(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Wrapper for MCP list_customers tool."""
    return _list_customers(status=status, limit=limit)


def mcp_update_customer(customer_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for MCP update_customer tool."""
    return _update_customer(customer_id, data)


def mcp_create_ticket(customer_id: int, issue: str, priority: str = "medium") -> Dict[str, Any]:
    """Wrapper for MCP create_ticket tool."""
    return _create_ticket(customer_id, issue, priority)


def mcp_get_customer_history(customer_id: int) -> List[Dict[str, Any]]:
    """Wrapper for MCP get_customer_history tool."""
    return _get_customer_history(customer_id)
