# config.py
"""
Shared configuration values for all services.
Adjust the ports / URLs as needed to match your environment.
"""

# Path to the SQLite database created by data_setup.py
DB_PATH = "support.db"

# Base URLs for each microservice
MCP_SERVER_URL = "http://localhost:8000"
ROUTER_AGENT_URL = "http://localhost:8001"
DATA_AGENT_URL = "http://localhost:8002"
SUPPORT_AGENT_URL = "http://localhost:8003"
