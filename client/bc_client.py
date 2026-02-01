"""
Banking Client (BC)

Customer-facing terminal interface for account management and transfers.
Communicates with BAS server for all operations.
"""

import os
import sys
import Pyro5.api

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import NAMESERVER_HOST, NAMESERVER_PORT, BAS_SERVER_NAME


class BankingClient:
    """
    Interactive banking terminal for end users.
    Manages session state and provides menu-driven interface for banking operations.
    """
    
    def __init__(self):
        """Initialize client state with null connection and authentication."""
        self.bas = None
        self.token = None
        self.username = None
    
    def connect_to_bas(self):
        """Establish Pyro5 connection to BAS server via nameserver lookup."""
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
        """Print application banner."""
        print("\n" + "=" * 60)
        print("  DISTRIBUTED BANKING SYSTEM - Three-Tier Architecture")
        print("  CSI3344 Assignment 2")
        print("=" * 60)
    
    def display_menu(self):
        """Print main menu with current authentication status."""
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
        print("  5. View Transaction History")
        print("  6. Exit")
        print("-" * 60)
    
    def login(self):
        """Prompt for credentials and authenticate with BAS server."""
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
        """Query and display current account balance for authenticated user."""
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
        """Collect transfer details, preview fees, and execute transfer after confirmation."""
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
            
            print("\nCalculating fees...")
            bas = self.connect_to_bas()
            fee = bas.calculate_fee(amount)
            total_deduction = amount + fee
            print(f"\n{'─' * 60}")
            print(f"  Transfer Details:")
            print(f"  Recipient Account: {recipient_account_id}")
            print(f"  Amount: ${amount:,.2f}")
            print(f"  Fee: ${fee:,.2f}")
            print(f"  Total Deduction: ${total_deduction:,.2f}")
            print(f"  Reference: {reference if reference else '(none)'}")
            print(f"{'─' * 60}")
            
            confirm = input("\nConfirm transfer? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Transfer cancelled")
                return
            
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
        """Retrieve and display detailed transfer information by ID."""
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
    
    def view_transaction_history(self):
        """Fetch and display transaction history for authenticated user's account."""
        print("\n" + "=" * 60)
        print("  TRANSACTION HISTORY")
        print("=" * 60)
        
        if not self.token:
            print("\n✗ Please login first")
            return
        
        try:
            print("\nRetrieving transaction history...")
            bas = self.connect_to_bas()
            success, result = bas.get_transaction_history(self.token)
            
            if success:
                transactions = result
                if not transactions:
                    print("\nNo transactions found for this account.")
                    return
                
                # Get current account to determine if transaction is IN or OUT
                _, balance_info = bas.get_balance(self.token)
                # Note: This is a hacky way to get the user's account ID if we don't store it
                # In a real app we'd get the account ID during login
                # For now let's use the first transaction to determine the current account ID
                # since we know the user is part of every transaction in the list
                # or better, let's just show from/to accounts.
                
                print(f"\n{'─' * 110}")
                print(f"  {'ID':<5} | {'Date/Time':<20} | {'Type':<8} | {'Account':<10} | {'Amount':<12} | {'Fee':<8} | {'Status':<10}")
                print(f"{'─' * 110}")
                
                my_account_id = 1001 if self.username == "john" else (1002 if self.username == "jane" else None)
                
                for tx in transactions:
                    dt = tx["created_at"].split(".")[0].replace("T", " ")
                    is_outgoing = tx["from_account_id"] == my_account_id
                    
                    tx_type = "SENT" if is_outgoing else "RECEIVED"
                    other_account = tx["to_account_id"] if is_outgoing else tx["from_account_id"]
                    
                    line = f"  {tx['transfer_id']:<5} | {dt:<20} | {tx_type:<8} | {other_account:<10} | "
                    line += f"${tx['amount']:>10,.2f} | "
                    line += f"${tx['fee']:>6,.2f} | " if is_outgoing else f"{' ':>7} | "
                    line += f"{tx['status']}"
                    
                    print(line)
                    if tx['reference']:
                        print(f"        Ref: {tx['reference']}")
                
                print(f"{'─' * 110}")
            else:
                print(f"\n✗ Failed to retrieve transaction history: {result}")
                
        except Exception as e:
            print(f"\n[ERROR] Transaction history query error: {e}")
    
    def run(self):
        """Main application loop with menu handling and error recovery."""
        self.display_header()
        
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
                    self.view_transaction_history()
                elif choice == '6':
                    print("\n" + "=" * 60)
                    print("  Thank you for using Distributed Banking System")
                    print("=" * 60)
                    print()
                    sys.exit(0)
                else:
                    print("\n✗ Invalid option. Please select 1-6")
                    
            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("  Application interrupted by user")
                print("=" * 60)
                print()
                sys.exit(0)
            except Exception as e:
                print(f"\n[ERROR] Unexpected error: {e}")


def main():
    """Initialize and run banking client application."""
    try:
        client = BankingClient()
        client.run()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
