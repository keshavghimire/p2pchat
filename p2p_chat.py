import socket
import threading
import json
import time
import random
from typing import Dict
from utils import send_message
from message_handler import handle_message

class P2PChat:
    def __init__(self, username: str, host: str = '0.0.0.0', port: int = None):
        self.username = username
        self.host = host
        self.port = port or random.randint(49152, 65535)
        self.peers: Dict[str, dict] = {}
        self.connected = True
        self.lock = threading.Lock()
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        self.server_thread = threading.Thread(target=self._listen_for_connections)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def _listen_for_connections(self):
        while self.connected:
            try:
                client_socket, address = self.server_socket.accept()
                client_handler = threading.Thread(
                    target=handle_message,
                    args=(self, client_socket, address)
                )
                client_handler.daemon = True
                client_handler.start()
            except Exception as e:
                if self.connected:
                    print(f"Error accepting connection: {e}")

    def broadcast_message(self, message: str):
        msg_data = {'type': 'chat', 'username': self.username, 'content': message}
        with self.lock:
            peers_copy = self.peers.copy()
        for peer, info in peers_copy.items():
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((info['address'], info['port']))
                send_message(peer_socket, msg_data)
                peer_socket.close()
            except Exception:
                with self.lock:
                    self.peers.pop(peer, None)

    def join_network(self, known_host: str, known_port: int):
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((known_host, known_port))
            send_message(peer_socket, {'type': 'join', 'username': self.username, 'port': self.port})

            data = peer_socket.recv(4096)
            if data:
                message = json.loads(data.decode())
                if message['type'] == 'welcome':
                    with self.lock:
                        self.peers[message['username']] = {'address': known_host, 'port': message['port'], 'last_seen': time.time()}
                    print(f"Joined network through {message['username']}")
            peer_socket.close()
        except Exception as e:
            print(f"Error joining network: {e}")

    def _send_heartbeat(self):
        while self.connected:
            with self.lock:
                peers_copy = self.peers.copy()
            for peer, info in peers_copy.items():
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.connect((info['address'], info['port']))
                    send_message(peer_socket, {'type': 'heartbeat', 'username': self.username})
                    peer_socket.close()
                except Exception:
                    with self.lock:
                        self.peers.pop(peer, None)
                        print(f"\n{peer} appears to be offline.")
            time.sleep(10)

    def disconnect(self):
        self.connected = False
        with self.lock:
            peers_copy = self.peers.copy()
        for peer, info in peers_copy.items():
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((info['address'], info['port']))
                send_message(peer_socket, {'type': 'leave', 'username': self.username})
                peer_socket.close()
            except Exception:
                pass
        self.server_socket.close()

