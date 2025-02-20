# utils.py
import socket
import json

def send_message(sock: socket.socket, message: dict):
    try:
        sock.send(json.dumps(message).encode())
    except Exception as e:
        print(f"Error sending message: {e}")
