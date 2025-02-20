import json
import time
from utils import send_message

def handle_message(chat, client_socket, address):
    try:
        while chat.connected:
            data = client_socket.recv(4096)
            if not data:
                break

            message = json.loads(data.decode())
            message_type = message.get('type')
            sender = message.get('username')

            if message_type == 'join':
                with chat.lock:
                    chat.peers[sender] = {'address': address[0], 'port': message['port']}
                send_message(client_socket, {'type': 'welcome', 'username': chat.username, 'port': chat.port})
                print(f"\n{sender} joined the chat!")

            elif message_type == 'chat':
                print(f"\n{sender}: {message['content']}")

            elif message_type == 'heartbeat':
                with chat.lock:
                    if sender in chat.peers:
                        chat.peers[sender]['last_seen'] = time.time()

            elif message_type == 'leave':
                with chat.lock:
                    chat.peers.pop(sender, None)
                print(f"\n{sender} left the chat.")

    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        client_socket.close()
