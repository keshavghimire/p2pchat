# utils.py
"""
Utility functions for network communication in the P2P chat application.
This module provides message framing to ensure complete messages are sent and received.
"""
import socket
import json
import struct


def send_message(sock: socket.socket, message: dict):
    """
    Send a message with proper length prefix for framing.

    This function handles the message framing protocol:
    1. Convert message dict to JSON
    2. Add a 4-byte length prefix
    3. Send the complete packet

    Args:
        sock: Socket connection to send message through
        message: Dictionary containing the message data
    """
    try:
        # Convert message to JSON string and encode to bytes
        data = json.dumps(message).encode()

        # Prefix with message length (4-byte integer in network byte order)
        length_prefix = struct.pack("!I", len(data))

        # Send length prefix followed by the data
        sock.sendall(length_prefix + data)
    except Exception as e:
        print(f"Error sending message: {e}")


def receive_message(sock: socket.socket) -> dict:
    """
    Receive a message with length prefix framing.

    This function handles the message framing protocol:
    1. Read the 4-byte length prefix
    2. Read the specified number of bytes
    3. Parse the JSON message

    Args:
        sock: Socket connection to receive message from

    Returns:
        Parsed message dictionary or None if an error occurred
    """
    try:
        # Set a timeout to prevent hanging forever
        sock.settimeout(10.0)  # 10 seconds timeout

        # First read the 4-byte length prefix
        length_bytes = sock.recv(4)
        if not length_bytes:
            # This is a normal disconnection, no need to print anything
            return None

        if len(length_bytes) < 4:
            # Only print for incomplete prefixes, not empty ones
            if len(length_bytes) > 0:
                print(f"Incomplete length prefix received ({len(length_bytes)} bytes)")
            return None

        # Unpack the length prefix to get the message size
        message_length = struct.unpack("!I", length_bytes)[0]

        # Sanity check to avoid allocating too much memory
        if message_length > 100 * 1024 * 1024:  # 100MB limit
            print(f"Message too large: {message_length} bytes")
            return None

        # Read the message data in chunks to handle large messages
        chunks = []
        bytes_received = 0
        while bytes_received < message_length:
            chunk = sock.recv(min(message_length - bytes_received, 4096))
            if not chunk:
                print("Connection closed while receiving message data")
                return None  # Connection closed unexpectedly
            chunks.append(chunk)
            bytes_received += len(chunk)

        # Combine all chunks and decode JSON
        data = b"".join(chunks)
        return json.loads(data.decode())
    except socket.timeout:
        # Socket timeouts are normal during polling, don't print
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except Exception as e:
        # Only log actual errors
        print(f"Error receiving message: {e}")
        return None
    finally:
        # Reset timeout to blocking mode
        try:
            sock.settimeout(None)
        except:
            pass  # Socket might be closed already
