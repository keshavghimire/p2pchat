# message_handler.py
import time
import socket
import json
from utils import send_message


class MessageHandler:
    def __init__(self, chat):
        self.chat = chat

    def handle_message(self, client_socket: socket.socket, address: tuple, message: dict):
        message_type = message.get('type')
        sender = message.get('username')

        if message_type == 'join':
            self.handle_join(client_socket, address, message, sender)
        elif message_type == 'request_peers':
            self.handle_request_peers(client_socket)
        elif message_type == 'chat':
            print(f"\n{sender}: {message['content']}")  # Clearer display with newline
        elif message_type == 'heartbeat':
            self.handle_heartbeat(sender)
        elif message_type == 'leave':
            self.handle_leave(sender)
        elif message_type == 'new_peer':
            self.handle_new_peer(message)
        else:
            print(f"Unknown message type received from {sender}: {message_type}")

    def handle_join(self, client_socket: socket.socket, address: tuple, message: dict, sender: str):
        with self.chat.lock:
            self.chat.peers[sender] = {
                'address': address[0],
                'port': message['port'],
                'last_seen': time.time()  # Initialize last_seen
            }
        send_message(client_socket, {
            'type': 'welcome',
            'username': self.chat.username,
            'port': self.chat.port
        })
        print(f"\n{sender} joined the chat!")

        # Inform existing peers about the new peer
        self._broadcast_new_peer(sender, address[0], message['port'])

    def handle_request_peers(self, client_socket: socket.socket):
        # Send the list of known peers back to the new peer
        peers_list = [{'username': peer, 'address': info['address'], 'port': info['port']}
                      for peer, info in self.chat.peers.items()]
        send_message(client_socket, {
            'type': 'peer_list',
            'peers': peers_list
        })

    def handle_heartbeat(self, sender: str):
        with self.chat.lock:
            if sender in self.chat.peers:
                self.chat.peers[sender]['last_seen'] = time.time()

    def handle_leave(self, sender: str):
        with self.chat.lock:
            if sender in self.chat.peers:
                del self.chat.peers[sender]
        print(f"\n{sender} left the chat.")

    def handle_new_peer(self, message: dict):
        # Handle new peer information received from another peer
        new_peer_username = message['username']
        new_peer_address = message['address']
        new_peer_port = message['port']

        with self.chat.lock:
            if new_peer_username not in self.chat.peers:
                self.chat.peers[new_peer_username] = {
                    'address': new_peer_address,
                    'port': new_peer_port,
                    'last_seen': time.time()
                }
                print(f"\nDiscovered new peer: {new_peer_username} ({new_peer_address}:{new_peer_port})")

    def _broadcast_new_peer(self, new_peer_username: str, new_peer_address: str, new_peer_port: int):
        """Inform existing peers about a new peer that has joined."""
        msg_data = {
            'type': 'new_peer',
            'username': new_peer_username,
            'address': new_peer_address,
            'port': new_peer_port
        }

        with self.chat.lock:
            peers_copy = self.chat.peers.copy()

        for peer_username, peer_info in peers_copy.items():
            if peer_username != new_peer_username:  # Don't send to the new peer itself
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.connect((peer_info['address'], peer_info['port']))
                    send_message(peer_socket, msg_data)
                    peer_socket.close()
                except Exception as e:
                    print(f"Error sending new peer info to {peer_username}: {e}")
                    # Consider removing unreachable peer here, or let heartbeat handle it
