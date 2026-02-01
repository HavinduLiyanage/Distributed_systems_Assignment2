
import os
import sys
import Pyro5.api
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import NAMESERVER_HOST, NAMESERVER_PORT, BAS_SERVER_NAME

def run_diagnostic():
    try:
        ns = Pyro5.api.locate_ns(host=NAMESERVER_HOST, port=NAMESERVER_PORT)
        uri = ns.lookup(BAS_SERVER_NAME)
        bas = Pyro5.api.Proxy(uri)
        
        success, token = bas.login("john", "pass123")
        if not success:
            print("Login failed")
            return
        
        print(f"Token: {token}")
        
        print("\n--- Diagnostic 1: Insufficient Funds ---")
        success, result = bas.submit_transfer(token, 1002, 1000000000.0, "Broke Test")
        print(f"Result: {success}, Message: {result}")
        
        print("\n--- Diagnostic 2: Reference Length Limit ---")
        long_ref = "A" * 250
        success, result = bas.submit_transfer(token, 1002, 10.0, long_ref)
        print(f"Result: {success}, Message: {result}")
        if success:
             print("WARNING: Reference > 200 chars was accepted!")

        print("\n--- Diagnostic 3: Repeated Requests ---")
        amount = 1.23
        ref = f"Repeat Test {time.time()}"
        print(f"First request: ${amount} with ref '{ref}'")
        success1, result1 = bas.submit_transfer(token, 1002, amount, ref)
        print(f"Result 1: {success1}")
        
        print(f"Second (duplicate) request...")
        success2, result2 = bas.submit_transfer(token, 1002, amount, ref)
        print(f"Result 2: {success2}")
        
        if success1 and success2:
            print("WARNING: Duplicate request was processed twice (not idempotent)!")
            
    except Exception as e:
        print(f"Diagnostic failed: {e}")

if __name__ == "__main__":
    run_diagnostic()
