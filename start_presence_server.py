# start_presence_server.py
"""
Simple script to start the presence server.
Run this script before trying to use presence-based connections.
"""

from presence_server import PresenceServer

if __name__ == "__main__":
    print("Starting P2P Chat Presence Server...")
    print("Press Ctrl+C to stop the server.")

    server = PresenceServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nStopping presence server...")
        server.stop()
        print("Server stopped.")
