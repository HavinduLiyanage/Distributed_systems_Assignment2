"""
Bank Database Server (BDB)
CSI3344 Assignment 2 - Distributed Banking System
Phase 2: Database Tier

This server manages all persistent data using SQLite.
Only the BAS server can access this server (not BC client).
"""

import sqlite3
import Pyro5.api
import Pyro5.server
from datetime import datetime, timedelta
import uuid
from config import (
    NAMESERVER_HOST, NAMESERVER_PORT, BDB_SERVER_NAME,
    DATABASE_FILE, MOCK_USERS, TOKEN_EXPIRATION_HOURS
)


@Pyro5.api.expose
class BankDatabaseServer:
    """
    Database server that manages all persistent data.
    Exposes methods via Pyro5 for the BAS server to call.
    """
    
    def __init__(self):
        """Initialize the database server"""
        self.db_file = DATABASE_FILE
        self.init_database()
        print(f"[BDB] Database initialized: {self.db_file}")
    
    def get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    
    def init_database(self):
        """Create all tables and insert mock data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create transfers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account_id INTEGER NOT NULL,
                to_account_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                status TEXT NOT NULL,
                reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (from_account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(account_id)
            )
        """)
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                user_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert mock users if they don't exist
        for username, data in MOCK_USERS.items():
            cursor.execute(
                "SELECT user_id FROM users WHERE username = ?",
                (username,)
            )
            if cursor.fetchone() is None:
                # Insert user
                cursor.execute(
                    "INSERT INTO users (user_id, username, password_hash, email) VALUES (?, ?, ?, ?)",
                    (data["user_id"], username, data["password"], f"{username}@bank.com")
                )
                # Insert account with initial balance
                cursor.execute(
                    "INSERT INTO accounts (account_id, user_id, balance) VALUES (?, ?, ?)",
                    (data["account_id"], data["user_id"], data["initial_balance"])
                )
        
        conn.commit()
        conn.close()
        print("[BDB] Database tables created and mock data inserted")
    
    # ==================== User Management ====================
    
    def get_user_by_username(self, username):
        """Get user record by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, password_hash, email FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "password_hash": row["password_hash"],
                "email": row["email"]
            }
        return None
    
    def create_session(self, user_id, token, expires_at):
        """Create a new session for authenticated user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires_at)
            )
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return session_id
        except Exception as e:
            conn.close()
            raise Exception(f"Failed to create session: {e}")
    
    def validate_session(self, token):
        """Validate session token and return user_id if valid"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?",
            (token,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.now() < expires_at:
                return row["user_id"]
        return None
    
    # ==================== Account Management ====================
    
    def get_account_by_user_id(self, user_id):
        """Get account record by user_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_id, user_id, balance FROM accounts WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "account_id": row["account_id"],
                "user_id": row["user_id"],
                "balance": row["balance"]
            }
        return None
    
    def get_account_by_id(self, account_id):
        """Get account record by account_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_id, user_id, balance FROM accounts WHERE account_id = ?",
            (account_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "account_id": row["account_id"],
                "user_id": row["user_id"],
                "balance": row["balance"]
            }
        return None
    
    def get_balance(self, account_id):
        """Get current balance for an account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance FROM accounts WHERE account_id = ?",
            (account_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row["balance"]
        return None
    
    def update_balance(self, account_id, new_balance):
        """Update account balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE account_id = ?",
                (new_balance, account_id)
            )
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            conn.close()
            raise Exception(f"Failed to update balance: {e}")
    
    # ==================== Transfer Management ====================
    
    def create_transfer(self, from_account_id, to_account_id, amount, fee, reference, status="PENDING"):
        """Create a new transfer record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO transfers 
                   (from_account_id, to_account_id, amount, fee, status, reference)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (from_account_id, to_account_id, amount, fee, status, reference)
            )
            transfer_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return transfer_id
        except Exception as e:
            conn.close()
            raise Exception(f"Failed to create transfer: {e}")
    
    def update_transfer_status(self, transfer_id, status, completed_at=None):
        """Update transfer status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if completed_at:
                cursor.execute(
                    "UPDATE transfers SET status = ?, completed_at = ? WHERE transfer_id = ?",
                    (status, completed_at, transfer_id)
                )
            else:
                cursor.execute(
                    "UPDATE transfers SET status = ? WHERE transfer_id = ?",
                    (status, transfer_id)
                )
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            conn.close()
            raise Exception(f"Failed to update transfer status: {e}")
    
    def get_transfer(self, transfer_id):
        """Get transfer record by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT transfer_id, from_account_id, to_account_id, amount, fee, 
                      status, reference, created_at, completed_at
               FROM transfers WHERE transfer_id = ?""",
            (transfer_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "transfer_id": row["transfer_id"],
                "from_account_id": row["from_account_id"],
                "to_account_id": row["to_account_id"],
                "amount": row["amount"],
                "fee": row["fee"],
                "status": row["status"],
                "reference": row["reference"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"]
            }
        return None
    
    def execute_transfer_transaction(self, from_account_id, to_account_id, amount, fee, reference):
        """
        Execute transfer as an atomic transaction.
        Returns (success, transfer_id, error_message)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Get current balances
            cursor.execute("SELECT balance FROM accounts WHERE account_id = ?", (from_account_id,))
            sender_row = cursor.fetchone()
            if not sender_row:
                conn.rollback()
                conn.close()
                return (False, None, "Sender account not found")
            
            sender_balance = sender_row["balance"]
            total_deduction = amount + fee
            
            # Check sufficient balance
            if sender_balance < total_deduction:
                conn.rollback()
                conn.close()
                return (False, None, "Insufficient balance")
            
            # Check recipient exists
            cursor.execute("SELECT balance FROM accounts WHERE account_id = ?", (to_account_id,))
            recipient_row = cursor.fetchone()
            if not recipient_row:
                conn.rollback()
                conn.close()
                return (False, None, "Recipient account not found")
            
            recipient_balance = recipient_row["balance"]
            
            # Deduct from sender
            new_sender_balance = round(sender_balance - total_deduction, 2)
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE account_id = ?",
                (new_sender_balance, from_account_id)
            )
            
            # Add to recipient
            new_recipient_balance = round(recipient_balance + amount, 2)
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE account_id = ?",
                (new_recipient_balance, to_account_id)
            )
            
            # Create transfer record with COMPLETED status
            cursor.execute(
                """INSERT INTO transfers 
                   (from_account_id, to_account_id, amount, fee, status, reference, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (from_account_id, to_account_id, amount, fee, "COMPLETED", reference, datetime.now().isoformat())
            )
            transfer_id = cursor.lastrowid
            
            # Commit transaction
            conn.commit()
            conn.close()
            
            return (True, transfer_id, None)
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return (False, None, f"Transaction failed: {e}")
    
    # ==================== Audit Logging ====================
    
    def log_operation(self, operation, user_id, details):
        """Log an operation for audit trail"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO audit_logs (operation, user_id, details) VALUES (?, ?, ?)",
                (operation, user_id, details)
            )
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return log_id
        except Exception as e:
            conn.close()
            print(f"[BDB] Audit log failed: {e}")
            return None


def main():
    """Start the BDB server"""
    print("=" * 60)
    print("Bank Database Server (BDB) - Starting")
    print("=" * 60)
    
    try:
        # Create database server instance
        bdb_server = BankDatabaseServer()
        
        # Start Pyro5 daemon
        daemon = Pyro5.server.Daemon()
        
        # Locate nameserver
        ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
        
        # Register server with daemon
        uri = daemon.register(bdb_server)
        
        # Register with nameserver
        ns.register(BDB_SERVER_NAME, uri)
        
        print(f"[BDB] Server registered as '{BDB_SERVER_NAME}'")
        print(f"[BDB] URI: {uri}")
        print("-" * 60)
        print("[BDB] Ready to accept requests from BAS server")
        print("[BDB] Press Ctrl+C to stop")
        print("=" * 60)
        
        # Start request loop
        daemon.requestLoop()
        
    except KeyboardInterrupt:
        print("\n[BDB] Server stopped by user")
    except Exception as e:
        print(f"[BDB] Error: {e}")
        print("\nMake sure the nameserver is running:")
        print("  python start_nameserver.py")


if __name__ == "__main__":
    main()
