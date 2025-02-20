import json

def send_message(sock, message):
    try:
        sock.send(json.dumps(message).encode())
    except Exception as e:
        print(f"Error sending message: {e}")
