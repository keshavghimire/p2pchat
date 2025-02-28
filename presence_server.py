# presence_server.py

"""
Presence Server for the P2P Chat Application.

This server tracks which users are online and allows users to discover 
each other without needing to know IP addresses and ports in advance.
"""

import socket
import threading
import json
import time
from utils import send_message, receive_message


class PresenceServer:
    """
    A server that keeps track of online users and their connection details.

    This server allows users to:
    - Register themselves as online
    - Discover other online users
    - Maintain their online status with heartbeats
    """

    def __init__(self, host="0.0.0.0", port=7000):
        """
        Initialize the presence server.

        Args:
            host: Host address to bind to (default: all interfaces)
            port: Port to listen on (default: 7000)
        """
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.online_users = {}  # username -> {address, port, last_seen}
        self.lock = threading.Lock()

    def start(self):
        """
        Start the presence server and begin accepting connections.

        This method:
        1. Binds to the specified host and port
        2. Starts a cleanup thread to remove stale users
        3. Accepts and processes client connections
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"Presence server running on {self.host}:{self.port}")

            # Start a thread to clean up stale users
            cleanup_thread = threading.Thread(target=self._cleanup_stale_users)
            cleanup_thread.daemon = True
            cleanup_thread.start()

            # Accept client connections
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client, args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")

        except Exception as e:
            print(f"Error starting presence server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def stop(self):
        """Stop the presence server and clean up resources."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
                self.server_socket.close()
            except Exception:
                pass  # Socket might already be closed

    def _handle_client(self, client_socket, address):
        """
        Handle a client request.

        Args:
            client_socket: Socket connected to the client
            address: Client's address as (ip, port) tuple
        """
        try:
            message = receive_message(client_socket)
            if not message:
                return

            msg_type = message.get("type")

            # Process different request types
            if msg_type == "register":
                self._register_user(message, client_socket)
            elif msg_type == "query":
                self._send_online_users(client_socket)
            elif msg_type == "heartbeat":
                self._update_user_heartbeat(message)
            elif msg_type == "unregister":
                self._unregister_user(message)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def _register_user(self, message, client_socket):
        """
        Register a new user or update existing user.

        Args:
            message: Dictionary with registration info
            client_socket: Socket to send response on
        """
        username = message.get("username")
        user_port = message.get("port")
        client_ip = message.get("address")

        # Validate required fields
        if not username or not user_port:
            send_message(
                client_socket,
                {
                    "type": "register_response",
                    "success": False,
                    "reason": "Missing required fields",
                },
            )
            return

        # Store user information
        with self.lock:
            self.online_users[username] = {
                "address": client_ip,
                "port": user_port,
                "last_seen": time.time(),
            }

        send_message(client_socket, {"type": "register_response", "success": True})
        print(f"Registered user: {username} at {client_ip}:{user_port}")

    def _send_online_users(self, client_socket):
        """Send list of online users to client"""
        with self.lock:
            user_list = [
                {"username": username, "address": data["address"], "port": data["port"]}
                for username, data in self.online_users.items()
            ]

        send_message(client_socket, {"type": "online_users", "users": user_list})

    def _update_user_heartbeat(self, message):
        """Update user's last_seen timestamp"""
        username = message.get("username")

        if username:
            with self.lock:
                if username in self.online_users:
                    self.online_users[username]["last_seen"] = time.time()

    def _unregister_user(self, message):
        """Remove user from online list"""
        username = message.get("username")

        if username:
            with self.lock:
                if username in self.online_users:
                    del self.online_users[username]
                    print(f"Unregistered user: {username}")

    def _cleanup_stale_users(self):
        """Periodically remove users who haven't sent heartbeats"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            current_time = time.time()
            stale_threshold = 60  # Consider users stale after 60 seconds

            to_remove = []

            with self.lock:
                for username, data in self.online_users.items():
                    if current_time - data["last_seen"] > stale_threshold:
                        to_remove.append(username)

                for username in to_remove:
                    del self.online_users[username]
                    print(f"Removed stale user: {username}")


# When running as a standalone script, start the presence server
if __name__ == "__main__":
    server = PresenceServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("Stopping presence server...")
        server.stop()
