"""
Pyro5 Nameserver Starter

Initializes and runs the Pyro5 nameserver for service discovery.
The nameserver enables servers and clients to locate registered services by name.
"""

import os
import sys
import Pyro5.api
import Pyro5.nameserver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import NAMESERVER_HOST, NAMESERVER_PORT


def start_nameserver():
    """Initialize and run the Pyro5 nameserver with configured host and port."""
    try:
        print("=" * 60)
        print("Starting Pyro5 Nameserver")
        print("=" * 60)
        print(f"Host: {NAMESERVER_HOST}")
        print(f"Port: {NAMESERVER_PORT}")
        print("-" * 60)
        print("Press Ctrl+C to stop the nameserver")
        print("=" * 60)
        
        uri, daemon, broadcast = Pyro5.nameserver.start_ns(
            host=NAMESERVER_HOST,
            port=NAMESERVER_PORT,
            enableBroadcast=False
        )
        
        print(f"Nameserver URI: {uri}")
        print("Nameserver is running...")
        
        daemon.requestLoop()
        
    except KeyboardInterrupt:
        print("\n\nNameserver stopped by user")
    except Exception as e:
        print(f"Error starting nameserver: {e}")
        print("\nMake sure no other nameserver is running on port {NAMESERVER_PORT}")


if __name__ == "__main__":
    start_nameserver()
