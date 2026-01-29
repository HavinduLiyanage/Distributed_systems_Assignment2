"""
Configuration file for the Distributed Banking System
CSI3344 Assignment 2 - Three-Tier Architecture
"""

# Pyro5 Configuration
NAMESERVER_HOST = "127.0.0.1"
NAMESERVER_PORT = 9090

# Server Object Names
BAS_SERVER_NAME = "bank.application.server"
BDB_SERVER_NAME = "bank.database.server"

# Database Configuration
DATABASE_FILE = "banking_system.db"

# Session Configuration
TOKEN_EXPIRATION_HOURS = 24

# Fee Tier Table (amount ranges and fee rules)
# Format: (min_amount, max_amount, percentage, cap)
FEE_TIERS = [
    (0.00, 2000.00, 0.0000, 0.00),           # Free tier
    (2000.01, 10000.00, 0.0025, 20.00),     # 0.25%, cap $20
    (10000.01, 20000.00, 0.0020, 25.00),    # 0.20%, cap $25
    (20000.01, 50000.00, 0.00125, 40.00),   # 0.125%, cap $40
    (50000.01, 100000.00, 0.0008, 50.00),   # 0.08%, cap $50
    (100000.01, float('inf'), 0.0005, 100.00)  # 0.05%, cap $100
]

# Mock User Credentials (Phase 1 - In-Memory)
MOCK_USERS = {
    "john": {
        "password": "pass123",
        "user_id": 1,
        "account_id": 1001,
        "initial_balance": 50000.00
    },
    "jane": {
        "password": "pass456",
        "user_id": 2,
        "account_id": 1002,
        "initial_balance": 75000.00
    }
}
