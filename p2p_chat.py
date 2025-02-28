# p2p_chat.py
import sys
import socket
import json
import time
import random
import threading
from typing import Dict, Callable
from utils import send_message, receive_message  # Import the new function


class P2PChat:
    def __init__(
        self,
        username: str,
        host: str = "0.0.0.0",
        port: int = None,
        ui_callback: Callable = None,
        file_chunk_callback: Callable = None,
        status_callback: Callable = None,
    ):
        self.username = username
        self.host = host
        self.port = port or random.randint(49152, 65535)
        self.peers: Dict[str, dict] = {}
        self.connected = True
        self.lock = threading.Lock()
        self.ui_callback = ui_callback
        self.status_callback = status_callback  # Callback for status changes

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
        except socket.error as e:
            self._notify_ui(f"Error binding socket: {e}. Exiting.")
            sys.exit(1)
        self.server_socket.listen(5)

        self.server_thread = threading.Thread(target=self._listen_for_connections)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        self._notify_ui(
            f"P2P Chat started on port {self.port}\nYour username: {username}"
        )
        self.file_chunk_callback = file_chunk_callback

    def _notify_ui(self, message: str):
        if self.ui_callback:
            self.ui_callback(message)

    def _listen_for_connections(self):
        while self.connected:
            try:
                client_socket, address = self.server_socket.accept()
                client_handler = threading.Thread(
                    target=self._handle_client, args=(client_socket, address)
                )
                client_handler.daemon = True
                client_handler.start()
            except socket.error as e:
                if self.connected:
                    self._notify_ui(f"Error accepting connection: {e}")
            except Exception as e:
                self._notify_ui(f"Unexpected error in _listen_for_connections: {e}")

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        try:
            while self.connected:
                # Use the new receive_message function
                message = receive_message(client_socket)
                if not message:
                    break

                self._handle_message(client_socket, address, message)

        except Exception as e:
            self._notify_ui(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()

    def _handle_message(
        self, client_socket: socket.socket, address: tuple, message: dict
    ):
        if message["type"] == "join":
            with self.lock:
                self.peers[message["username"]] = {
                    "address": address[0],
                    "port": message["port"],
                    "last_seen": time.time(),
                    "status": "online",  # Add status field
                }
            send_message(
                client_socket,
                {"type": "welcome", "username": self.username, "port": self.port},
            )
            self._notify_ui(f"{message['username']} joined the network.")

            # Notify status callback of new online peer
            if self.status_callback:
                self.status_callback(message["username"], "online")

        elif message["type"] == "chat":
            self._notify_ui(f"{message['username']}: {message['content']}")

        elif message["type"] == "heartbeat":
            with self.lock:
                if message["username"] in self.peers:
                    peer_info = self.peers[message["username"]]
                    old_status = peer_info.get("status", "unknown")
                    peer_info["last_seen"] = time.time()
                    peer_info["status"] = "online"

                    # Notify if status changed from offline to online
                    if old_status != "online" and self.status_callback:
                        self.status_callback(message["username"], "online")

        elif message["type"] == "leave":
            with self.lock:
                if message["username"] in self.peers:
                    del self.peers[message["username"]]
            self._notify_ui(f"{message['username']} left the network.")

        elif message["type"] == "request_peers":
            with self.lock:
                peers_list = [
                    {"username": peer, "address": info["address"], "port": info["port"]}
                    for peer, info in self.peers.items()
                ]
            send_message(client_socket, {"type": "peer_list", "peers": peers_list})

        elif message["type"] == "file_chunk":
            # Add sender information before forwarding to the file_chunk_callback
            if "sender" in message and message["sender"] == "You":
                # Replace "You" with the actual sender's username
                message["sender"] = message.get("username", "Unknown")
            elif "sender" not in message:
                message["sender"] = message.get("username", "Unknown")

            # Forward the entire message to the file_chunk_callback for handling
            if self.file_chunk_callback:
                self.file_chunk_callback(message)
        else:
            self._notify_ui(f"Unknown message type: {message['type']} from {address}")

    def broadcast_message(self, message: str):
        msg_data = {"type": "chat", "username": self.username, "content": message}

        with self.lock:
            peers_copy = self.peers.copy()

        for peer_username, peer_info in peers_copy.items():
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_info["address"], peer_info["port"]))
                send_message(peer_socket, msg_data)
                peer_socket.close()
            except Exception as e:
                self._notify_ui(f"Error sending message to {peer_username}: {e}")
                with self.lock:
                    if peer_username in self.peers:
                        del self.peers[peer_username]

    def join_network(self, known_host: str, known_port: int):
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((known_host, known_port))

            # Send join request with our username and port
            send_message(
                peer_socket,
                {"type": "join", "username": self.username, "port": self.port},
            )

            # Use the new receive_message function instead of raw socket.recv
            message = receive_message(peer_socket)
            if message and message.get("type") == "welcome":
                with self.lock:
                    self.peers[message["username"]] = {
                        "address": known_host,
                        "port": message["port"],
                        "last_seen": time.time(),
                        "status": "online",  # Add status field
                    }
                self._notify_ui(
                    f"Successfully joined the network through {message['username']}."
                )

                # Request list of peers
                send_message(peer_socket, {"type": "request_peers"})

                # Receive peer list using the new function
                peer_list_msg = receive_message(peer_socket)
                if peer_list_msg and peer_list_msg.get("type") == "peer_list":
                    with self.lock:
                        for peer in peer_list_msg["peers"]:
                            if peer["username"] != self.username:
                                self.peers[peer["username"]] = {
                                    "address": peer["address"],
                                    "port": peer["port"],
                                    "last_seen": time.time(),
                                    "status": "online",  # Add status field
                                }
                    self._notify_ui(
                        f"Received list of existing peers: {len(peer_list_msg['peers'])} peers found."
                    )

                    # Notify status callback of new online peer
                    if self.status_callback:
                        self.status_callback(message["username"], "online")
            else:
                self._notify_ui(
                    f"Unexpected or missing response when joining: {message}"
                )

            peer_socket.close()
            return True
        except Exception as e:
            self._notify_ui(f"Error joining network: {e}")
            return False

    def _send_heartbeat(self):
        while self.connected:
            current_time = time.time()

            with self.lock:
                peers_copy = self.peers.copy()

            for peer_username, peer_info in peers_copy.items():
                try:
                    # Check if peer might be offline (no heartbeat for 15 seconds)
                    if current_time - peer_info.get("last_seen", 0) > 15:
                        old_status = peer_info.get("status", "unknown")

                        # Try to connect
                        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        peer_socket.settimeout(5)
                        peer_socket.connect((peer_info["address"], peer_info["port"]))
                        send_message(
                            peer_socket,
                            {"type": "heartbeat", "username": self.username},
                        )
                        peer_socket.close()

                        # Update last seen and ensure status is online
                        with self.lock:
                            if peer_username in self.peers:
                                self.peers[peer_username]["last_seen"] = time.time()
                                self.peers[peer_username]["status"] = "online"

                                # Notify if status changed
                                if old_status != "online" and self.status_callback:
                                    self.status_callback(peer_username, "online")

                except Exception:
                    # Connection failed - mark as offline
                    with self.lock:
                        if peer_username in self.peers:
                            old_status = self.peers[peer_username].get(
                                "status", "unknown"
                            )
                            self.peers[peer_username]["status"] = "offline"

                            # Notify UI and status callback
                            if old_status != "offline":
                                self._notify_ui(
                                    f"{peer_username} appears to be offline."
                                )
                                if self.status_callback:
                                    self.status_callback(peer_username, "offline")

            time.sleep(10)  # Check every 10 seconds

    # Add a method to get all online peers
    def get_online_peers(self):
        with self.lock:
            return {
                username: info
                for username, info in self.peers.items()
                if info.get("status") == "online"
            }

    def disconnect(self):
        self.connected = False

        with self.lock:
            peers_copy = self.peers.copy()

        for peer_username, peer_info in peers_copy.items():
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_info["address"], peer_info["port"]))
                send_message(peer_socket, {"type": "leave", "username": self.username})
                peer_socket.close()
            except Exception:
                pass

        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.server_socket.close()
