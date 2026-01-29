"""
Bank Application Server (BAS)
CSI3344 Assignment 2 - Distributed Banking System
Phase 2: Application Tier

This server implements all business logic including:
- Authentication and session management
- Balance queries
- Transfer validation and processing
- Fee calculation (6-tier structure)
- Integration with BDB server
"""

import Pyro5.api
import Pyro5.server
import uuid
from datetime import datetime, timedelta
from config import (
    NAMESERVER_HOST, NAMESERVER_PORT, BAS_SERVER_NAME, BDB_SERVER_NAME,
    FEE_TIERS, TOKEN_EXPIRATION_HOURS
)
import time
import hashlib


@Pyro5.api.expose
class BankApplicationServer:
    """
    Application server that handles all business logic.
    Communicates with BDB server for data persistence.
    Exposes methods via Pyro5 for BC client to call.
    """
    
    def __init__(self):
        """Initialize the application server"""
        self.recent_transfers = {}  # For idempotency: {hash: timestamp}
        self.IDEMPOTENCY_WINDOW = 5  # Seconds
        print("[BAS] Application server initialized")
    
    def connect_to_bdb(self):
        """Connect to BDB server via Pyro5"""
        try:
            ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
            uri = ns.lookup(BDB_SERVER_NAME)
            return Pyro5.api.Proxy(uri)
        except Exception as e:
            raise Exception(f"Failed to connect to BDB server: {e}")
    
    # ==================== Fee Calculation ====================
    
    def calculate_fee(self, amount):
        """
        Calculate transfer fee based on 6-tier structure.
        Returns fee rounded to 2 decimal places.
        """
        if amount <= 0:
            return 0.00
        
        # Find the appropriate fee tier
        for min_amount, max_amount, percentage, cap in FEE_TIERS:
            if min_amount <= amount <= max_amount:
                fee = amount * percentage
                fee = min(fee, cap)  # Apply cap
                return round(fee, 2)
        
        # Should never reach here if FEE_TIERS is properly configured
        return 0.00
    
    # ==================== Authentication ====================
    
    def login(self, username, password):
        """
        Authenticate user and create session.
        Returns: (success, token_or_error_message)
        """
        try:
            bdb = self.connect_to_bdb()
            
            # Get user from database
            user = bdb.get_user_by_username(username)
            
            if user is None:
                bdb.log_operation("LOGIN_FAILED", None, f"Username not found: {username}")
                return (False, "Invalid username or password")
            
            # Validate password (simple comparison for mock)
            if user["password_hash"] != password:
                bdb.log_operation("LOGIN_FAILED", user["user_id"], f"Invalid password for user: {username}")
                return (False, "Invalid username or password")
            
            # Generate session token
            token = str(uuid.uuid4())
            expires_at = (datetime.now() + timedelta(hours=TOKEN_EXPIRATION_HOURS)).isoformat()
            
            # Create session in database
            bdb.create_session(user["user_id"], token, expires_at)
            
            # Log successful login
            bdb.log_operation("LOGIN_SUCCESS", user["user_id"], f"User logged in: {username}")
            
            print(f"[BAS] User '{username}' logged in successfully")
            return (True, token)
            
        except Exception as e:
            print(f"[BAS] Login error: {e}")
            return (False, f"Login failed: {e}")
    
    def validate_token(self, token):
        """
        Validate session token and return user_id.
        Raises exception if token is invalid.
        """
        try:
            bdb = self.connect_to_bdb()
            user_id = bdb.validate_session(token)
            
            if user_id is None:
                raise Exception("Invalid or expired session token")
            
            return user_id
            
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    # ==================== Balance Query ====================
    
    def get_balance(self, token):
        """
        Get account balance for authenticated user.
        Returns: (success, balance_or_error_message)
        """
        try:
            bdb = self.connect_to_bdb()
            
            # Validate token and get user_id
            user_id = self.validate_token(token)
            
            # Get account for user
            account = bdb.get_account_by_user_id(user_id)
            
            if account is None:
                return (False, "Account not found")
            
            balance = account["balance"]
            
            # Log balance query
            bdb.log_operation("BALANCE_QUERY", user_id, f"Balance queried: ${balance:.2f}")
            
            print(f"[BAS] Balance query for user_id {user_id}: ${balance:.2f}")
            return (True, balance)
            
        except Exception as e:
            print(f"[BAS] Balance query error: {e}")
            return (False, str(e))
    
    # ==================== Transfer Processing ====================
    
    def submit_transfer(self, token, recipient_account_id, amount, reference=""):
        """
        Submit and process a transfer.
        Returns: (success, result_dict_or_error_message)
        
        result_dict format:
        {
            "transfer_id": int,
            "amount": float,
            "fee": float,
            "status": str,
            "message": str
        }
        """
        try:
            bdb = self.connect_to_bdb()
            
            # Validate token and get user_id
            user_id = self.validate_token(token)
            
            # Get sender account
            sender_account = bdb.get_account_by_user_id(user_id)
            if sender_account is None:
                return (False, "Sender account not found")
            
            sender_account_id = sender_account["account_id"]
            
            # Validate amount
            if amount <= 0:
                return (False, "Transfer amount must be positive")
            
            # Validate reference length
            if reference and len(reference) > 200:
                return (False, "Reference message too long (max 200 characters)")
            
            # Round amount to 2 decimals
            amount = round(amount, 2)
            
            # Idempotency check
            # Create a unique hash for this specific transfer attempt
            transfer_key = f"{user_id}:{recipient_account_id}:{amount}:{reference}"
            transfer_hash = hashlib.md5(transfer_key.encode()).hexdigest()
            
            current_time = time.time()
            if transfer_hash in self.recent_transfers:
                last_time = self.recent_transfers[transfer_hash]
                if current_time - last_time < self.IDEMPOTENCY_WINDOW:
                    print(f"[BAS] Rejecting duplicate transfer (idempotency): {transfer_key}")
                    return (False, "Duplicate transfer detected. Please wait a few seconds before trying again.")
            
            # Store this transfer attempt
            self.recent_transfers[transfer_hash] = current_time
            
            # Cleanup old idempotency keys periodically
            self.recent_transfers = {k: v for k, v in self.recent_transfers.items() 
                                    if current_time - v < self.IDEMPOTENCY_WINDOW}
            
            # Validate recipient exists
            recipient_account = bdb.get_account_by_id(recipient_account_id)
            if recipient_account is None:
                return (False, "Recipient account not found")
            
            # Check not sending to self
            if sender_account_id == recipient_account_id:
                return (False, "Cannot transfer to your own account")
            
            # Calculate fee
            fee = self.calculate_fee(amount)
            
            # Get current balance
            current_balance = sender_account["balance"]
            total_deduction = amount + fee
            
            # Check sufficient balance
            if current_balance < total_deduction:
                bdb.log_operation(
                    "TRANSFER_FAILED", 
                    user_id, 
                    f"Insufficient funds: balance=${current_balance:.2f}, needed=${total_deduction:.2f}"
                )
                return (False, f"Insufficient balance. Required: ${total_deduction:.2f}, Available: ${current_balance:.2f}")
            
            # Execute transfer as atomic transaction
            success, transfer_id, error = bdb.execute_transfer_transaction(
                sender_account_id,
                recipient_account_id,
                amount,
                fee,
                reference
            )
            
            if not success:
                bdb.log_operation("TRANSFER_FAILED", user_id, f"Transaction failed: {error}")
                return (False, error)
            
            # Log successful transfer
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
    
    # ==================== Transfer Status Query ====================
    
    def get_transfer_status(self, token, transfer_id):
        """
        Query transfer status by ID.
        Returns: (success, transfer_info_or_error_message)
        """
        try:
            bdb = self.connect_to_bdb()
            
            # Validate token
            user_id = self.validate_token(token)
            
            # Get transfer record
            transfer = bdb.get_transfer(transfer_id)
            
            if transfer is None:
                return (False, "Transfer not found")
            
            # Log status query
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


def main():
    """Start the BAS server"""
    print("=" * 60)
    print("Bank Application Server (BAS) - Starting")
    print("=" * 60)
    
    try:
        # Create application server instance
        bas_server = BankApplicationServer()
        
        # Start Pyro5 daemon
        daemon = Pyro5.server.Daemon()
        
        # Locate nameserver
        ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
        
        # Register server with daemon
        uri = daemon.register(bas_server)
        
        # Register with nameserver
        ns.register(BAS_SERVER_NAME, uri)
        
        print(f"[BAS] Server registered as '{BAS_SERVER_NAME}'")
        print(f"[BAS] URI: {uri}")
        print("-" * 60)
        print("[BAS] Ready to accept requests from BC clients")
        print("[BAS] Press Ctrl+C to stop")
        print("=" * 60)
        
        # Start request loop
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
