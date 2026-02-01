"""
Bank Application Server (BAS)

Implements business logic layer including authentication, transfer processing,
and six-tier fee calculation. Communicates with BDB server for persistence.
"""

import os
import sys
import Pyro5.api
import Pyro5.server
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import (
    NAMESERVER_HOST, NAMESERVER_PORT, BAS_SERVER_NAME, BDB_SERVER_NAME,
    FEE_TIERS, TOKEN_EXPIRATION_HOURS
)
import time
import hashlib


@Pyro5.api.expose
class BankApplicationServer:
    """
    Implements business logic tier for banking operations.
    Validates inputs, applies business rules, and coordinates with database tier.
    """
    
    def __init__(self):
        """Initialize with idempotency tracking for duplicate transaction prevention."""
        self.recent_transfers = {}
        self.IDEMPOTENCY_WINDOW = 5
        print("[BAS] Application server initialized")
    
    def connect_to_bdb(self):
        """Establish Pyro5 proxy connection to database server."""
        try:
            ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
            uri = ns.lookup(BDB_SERVER_NAME)
            return Pyro5.api.Proxy(uri)
        except Exception as e:
            raise Exception(f"Failed to connect to BDB server: {e}")
    
    def calculate_fee(self, amount):
        """
        Apply tiered fee structure with percentage-based calculation and per-tier caps.
        Returns fee rounded to two decimal places.
        """
        if amount <= 0:
            return 0.00
        
        for min_amount, max_amount, percentage, cap in FEE_TIERS:
            if min_amount <= amount <= max_amount:
                fee = amount * percentage
                fee = min(fee, cap)
                return round(fee, 2)
        
        return 0.00
    
    def login(self, username, password):
        """
        Authenticate user credentials and establish session.
        Returns (success, session_token) on success or (False, error_message) on failure.
        """
        try:
            bdb = self.connect_to_bdb()
            
            user = bdb.get_user_by_username(username)
            
            if user is None:
                bdb.log_operation("LOGIN_FAILED", None, f"Username not found: {username}")
                return (False, "Invalid username or password")
            
            # Verify password hash
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user["password_hash"] != password_hash:
                bdb.log_operation("LOGIN_FAILED", user["user_id"], f"Invalid password for user: {username}")
                return (False, "Invalid username or password")
            
            token = str(uuid.uuid4())
            expires_at = (datetime.now() + timedelta(hours=TOKEN_EXPIRATION_HOURS)).isoformat()
            
            bdb.create_session(user["user_id"], token, expires_at)
            
            bdb.log_operation("LOGIN_SUCCESS", user["user_id"], f"User logged in: {username}")
            
            print(f"[BAS] User '{username}' logged in successfully")
            return (True, token)
            
        except Exception as e:
            print(f"[BAS] Login error: {e}")
            return (False, f"Login failed: {e}")
    
    def validate_token(self, token):
        """
        Verify session token validity and expiration.
        Returns user_id if valid, raises exception otherwise.
        """
        try:
            bdb = self.connect_to_bdb()
            user_id = bdb.validate_session(token)
            
            if user_id is None:
                raise Exception("Invalid or expired session token")
            
            return user_id
            
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    def get_balance(self, token):
        """
        Retrieve account balance for authenticated user.
        Returns (success, balance) or (False, error_message).
        """
        try:
            bdb = self.connect_to_bdb()
            
            user_id = self.validate_token(token)
            
            account = bdb.get_account_by_user_id(user_id)
            
            if account is None:
                return (False, "Account not found")
            
            balance = account["balance"]
            
            bdb.log_operation("BALANCE_QUERY", user_id, f"Balance queried: ${balance:.2f}")
            
            print(f"[BAS] Balance query for user_id {user_id}: ${balance:.2f}")
            return (True, balance)
            
        except Exception as e:
            print(f"[BAS] Balance query error: {e}")
            return (False, str(e))
    
    def submit_transfer(self, token, recipient_account_id, amount, reference=""):
        """
        Validate and execute fund transfer with fee calculation.
        Applies idempotency check to prevent duplicate transactions within time window.
        
        Returns (success, result_dict) with transfer details or (False, error_message).
        """
        try:
            bdb = self.connect_to_bdb()
            
            user_id = self.validate_token(token)
            
            sender_account = bdb.get_account_by_user_id(user_id)
            if sender_account is None:
                return (False, "Sender account not found")
            
            sender_account_id = sender_account["account_id"]
            
            if amount <= 0:
                return (False, "Transfer amount must be positive")
            
            if reference and len(reference) > 200:
                return (False, "Reference message too long (max 200 characters)")
            
            amount = round(amount, 2)
            
            transfer_key = f"{user_id}:{recipient_account_id}:{amount}:{reference}"
            transfer_hash = hashlib.md5(transfer_key.encode()).hexdigest()
            
            current_time = time.time()
            if transfer_hash in self.recent_transfers:
                last_time = self.recent_transfers[transfer_hash]
                if current_time - last_time < self.IDEMPOTENCY_WINDOW:
                    print(f"[BAS] Rejecting duplicate transfer (idempotency): {transfer_key}")
                    return (False, "Duplicate transfer detected. Please wait a few seconds before trying again.")
            
            self.recent_transfers[transfer_hash] = current_time
            
            self.recent_transfers = {k: v for k, v in self.recent_transfers.items() 
                                    if current_time - v < self.IDEMPOTENCY_WINDOW}
            
            recipient_account = bdb.get_account_by_id(recipient_account_id)
            if recipient_account is None:
                return (False, "Recipient account not found")
            
            if sender_account_id == recipient_account_id:
                return (False, "Cannot transfer to your own account")
            
            fee = self.calculate_fee(amount)
            
            current_balance = sender_account["balance"]
            total_deduction = amount + fee
            
            if current_balance < total_deduction:
                bdb.log_operation(
                    "TRANSFER_FAILED", 
                    user_id, 
                    f"Insufficient funds: balance=${current_balance:.2f}, needed=${total_deduction:.2f}"
                )
                return (False, f"Insufficient balance. Required: ${total_deduction:.2f}, Available: ${current_balance:.2f}")
            
            # Two-Step Transfer Process:
            # 1. Create PENDING transfer record
            transfer_id = bdb.create_transfer(
                sender_account_id,
                recipient_account_id,
                amount,
                fee,
                reference,
                "PENDING"
            )
            
            # 2. Attempt to settle the transfer (Atomic: Check Balance -> Move Funds -> Complete/Fail)
            success, error = bdb.settle_transfer_transaction(transfer_id)
            
            if not success:
                bdb.log_operation("TRANSFER_FAILED", user_id, f"Transaction failed for ID {transfer_id}: {error}")
                return (False, error)
            
            bdb.log_operation(
                "TRANSFER_SUCCESS",
                user_id,
                f"Transfer ID {transfer_id}: ${amount:.2f} to account {recipient_account_id}, fee ${fee:.2f}"
            )
            
            result = {
                "transfer_id": transfer_id,
                "amount": amount,
                "fee": fee,
                "status": "COMPLETED",
                "message": f"Transfer successful! Transferred ${amount:.2f} with fee ${fee:.2f}"
            }
            
            print(f"[BAS] Transfer completed: ID={transfer_id}, Amount=${amount:.2f}, Fee=${fee:.2f}")
            return (True, result)
            
        except Exception as e:
            print(f"[BAS] Transfer error: {e}")
            return (False, str(e))
    
    def get_transfer_status(self, token, transfer_id):
        """
        Retrieve transfer details and current status by ID.
        Returns (success, transfer_info) or (False, error_message).
        """
        try:
            bdb = self.connect_to_bdb()
            
            user_id = self.validate_token(token)
            
            transfer = bdb.get_transfer(transfer_id)
            
            if transfer is None:
                return (False, "Transfer not found")
            
            bdb.log_operation(
                "TRANSFER_STATUS_QUERY",
                user_id,
                f"Queried status for transfer ID {transfer_id}"
            )
            
            print(f"[BAS] Transfer status query: ID={transfer_id}, Status={transfer['status']}")
            return (True, transfer)
            
        except Exception as e:
            print(f"[BAS] Transfer status query error: {e}")
            return (False, str(e))
    
    def get_transaction_history(self, token, limit=50):
        """
        Fetch transaction history for authenticated user's account.
        Returns (success, transactions_list) or (False, error_message).
        """
        try:
            bdb = self.connect_to_bdb()
            
            user_id = self.validate_token(token)
            
            account = bdb.get_account_by_user_id(user_id)
            if account is None:
                return (False, "Account not found")
            
            account_id = account["account_id"]
            
            transactions = bdb.get_user_transactions(account_id, limit)
            
            bdb.log_operation(
                "TRANSACTION_HISTORY_QUERY",
                user_id,
                f"User queried transaction history (found {len(transactions)} items)"
            )
            
            print(f"[BAS] Transaction history query for user_id {user_id}: {len(transactions)} items found")
            return (True, transactions)
            
        except Exception as e:
            print(f"[BAS] Transaction history error: {e}")
            return (False, f"Failed to retrieve transaction history: {e}")


def main():
    """Initialize and register BAS server with nameserver."""
    print("=" * 60)
    print("Bank Application Server (BAS) - Starting")
    print("=" * 60)
    
    try:
        bas_server = BankApplicationServer()
        
        daemon = Pyro5.server.Daemon()
        ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
        
        uri = daemon.register(bas_server)
        ns.register(BAS_SERVER_NAME, uri)
        
        print(f"[BAS] Server registered as '{BAS_SERVER_NAME}'")
        print(f"[BAS] URI: {uri}")
        print("-" * 60)
        print("[BAS] Ready to accept requests from BC clients")
        print("[BAS] Press Ctrl+C to stop")
        print("=" * 60)
        
        daemon.requestLoop()
        
    except KeyboardInterrupt:
        print("\n[BAS] Server stopped by user")
    except Exception as e:
        print(f"[BAS] Error: {e}")
        print("\nMake sure:")
        print("  1. Nameserver is running: python start_nameserver.py")
        print("  2. BDB server is running: python bdb_server.py")


if __name__ == "__main__":
    main()
