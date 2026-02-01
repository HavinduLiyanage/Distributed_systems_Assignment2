"""
System Test Suite

Comprehensive automated tests validating authentication, balance queries,
fee calculation across all tiers, transfer validation, and idempotency.
"""

import os
import sys
import unittest
import Pyro5.api
import time
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import NAMESERVER_HOST, NAMESERVER_PORT, BAS_SERVER_NAME, DATABASE_FILE, BDB_SERVER_NAME

class TestBankingSystem(unittest.TestCase):
    def setUp(self):
        """Reset test account balance and establish authenticated session before each test."""
        # Fix: Use Pyro5 to BDB for setup instead of direct SQLite connection
        try:
            ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
            
            # Connect to BDB for test setup
            bdb_uri = ns.lookup(BDB_SERVER_NAME)
            self.bdb = Pyro5.api.Proxy(bdb_uri)
            self.bdb.update_balance(1001, 10000000.00)
            
            # Connect to BAS for testing
            bas_uri = ns.lookup(BAS_SERVER_NAME)
            self.bas = Pyro5.api.Proxy(bas_uri)
            
        except Exception as e:
            self.fail(f"Failed to connect to servers: {e}")

        
        self.username = "john"
        self.password = "pass123"
        success, result = self.bas.login(self.username, self.password)
        self.assertTrue(success, f"Login failed: {result}")
        self.token = result

    def test_01_login_invalid_credentials(self):
        """Verify login rejection with incorrect password."""
        success, msg = self.bas.login("john", "wrongpass")
        self.assertFalse(success)
        self.assertIn("Invalid", msg)

    def test_02_login_invalid_username(self):
        """Verify login rejection for non-existent user."""
        success, msg = self.bas.login("nobody", "pass123")
        self.assertFalse(success)
        self.assertIn("Invalid", msg)

    def test_03_get_balance(self):
        """Verify balance query returns non-negative float."""
        success, balance = self.bas.get_balance(self.token)
        self.assertTrue(success)
        self.assertIsInstance(balance, float)
        self.assertGreaterEqual(balance, 0.0)

    def test_04_transfer_validation(self):
        """Verify transfer input validation for invalid recipients, negative amounts, and self-transfers."""
        success, msg = self.bas.submit_transfer(self.token, 999999, 100.0)
        self.assertFalse(success)
        self.assertIn("Recipient account not found", msg)
        success, msg = self.bas.submit_transfer(self.token, 1002, -50.0)
        self.assertFalse(success)
        self.assertIn("positive", msg)
        success, msg = self.bas.submit_transfer(self.token, 1001, 10.0)
        self.assertFalse(success)
        self.assertIn("own account", msg)

    def test_05_fee_tier_1_boundary(self):
        """Test Tier 1 upper boundary: $2,000.00 should incur 0% fee."""
        amount = 2000.00
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 1 Boundary")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], 0.00)

    def test_06_fee_tier_2_boundary_start(self):
        """Test Tier 2 lower boundary: $2,000.01 should incur 0.25% fee."""
        amount = 2000.01
        expected_fee = round(2000.01 * 0.0025, 2)
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 2 Start")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_07_fee_tier_2_boundary_end_cap(self):
        """Test Tier 2 upper boundary: $10,000.00 fee should be capped at $20."""
        amount = 10000.00
        expected_fee = 20.00
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 2 End Cap")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_08_fee_tier_3_boundary_start(self):
        """Test Tier 3 lower boundary: $10,000.01 should incur 0.20% fee."""
        amount = 10000.01
        expected_fee = round(10000.01 * 0.0020, 2)
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 3 Start")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_09_fee_tier_3_boundary_end_cap(self):
        """Test Tier 3 upper boundary: $20,000.00 fee should be capped at $25."""
        amount = 20000.00
        expected_fee = 25.00
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 3 End Cap")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_10_fee_tier_4_boundary_start(self):
        """Test Tier 4 lower boundary: $20,000.01 should incur 0.125% fee."""
        amount = 20000.01
        expected_fee = round(20000.01 * 0.00125, 2)
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 4 Start")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_11_fee_tier_4_boundary_end_cap(self):
        """Test Tier 4 upper boundary: $50,000.00 fee should be capped at $40."""
        amount = 50000.00
        expected_fee = 40.00
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 4 End Cap")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)
    
    def test_12_fee_tier_5_boundary_start(self):
        """Test Tier 5 lower boundary: $50,000.01 should incur 0.08% fee."""
        amount = 50000.01
        expected_fee = round(50000.01 * 0.0008, 2)
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 5 Start")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_13_fee_tier_5_boundary_end_cap(self):
        """Test Tier 5 upper boundary: $100,000.00 fee should be capped at $50."""
        amount = 100000.00
        expected_fee = 50.00
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Tier 5 End Cap")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_14_fee_rounding(self):
        """Verify fee calculation rounds to two decimal places correctly."""
        amount = 3333.33
        expected_fee = 8.33
        
        success, result = self.bas.submit_transfer(self.token, 1002, amount, "Rounding Test")
        self.assertTrue(success, f"Transfer failed: {result}")
        self.assertEqual(result['fee'], expected_fee)

    def test_16_insufficient_funds(self):
        """Verify transfer rejection when balance is insufficient for amount plus fee."""
        success, balance = self.bas.get_balance(self.token)
        self.assertTrue(success)
        
        huge_amount = balance + 100.0
        success, result = self.bas.submit_transfer(self.token, 1002, huge_amount, "Broke Test")
        
        self.assertFalse(success)
        self.assertIn("Insufficient balance", result)

    def test_17_reference_length(self):
        """Verify reference message length validation (200 character limit)."""
        ok_ref = "A" * 200
        success, result = self.bas.submit_transfer(self.token, 1002, 10.0, ok_ref)
        self.assertTrue(success, f"200 char reference failed: {result}")
        
        bad_ref = "A" * 201
        success, result = self.bas.submit_transfer(self.token, 1002, 10.0, bad_ref)
        self.assertFalse(success)
        self.assertIn("too long", result)

    def test_18_idempotency(self):
        """Verify duplicate transfer detection within idempotency window."""
        amount = 1.99
        ref = f"Idempotency Test {time.time()}"
        
        success1, result1 = self.bas.submit_transfer(self.token, 1002, amount, ref)
        self.assertTrue(success1, f"First request failed: {result1}")
        
        success2, result2 = self.bas.submit_transfer(self.token, 1002, amount, ref)
        self.assertFalse(success2)
        self.assertIn("Duplicate transfer", result2)

    def test_19_failed_transfer_persistence(self):
        """Verify failed transfers are recorded with FAILED status."""
        # 1. Trigger failure with insufficient funds
        success, balance = self.bas.get_balance(self.token)
        huge_amount = balance + 500000.0
        success, error_msg = self.bas.submit_transfer(self.token, 1002, huge_amount, "Persistence Test")
        self.assertFalse(success)
        
        # 2. Extract Transfer ID from error message
        # Expected format: "Transaction failed for ID <id>: <error>"
        import re
        match = re.search(r"ID (\d+)", error_msg)
        self.assertTrue(match, f"Could not find Transfer ID in error message: {error_msg}")
        transfer_id = int(match.group(1))
        
        # 3. Query status using the ID
        success, transfer = self.bas.get_transfer_status(self.token, transfer_id)
        self.assertTrue(success, "Could not retrieve failed transfer by ID")
        self.assertEqual(transfer["status"], "FAILED")
        self.assertIn("Insufficient", transfer["reference"])

if __name__ == '__main__':
    print("="*60)
    print("RUNNING SYSTEM TESTS")
    print("Ensure functionality of Client -> BAS -> BDB")
    print("="*60)
    unittest.main()
