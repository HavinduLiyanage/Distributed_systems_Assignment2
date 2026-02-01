"""
Bank Database Server (BDB)

Manages all persistent data operations using SQLite.
Designed to be accessed exclusively by the BAS server tier.
"""

import os
import sys
import sqlite3
import Pyro5.api
import Pyro5.server
from datetime import datetime, timedelta
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import (
    NAMESERVER_HOST, NAMESERVER_PORT, BDB_SERVER_NAME,
    DATABASE_FILE, MOCK_USERS, TOKEN_EXPIRATION_HOURS
)


@Pyro5.api.expose
class BankDatabaseServer:
    """
    Provides data persistence layer for the banking system.
    All database operations are exposed via Pyro5 RPC for BAS server access.
    """
    
    def __init__(self):
        """Initialize database connection and schema."""
        self.db_file = DATABASE_FILE
        self.init_database()
        print(f"[BDB] Database initialized: {self.db_file}")
    
    def get_connection(self):
        """Create a new SQLite connection with row factory enabled."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    
    def init_database(self):
        """Initialize database schema and populate with test data if tables are empty."""
        conn = self.get_connection()
        cursor = conn.cursor()
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        

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
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                user_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        for username, data in MOCK_USERS.items():
            cursor.execute(
                "SELECT user_id FROM users WHERE username = ?",
                (username,)
            )
            if cursor.fetchone() is None:
                # Hash password before storage
                import hashlib
                pwd_hash = hashlib.sha256(data["password"].encode()).hexdigest()
                
                cursor.execute(
                    "INSERT INTO users (user_id, username, password_hash, email) VALUES (?, ?, ?, ?)",
                    (data["user_id"], username, pwd_hash, f"{username}@bank.com")
                )
                cursor.execute(
                    "INSERT INTO accounts (account_id, user_id, balance) VALUES (?, ?, ?)",
                    (data["account_id"], data["user_id"], data["initial_balance"])
                )
        
        conn.commit()
        conn.close()
        print("[BDB] Database tables created and mock data inserted")

    def log_failed_transfer(self, from_account_id, to_account_id, amount, fee, reference, error_message):
        """Persist a failed transfer attempt for audit and status tracking."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # We record it as FAILED immediately
            cursor.execute(
                """INSERT INTO transfers 
                   (from_account_id, to_account_id, amount, fee, status, reference, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (from_account_id, to_account_id, amount, fee, "FAILED", f"{reference} [Error: {error_message}]", datetime.now().isoformat())
            )
            transfer_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return transfer_id
        except Exception as e:
            if conn:
                conn.close()
            print(f"[BDB] Failed to log failed transfer: {e}")
            return None
    def get_user_by_username(self, username):
        """Retrieve user credentials and metadata by username."""
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
        """Persist new user session with expiration timestamp."""
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
        """Verify session token and check expiration. Returns user_id if valid, None otherwise."""
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
    
    def get_account_by_user_id(self, user_id):
        """Retrieve account details for a given user."""
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
        """Retrieve account details by account identifier."""
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
        """Query current account balance."""
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
        """Set new balance for specified account."""
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
    
    def create_transfer(self, from_account_id, to_account_id, amount, fee, reference, status="PENDING"):
        """Persist transfer record with specified status."""
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
        """Modify transfer status and optionally set completion timestamp."""
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
        """Retrieve complete transfer details by identifier."""
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
    
    def get_user_transactions(self, account_id, limit=50):
        """
        Retrieve transaction history for account, ordered by most recent first.
        Includes both incoming and outgoing transfers.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT transfer_id, from_account_id, to_account_id, amount, fee, 
                          status, reference, created_at, completed_at
                   FROM transfers 
                   WHERE from_account_id = ? OR to_account_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (account_id, account_id, limit)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            transactions = []
            for row in rows:
                transactions.append({
                    "transfer_id": row["transfer_id"],
                    "from_account_id": row["from_account_id"],
                    "to_account_id": row["to_account_id"],
                    "amount": row["amount"],
                    "fee": row["fee"],
                    "status": row["status"],
                    "reference": row["reference"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"]
                })
            return transactions
            
        except Exception as e:
            if conn:
                conn.close()
            raise Exception(f"Failed to retrieve user transactions: {e}")
    
    def settle_transfer_transaction(self, transfer_id):
        """
        Execute fund transfer logic for a PENDING transfer.
        Atomically checks balance, updates accounts, and sets status to COMPLETED.
        If insufficient funds, sets status to FAILED.
        Returns (success, error_message).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute("BEGIN TRANSACTION")
            
            # 1. Get transfer details
            cursor.execute("SELECT from_account_id, to_account_id, amount, fee, status FROM transfers WHERE transfer_id = ?", (transfer_id,))
            transfer = cursor.fetchone()
            
            if not transfer:
                conn.rollback()
                return (False, "Transfer record not found")
                
            if transfer["status"] != "PENDING":
                conn.rollback()
                return (False, f"Transfer is already {transfer['status']}")
            
            from_account_id = transfer["from_account_id"]
            to_account_id = transfer["to_account_id"]
            amount = transfer["amount"]
            fee = transfer["fee"]
            
            # 2. Check Sender Balance
            cursor.execute("SELECT balance FROM accounts WHERE account_id = ?", (from_account_id,))
            sender_row = cursor.fetchone()
            if not sender_row:
                # Account missing? Fail transfer
                cursor.execute("UPDATE transfers SET status = ?, reference = reference || ' [Error: Sender missing]', completed_at = ? WHERE transfer_id = ?", 
                               ("FAILED", datetime.now().isoformat(), transfer_id))
                conn.commit()
                return (False, "Sender account not found")
            
            sender_balance = sender_row["balance"]
            total_deduction = amount + fee
            
            if sender_balance < total_deduction:
                # Insufficient funds -> Fail transfer
                cursor.execute("UPDATE transfers SET status = ?, reference = reference || ' [Error: Insufficient funds]', completed_at = ? WHERE transfer_id = ?", 
                               ("FAILED", datetime.now().isoformat(), transfer_id))
                conn.commit()
                return (False, f"Insufficient balance. Available: ${sender_balance:.2f}")
            
            # 3. Check Recipient Existence
            cursor.execute("SELECT account_id, balance FROM accounts WHERE account_id = ?", (to_account_id,))
            recipient_row = cursor.fetchone()
            if not recipient_row:
                 cursor.execute("UPDATE transfers SET status = ?, reference = reference || ' [Error: Recipient missing]', completed_at = ? WHERE transfer_id = ?", 
                               ("FAILED", datetime.now().isoformat(), transfer_id))
                 conn.commit()
                 return (False, "Recipient account not found")
            
            recipient_balance = recipient_row["balance"]
            
            # 4. Execute Updates
            new_sender_balance = round(sender_balance - total_deduction, 2)
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE account_id = ?",
                (new_sender_balance, from_account_id)
            )
            
            new_recipient_balance = round(recipient_balance + amount, 2)
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE account_id = ?",
                (new_recipient_balance, to_account_id)
            )
            
            cursor.execute(
                "UPDATE transfers SET status = ?, completed_at = ? WHERE transfer_id = ?",
                ("COMPLETED", datetime.now().isoformat(), transfer_id)
            )
            
            conn.commit()
            conn.close()
            
            return (True, None)
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
                conn.close()
            return (False, f"Transaction error: {e}")
    
    def log_operation(self, operation, user_id, details):
        """Record operation in audit log for compliance and debugging."""
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
    """Initialize and register BDB server with nameserver."""
    print("=" * 60)
    print("Bank Database Server (BDB) - Starting")
    print("=" * 60)
    
    try:
        bdb_server = BankDatabaseServer()
        
        daemon = Pyro5.server.Daemon()
        ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
        
        uri = daemon.register(bdb_server)
        ns.register(BDB_SERVER_NAME, uri)
        
        print(f"[BDB] Server registered as '{BDB_SERVER_NAME}'")
        print(f"[BDB] URI: {uri}")
        print("-" * 60)
        print("[BDB] Ready to accept requests from BAS server")
        print("[BDB] Press Ctrl+C to stop")
        print("=" * 60)
        
        daemon.requestLoop()
        
    except KeyboardInterrupt:
        print("\n[BDB] Server stopped by user")
    except Exception as e:
        print(f"[BDB] Error: {e}")
        print("\nMake sure the nameserver is running:")
        print("  python start_nameserver.py")


if __name__ == "__main__":
    main()
