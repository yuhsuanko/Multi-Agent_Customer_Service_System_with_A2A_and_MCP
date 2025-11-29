#!/usr/bin/env python3
"""
Quick verification script to check if all dependencies and modules are properly set up.
Run this before running the main demo.
"""

import sys

def check_imports():
    """Check if all required modules can be imported."""
    print("Checking imports...")
    
    try:
        import sqlite3
        print("✓ sqlite3")
    except ImportError as e:
        print(f"✗ sqlite3: {e}")
        return False
    
    try:
        import fastapi
        print("✓ fastapi")
    except ImportError as e:
        print(f"✗ fastapi: {e}")
        return False
    
    try:
        import uvicorn
        print("✓ uvicorn")
    except ImportError as e:
        print(f"✗ uvicorn: {e}")
        return False
    
    try:
        import requests
        print("✓ requests")
    except ImportError as e:
        print(f"✗ requests: {e}")
        return False
    
    try:
        from langgraph.graph import StateGraph, END
        print("✓ langgraph")
    except ImportError as e:
        print(f"✗ langgraph: {e}")
        return False
    
    try:
        from typing_extensions import TypedDict
        print("✓ typing_extensions")
    except ImportError as e:
        print(f"✗ typing_extensions: {e}")
        return False
    
    return True

def check_project_modules():
    """Check if project modules can be imported."""
    print("\nChecking project modules...")
    
    try:
        from agents.state import CSState, AgentMessage
        print("✓ agents.state")
    except ImportError as e:
        print(f"✗ agents.state: {e}")
        return False
    
    try:
        from agents.graph import build_workflow
        print("✓ agents.graph")
    except ImportError as e:
        print(f"✗ agents.graph: {e}")
        return False
    
    try:
        from agents.router_agent import router_node
        print("✓ agents.router_agent")
    except ImportError as e:
        print(f"✗ agents.router_agent: {e}")
        return False
    
    try:
        from agents.data_agent import data_agent_node
        print("✓ agents.data_agent")
    except ImportError as e:
        print(f"✗ agents.data_agent: {e}")
        return False
    
    try:
        from agents.support_agent import support_agent_node
        print("✓ agents.support_agent")
    except ImportError as e:
        print(f"✗ agents.support_agent: {e}")
        return False
    
    try:
        from agents.mcp_client import mcp_get_customer
        print("✓ agents.mcp_client")
    except ImportError as e:
        print(f"✗ agents.mcp_client: {e}")
        return False
    
    try:
        import mcp_tools
        print("✓ mcp_tools")
    except ImportError as e:
        print(f"✗ mcp_tools: {e}")
        return False
    
    try:
        import config
        print("✓ config")
    except ImportError as e:
        print(f"✗ config: {e}")
        return False
    
    return True

def check_database():
    """Check if database exists."""
    print("\nChecking database...")
    
    import os
    if os.path.exists("support.db"):
        print("✓ support.db exists")
        return True
    else:
        print("✗ support.db not found (run 'python database_setup.py' to create it)")
        return False

def main():
    print("=" * 60)
    print("Multi-Agent Customer Service System - Setup Verification")
    print("=" * 60)
    
    all_good = True
    
    all_good = check_imports() and all_good
    all_good = check_project_modules() and all_good
    all_good = check_database() and all_good
    
    print("\n" + "=" * 60)
    if all_good:
        print("✓ All checks passed! You're ready to run the demo.")
        print("\nRun: python demo/main.py")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()

