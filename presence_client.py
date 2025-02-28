import socket
import threading
import time
from utils import send_message, receive_message


class PresenceClient:
    """Client for interacting with the presence server to register and discover peers"""

    def __init__(self, username, port, presence_server="127.0.0.1", presence_port=7000):
        self.username = username
        self.port = port  # User's P2P chat port
        self.presence_server = presence_server
        self.presence_port = presence_port
        self.registered = False
        self.heartbeat_thread = None
        self.running = False

    def register(self):
        """Register with the presence server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Add timeout to avoid hanging

            try:
                sock.connect((self.presence_server, self.presence_port))
            except ConnectionRefusedError:
                print(
                    f"Presence server not running at {self.presence_server}:{self.presence_port}"
                )
                print(
                    "Start the presence server first by running start_presence_server.py"
                )
                return False

            # Get the local IP address that can be used by other peers
            # This is a simple approach - in a real-world scenario you might
            # need more sophisticated methods to get the correct external IP
            local_ip = sock.getsockname()[0]
            if local_ip == "0.0.0.0":
                local_ip = "127.0.0.1"  # Fallback to localhost

            send_message(
                sock,
                {
                    "type": "register",
                    "username": self.username,
                    "port": self.port,
                    "address": local_ip,
                },
            )

            response = receive_message(sock)
            sock.close()

            if response and response.get("success"):
                self.registered = True
                self.running = True

                # Start heartbeat thread
                self.heartbeat_thread = threading.Thread(target=self._send_heartbeats)
                self.heartbeat_thread.daemon = True
                self.heartbeat_thread.start()

                return True
            else:
                reason = (
                    response.get("reason", "Unknown error")
                    if response
                    else "No response"
                )
                print(f"Registration failed: {reason}")
                return False

        except Exception as e:
            print(f"Error registering with presence server: {e}")
            return False

    def unregister(self):
        """Unregister from the presence server"""
        self.running = False

        if not self.registered:
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.presence_server, self.presence_port))

            send_message(sock, {"type": "unregister", "username": self.username})

            sock.close()
            self.registered = False
            print("Unregistered from presence server")

        except Exception as e:
            print(f"Error unregistering from presence server: {e}")

    def get_online_users(self):
        """Get list of online users from the presence server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.presence_server, self.presence_port))

            send_message(sock, {"type": "query"})

            response = receive_message(sock)
            sock.close()

            if response and response.get("type") == "online_users":
                # Filter out ourselves from the list
                return [
                    user
                    for user in response.get("users", [])
                    if user.get("username") != self.username
                ]

            return []

        except Exception as e:
            print(f"Error querying online users: {e}")
            return []

    def _send_heartbeats(self):
        """Send periodic heartbeats to the presence server"""
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.presence_server, self.presence_port))

                send_message(sock, {"type": "heartbeat", "username": self.username})

                sock.close()
            except Exception as e:
                print(f"Error sending heartbeat: {e}")

            time.sleep(20)  # Send heartbeat every 20 seconds
