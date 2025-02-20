# p2p_chat.py
import socket
import threading
import json
import time
from typing import Dict
import sys
import random
import traceback

from message_handler import MessageHandler
from utils import send_message


class P2PChat:
    def __init__(self, username: str, host: str = '0.0.0.0', port: int = None):
        self.username = username
        self.host = host
        self.port = port or random.randint(49152, 65535)
        self.peers: Dict[str, dict] = {}
        self.connected = True
        self.lock = threading.Lock()
        self.message_handler = MessageHandler(self)  # Initialize MessageHandler

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
        except socket.error as e:
            print(f"Error binding socket: {e}. Exiting.")
            sys.exit(1)
        self.server_socket.listen(5)

        self.server_thread = threading.Thread(target=self._listen_for_connections)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        print(f"P2P Chat started on port {self.port}")
        print(f"Your username: {username}")

    def _listen_for_connections(self):
        while self.connected:
            try:
                client_socket, address = self.server_socket.accept()
                client_handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_handler.daemon = True
                client_handler.start()
            except socket.error as e:
                if self.connected:
                    print(f"Error accepting connection: {e}")
            except Exception as e:
                print(f"Unexpected error in _listen_for_connections: {e}")
                traceback.print_exc()

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        try:
            while self.connected:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message = json.loads(data.decode())
                except json.JSONDecodeError:
                    print(f"Invalid JSON received from {address}")
                    break

                self.message_handler.handle_message(client_socket, address, message)

        except Exception as e:
            print(f"Error handling client {address}: {e}")
            traceback.print_exc()  # Print full traceback
        finally:
            client_socket.close()

    def broadcast_message(self, message: str):
        msg_data = {
            'type': 'chat',
            'username': self.username,
            'content': message
        }

        with self.lock:
            peers_copy = self.peers.copy()

        for peer_username, peer_info in peers_copy.items():
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_info['address'], peer_info['port']))
                send_message(peer_socket, msg_data)
                peer_socket.close()
            except Exception as e:
                print(f"Error sending message to {peer_username}: {e}")
                # Remove unreachable peer
                with self.lock:
                    if peer_username in self.peers:
                        del self.peers[peer_username]

    def join_network(self, known_host: str, known_port: int):
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((known_host, known_port))

            send_message(peer_socket, {
                'type': 'join',
                'username': self.username,
                'port': self.port
            })

            data = peer_socket.recv(4096)
            if data:
                message = json.loads(data.decode())
                if message['type'] == 'welcome':
                    with self.lock:
                        self.peers[message['username']] = {
                            'address': known_host,
                            'port': message['port'],
                            'last_seen': time.time()
                        }
                    print(f"Successfully joined the network through {message['username']}")

                    # After joining, request the list of existing peers
                    send_message(peer_socket, {'type': 'request_peers'})

                    # Now listen for the list of peers
                    data = peer_socket.recv(4096)
                    if data:
                        message = json.loads(data.decode())
                        if message['type'] == 'peer_list':
                            with self.lock:
                                for peer in message['peers']:
                                    self.peers[peer['username']] = peer
                            print(f"Received list of existing peers.")
                else:
                    print("Unexpected message received during join:", message)

            peer_socket.close()
        except Exception as e:
            print(f"Error joining network: {e}")

    def _send_heartbeat(self):
        while self.connected:
            with self.lock:
                peers_copy = self.peers.copy()

            for peer_username, peer_info in peers_copy.items():
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.settimeout(5)  # Add a timeout
                    peer_socket.connect((peer_info['address'], peer_info['port']))
                    send_message(peer_socket, {
                        'type': 'heartbeat',
                        'username': self.username
                    })
                    peer_socket.close()
                except Exception:
                    # Remove unreachable peer
                    with self.lock:
                        if peer_username in self.peers:
                            del self.peers[peer_username]
                            print(f"\n{peer_username} appears to be offline.")

            time.sleep(10)

    def disconnect(self):
        self.connected = False

        with self.lock:
            peers_copy = self.peers.copy()

        for peer_username, peer_info in peers_copy.items():
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_info['address'], peer_info['port']))
                send_message(peer_socket, {
                    'type': 'leave',
                    'username': self.username
                })
                peer_socket.close()
            except Exception:
                pass

        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Ignore if socket is already closed
        finally:
            self.server_socket.close()
