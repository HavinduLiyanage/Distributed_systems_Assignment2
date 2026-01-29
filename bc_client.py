"""
Banking Client (BC)
CSI3344 Assignment 2 - Distributed Banking System
Phase 2: Client Tier

This is the customer-facing banking client.
Users can login, view balance, submit transfers, and query transfer status.
"""

import Pyro5.api
import sys
from config import NAMESERVER_HOST, NAMESERVER_PORT, BAS_SERVER_NAME


class BankingClient:
    """
    Banking client that communicates with BAS server.
    Provides interactive menu for banking operations.
    """
    
    def __init__(self):
        """Initialize the banking client"""
        self.bas = None  # BAS server proxy
        self.token = None  # Session token after login
        self.username = None  # Current username
    
    def connect_to_bas(self):
        """Connect to BAS server via Pyro5"""
        if self.bas is None:
            try:
                ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
                uri = ns.lookup(BAS_SERVER_NAME)
                self.bas = Pyro5.api.Proxy(uri)
                print("[BC] Connected to Bank Application Server")
            except Exception as e:
                print(f"\n[ERROR] Failed to connect to BAS server: {e}")
                print("\nMake sure:")
                print("  1. Nameserver is running: python start_nameserver.py")
                print("  2. BDB server is running: python bdb_server.py")
                print("  3. BAS server is running: python bas_server.py")
                sys.exit(1)
        return self.bas
    
    def display_header(self):
        """Display application header"""
        print("\n" + "=" * 60)
        print("  DISTRIBUTED BANKING SYSTEM - Three-Tier Architecture")
        print("  CSI3344 Assignment 2")
        print("=" * 60)
    
    def display_menu(self):
        """Display main menu"""
        print("\n" + "-" * 60)
        if self.token:
            print(f"  Logged in as: {self.username}")
        else:
            print("  Status: Not logged in")
        print("-" * 60)
        print("  MAIN MENU:")
        print("  1. Login")
        print("  2. View Balance")
        print("  3. Submit Transfer")
        print("  4. Query Transfer Status")
        print("  5. Exit")
        print("-" * 60)
    
    def login(self):
        """Handle user login"""
        print("\n" + "=" * 60)
        print("  LOGIN")
        print("=" * 60)
        
        if self.token:
            print(f"Already logged in as '{self.username}'")
            return
        
        print("\nMock credentials for testing:")
        print("  Username: john, Password: pass123 (Balance: $50,000)")
        print("  Username: jane, Password: pass456 (Balance: $75,000)")
        print()
        
        try:
            username = input("Enter username: ").strip()
            password = input("Enter password: ").strip()
            
            if not username or not password:
                print("[ERROR] Username and password cannot be empty")
                return
            
            print("\nAuthenticating...")
            bas = self.connect_to_bas()
            success, result = bas.login(username, password)
            
            if success:
                self.token = result
                self.username = username
                print(f"\n✓ Login successful! Welcome, {username}")
            else:
                print(f"\n✗ Login failed: {result}")
                
        except Exception as e:
            print(f"\n[ERROR] Login error: {e}")
    
    def view_balance(self):
        """View account balance"""
        print("\n" + "=" * 60)
        print("  BALANCE QUERY")
        print("=" * 60)
        
        if not self.token:
            print("\n✗ Please login first")
            return
        
        try:
            print("\nQuerying balance...")
            bas = self.connect_to_bas()
            success, result = bas.get_balance(self.token)
            
            if success:
                balance = result
                print(f"\n{'─' * 60}")
                print(f"  Your current balance: ${balance:,.2f}")
                print(f"{'─' * 60}")
            else:
                print(f"\n✗ Failed to retrieve balance: {result}")
                
        except Exception as e:
            print(f"\n[ERROR] Balance query error: {e}")
    
    def submit_transfer(self):
        """Submit a transfer request"""
        print("\n" + "=" * 60)
        print("  SUBMIT TRANSFER")
        print("=" * 60)
        
        if not self.token:
            print("\n✗ Please login first")
            return
        
        print("\nAccount IDs:")
        print("  1001 - John's account")
        print("  1002 - Jane's account")
        print()
        
        try:
            # Get transfer details
            recipient_input = input("Enter recipient account ID: ").strip()
            if not recipient_input:
                print("[ERROR] Recipient account ID cannot be empty")
                return
            
            try:
                recipient_account_id = int(recipient_input)
            except ValueError:
                print("[ERROR] Account ID must be a number")
                return
            
            amount_input = input("Enter transfer amount ($): ").strip()
            if not amount_input:
                print("[ERROR] Amount cannot be empty")
                return
            
            try:
                amount = float(amount_input)
            except ValueError:
                print("[ERROR] Amount must be a number")
                return
            
            reference = input("Enter reference message (optional): ").strip()
            
            # Confirm transfer
            print(f"\n{'─' * 60}")
            print(f"  Transfer Details:")
            print(f"  Recipient Account: {recipient_account_id}")
            print(f"  Amount: ${amount:,.2f}")
            print(f"  Reference: {reference if reference else '(none)'}")
            print(f"{'─' * 60}")
            
            confirm = input("\nConfirm transfer? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Transfer cancelled")
                return
            
            # Submit transfer
            print("\nProcessing transfer...")
            bas = self.connect_to_bas()
            success, result = bas.submit_transfer(self.token, recipient_account_id, amount, reference)
            
            if success:
                print(f"\n{'─' * 60}")
                print("  ✓ TRANSFER SUCCESSFUL")
                print(f"{'─' * 60}")
                print(f"  Transfer ID: {result['transfer_id']}")
                print(f"  Amount: ${result['amount']:,.2f}")
                print(f"  Fee: ${result['fee']:,.2f}")
                print(f"  Total Deducted: ${result['amount'] + result['fee']:,.2f}")
                print(f"  Status: {result['status']}")
                print(f"{'─' * 60}")
            else:
                print(f"\n✗ Transfer failed: {result}")
                
        except Exception as e:
            print(f"\n[ERROR] Transfer error: {e}")
    
    def query_transfer_status(self):
        """Query the status of a transfer"""
        print("\n" + "=" * 60)
        print("  QUERY TRANSFER STATUS")
        print("=" * 60)
        
        if not self.token:
            print("\n✗ Please login first")
            return
        
        try:
            transfer_id_input = input("\nEnter transfer ID: ").strip()
            if not transfer_id_input:
                print("[ERROR] Transfer ID cannot be empty")
                return
            
            try:
                transfer_id = int(transfer_id_input)
            except ValueError:
                print("[ERROR] Transfer ID must be a number")
                return
            
            print("\nQuerying transfer status...")
            bas = self.connect_to_bas()
            success, result = bas.get_transfer_status(self.token, transfer_id)
            
            if success:
                print(f"\n{'─' * 60}")
                print("  TRANSFER DETAILS")
                print(f"{'─' * 60}")
                print(f"  Transfer ID: {result['transfer_id']}")
                print(f"  From Account: {result['from_account_id']}")
                print(f"  To Account: {result['to_account_id']}")
                print(f"  Amount: ${result['amount']:,.2f}")
                print(f"  Fee: ${result['fee']:,.2f}")
                print(f"  Status: {result['status']}")
                print(f"  Reference: {result['reference'] if result['reference'] else '(none)'}")
                print(f"  Created: {result['created_at']}")
                if result['completed_at']:
                    print(f"  Completed: {result['completed_at']}")
                print(f"{'─' * 60}")
            else:
                print(f"\n✗ Failed to retrieve transfer: {result}")
                
        except Exception as e:
            print(f"\n[ERROR] Transfer status query error: {e}")
    
    def run(self):
        """Main application loop"""
        self.display_header()
        
        # Connect to BAS server
        self.connect_to_bas()
        
        while True:
            self.display_menu()
            
            try:
                choice = input("\nSelect option (1-5): ").strip()
                
                if choice == '1':
                    self.login()
                elif choice == '2':
                    self.view_balance()
                elif choice == '3':
                    self.submit_transfer()
                elif choice == '4':
                    self.query_transfer_status()
                elif choice == '5':
                    print("\n" + "=" * 60)
                    print("  Thank you for using Distributed Banking System")
                    print("=" * 60)
                    print()
                    sys.exit(0)
                else:
                    print("\n✗ Invalid option. Please select 1-5")
                    
            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("  Application interrupted by user")
                print("=" * 60)
                print()
                sys.exit(0)
            except Exception as e:
                print(f"\n[ERROR] Unexpected error: {e}")


def main():
    """Entry point for banking client"""
    try:
        client = BankingClient()
        client.run()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
