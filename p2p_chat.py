# p2p_chat.py
import sys
import socket
import json
import time
import random
import threading
from typing import Dict, Callable

class P2PChat:
    def __init__(self, username: str, host: str = '0.0.0.0', port: int = None, ui_callback: Callable = None):
        self.username = username
        self.host = host
        self.port = port or random.randint(49152, 65535)
        self.peers: Dict[str, dict] = {}
        self.connected = True
        self.lock = threading.Lock()
        self.ui_callback = ui_callback

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

        self._notify_ui(f"P2P Chat started on port {self.port}\nYour username: {username}")

    def _notify_ui(self, message: str):
        if self.ui_callback:
            self.ui_callback(message)

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
                    self._notify_ui(f"Error accepting connection: {e}")
            except Exception as e:
                self._notify_ui(f"Unexpected error in _listen_for_connections: {e}")

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        try:
            while self.connected:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message = json.loads(data.decode())
                except json.JSONDecodeError:
                    self._notify_ui(f"Invalid JSON received from {address}")
                    break

                self._handle_message(client_socket, address, message)

        except Exception as e:
            self._notify_ui(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()

    def _handle_message(self, client_socket: socket.socket, address: tuple, message: dict):
        if message['type'] == 'join':
            with self.lock:
                self.peers[message['username']] = {
                    'address': address[0],
                    'port': message['port'],
                    'last_seen': time.time()
                }
            send_message(client_socket, {
                'type': 'welcome',
                'username': self.username,
                'port': self.port
            })
            self._notify_ui(f"{message['username']} joined the network.")

        elif message['type'] == 'chat':
            self._notify_ui(f"{message['username']}: {message['content']}")

        elif message['type'] == 'heartbeat':
            with self.lock:
                if message['username'] in self.peers:
                    self.peers[message['username']]['last_seen'] = time.time()

        elif message['type'] == 'leave':
            with self.lock:
                if message['username'] in self.peers:
                    del self.peers[message['username']]
            self._notify_ui(f"{message['username']} left the network.")

        elif message['type'] == 'request_peers':
            with self.lock:
                peers_list = [{
                    'username': peer,
                    'address': info['address'],
                    'port': info['port']
                } for peer, info in self.peers.items()]
            send_message(client_socket, {
                'type': 'peer_list',
                'peers': peers_list
            })

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
                self._notify_ui(f"Error sending message to {peer_username}: {e}")
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
                    self._notify_ui(f"Successfully joined the network through {message['username']}.")

                    send_message(peer_socket, {'type': 'request_peers'})
                    data = peer_socket.recv(4096)
                    if data:
                        message = json.loads(data.decode())
                        if message['type'] == 'peer_list':
                            with self.lock:
                                for peer in message['peers']:
                                    if peer['username'] != self.username:
                                        self.peers[peer['username']] = {
                                            'address': peer['address'],
                                            'port': peer['port'],
                                            'last_seen': time.time()
                                        }
                            self._notify_ui(f"Received list of existing peers: {len(message['peers'])} peers found.")
                else:
                    self._notify_ui(f"Unexpected message received during join: {message}")

            peer_socket.close()
            return True
        except Exception as e:
            self._notify_ui(f"Error joining network: {e}")
            return False

    def _send_heartbeat(self):
        while self.connected:
            with self.lock:
                peers_copy = self.peers.copy()

            for peer_username, peer_info in peers_copy.items():
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.settimeout(5)
                    peer_socket.connect((peer_info['address'], peer_info['port']))
                    send_message(peer_socket, {
                        'type': 'heartbeat',
                        'username': self.username
                    })
                    peer_socket.close()
                except Exception:
                    with self.lock:
                        if peer_username in self.peers:
                            del self.peers[peer_username]
                    self._notify_ui(f"{peer_username} appears to be offline.")

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
            pass
        finally:
            self.server_socket.close()

def send_message(sock: socket.socket, message: dict):
    try:
        sock.sendall(json.dumps(message).encode())
    except Exception as e:
        print(f"Error sending message: {e}")