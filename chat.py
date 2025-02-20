import sys
from p2p_chat import P2PChat

def main():
    if len(sys.argv) < 2:
        print("Usage: python chat.py <username> [known_host known_port]")
        return

    username = sys.argv[1]
    chat = P2PChat(username)

    print(f"P2P Chat started on port {chat.port}")
    print(f"Your username: {username}")

    if len(sys.argv) == 4:
        known_host = sys.argv[2]
        known_port = int(sys.argv[3])
        chat.join_network(known_host, known_port)

    try:
        while True:
            message = input("")
            if message.lower() == '/quit':
                break
            elif message.lower() == '/peers':
                print("\nConnected peers:")
                for peer, info in chat.peers.items():
                    print(f"- {peer} ({info['address']}:{info['port']})")
            elif message:
                chat.broadcast_message(message)
    except KeyboardInterrupt:
        pass
    finally:
        chat.disconnect()
        print("\nDisconnected from the network.")

if __name__ == "__main__":
    main()
