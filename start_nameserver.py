"""
Pyro5 Nameserver Starter
CSI3344 Assignment 2 - Distributed Banking System

This script starts the Pyro5 nameserver which allows 
servers and clients to locate each other.
"""

import Pyro5.api
import Pyro5.nameserver
from config import NAMESERVER_HOST, NAMESERVER_PORT


def start_nameserver():
    """Start the Pyro5 nameserver"""
    try:
        print("=" * 60)
        print("Starting Pyro5 Nameserver")
        print("=" * 60)
        print(f"Host: {NAMESERVER_HOST}")
        print(f"Port: {NAMESERVER_PORT}")
        print("-" * 60)
        print("Press Ctrl+C to stop the nameserver")
        print("=" * 60)
        
        # Start the nameserver
        # Start the nameserver components
        uri, daemon, broadcast = Pyro5.nameserver.start_ns(
            host=NAMESERVER_HOST,
            port=NAMESERVER_PORT,
            enableBroadcast=False
        )
        
        print(f"Nameserver URI: {uri}")
        print("Nameserver is running...")
        
        # Enter the request loop
        daemon.requestLoop()
        
    except KeyboardInterrupt:
        print("\n\nNameserver stopped by user")
    except Exception as e:
        print(f"Error starting nameserver: {e}")
        print("\nMake sure no other nameserver is running on port {NAMESERVER_PORT}")


if __name__ == "__main__":
    start_nameserver()
