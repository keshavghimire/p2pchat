# chat.py
import sys
from p2p_chat import P2PChat


def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <username> [known_host known_port]")
        return

    username = sys.argv[1]
    chat = P2PChat(username)

    # If known peer is provided, join through them
    if len(sys.argv) == 4:
        known_host = sys.argv[2]
        try:
            known_port = int(sys.argv[3])
            chat.join_network(known_host, known_port)
        except ValueError:
            print("Invalid port number. Port must be an integer.")
            sys.exit(1)  # Exit if port is invalid

    try:
        while True:
            message = input("")  # Empty prompt for cleaner UI
            if message.lower() == '/quit':
                break
            elif message.lower() == '/peers':
                print("\nConnected peers:")
                with chat.lock:
                    for peer, info in chat.peers.items():
                        print(f"- {peer} ({info['address']}:{info['port']})")
            elif message:
                chat.broadcast_message(message)
    except KeyboardInterrupt:
        print("\nExiting due to keyboard interrupt...")  # More informative
    finally:
        chat.disconnect()
        print("\nDisconnected from the network.")


if __name__ == "__main__":
    main()
