"""
File transfer functionality for P2P Chat.

This module handles sending and receiving files between peers by breaking
them into chunks that can be sent as messages.
"""

import os
import uuid
import base64
import socket
from utils import send_message

CHUNK_SIZE = 8192  # 8KB chunk size for file transfers


class FileTransfer:
    """
    Handles file transfer operations between peers.

    Features:
    - Break files into chunks for sending
    - Reassemble received chunks into complete files
    - Track file transfer progress
    - Notify UI about transfer status
    """

    def __init__(self, message_sender, downloads_folder="downloads", ui_callback=None):
        """
        Initialize the FileTransfer system.

        Args:
            message_sender: Function to send messages to peers
            downloads_folder: Directory to save received files
            ui_callback: Function to notify UI of transfer events
        """
        self.message_sender = message_sender
        self.downloads_folder = downloads_folder
        self.ui_callback = ui_callback
        # Create downloads directory if it doesn't exist
        os.makedirs(self.downloads_folder, exist_ok=True)

        # Dictionary to track incoming file transfers
        # transfer_id -> {"filename": str, "data": bytearray(), "sender": str}
        self.incoming_transfers = {}

    def send_file(self, file_path, target_addr=None):
        """
        Send a file to a peer by breaking it into chunks.

        Args:
            file_path: Path to the file to send
            target_addr: (host, port) of the recipient
        """
        if not os.path.isfile(file_path):
            print(f"[FileTransfer] File not found: {file_path}")
            return

        # Get just the filename (not full path)
        file_name = os.path.basename(file_path)
        # Generate a unique ID for this transfer
        transfer_id = str(uuid.uuid4())

        # Read and send file in chunks
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    # Send an empty chunk to indicate end of file
                    self._send_chunk(transfer_id, file_name, b"", True, target_addr)
                    break
                self._send_chunk(transfer_id, file_name, chunk, False, target_addr)

    def handle_incoming_file_chunk(self, message):
        """
        Process an incoming file chunk message and save completed files.

        Args:
            message: Dictionary containing file chunk data with fields:
                - type: "file_chunk"
                - transfer_id: Unique ID for this transfer
                - filename: Name of the file
                - data: Base64-encoded chunk data
                - is_last: Boolean indicating if this is the last chunk
                - sender: Username of sender
        """
        try:
            # Extract message fields
            transfer_id = message.get("transfer_id")
            filename = message.get("filename")
            encoded_data = message.get("data", "")
            is_last = message.get("is_last", False)
            sender = message.get("sender", "Unknown")  # Get sender's username

            # Validate required fields
            if not transfer_id or not filename:
                print("[FileTransfer] Invalid file chunk message")
                return

            # Decode from base64 if it's a string
            data_chunk = base64.b64decode(encoded_data) if encoded_data else b""

            # If this is the first chunk for this transfer, initialize entry
            if transfer_id not in self.incoming_transfers:
                self.incoming_transfers[transfer_id] = {
                    "filename": filename,
                    "data": bytearray(),
                    "sender": sender,
                }

                # Notify UI when starting to receive a file
                if self.ui_callback:
                    self.ui_callback(f"Receiving file '{filename}' from {sender}...")

            # Add this chunk to the accumulated file data
            self.incoming_transfers[transfer_id]["data"].extend(data_chunk)

            # If this is the last chunk, save the completed file
            if is_last:
                # Get the complete file data
                file_data = self.incoming_transfers[transfer_id]["data"]
                save_path = os.path.join(self.downloads_folder, filename)

                # Write to disk
                with open(save_path, "wb") as f:
                    f.write(file_data)

                # Notify UI that file is complete
                if self.ui_callback:
                    self.ui_callback(
                        f"File '{filename}' received from {sender} and saved to {save_path}"
                    )

                # Clean up the transfer
                del self.incoming_transfers[transfer_id]
                print(f"[FileTransfer] File '{filename}' saved to {save_path}")
        except Exception as e:
            print(f"[FileTransfer] Error handling file chunk: {e}")

    def _send_chunk(
        self, transfer_id, filename, chunk, is_last_chunk, target_addr=None
    ):
        """
        Create and send a file chunk message.

        Args:
            transfer_id: Unique ID for the transfer
            filename: Name of the file
            chunk: Binary data to send
            is_last_chunk: Boolean flag for the last chunk
            target_addr: (host, port) of recipient
        """
        # Encode binary data as base64 string
        if isinstance(chunk, bytes):
            chunk = base64.b64encode(chunk).decode("ascii")

        # Create the message
        message = {
            "type": "file_chunk",
            "transfer_id": transfer_id,
            "filename": filename,
            "data": chunk,
            "is_last": is_last_chunk,
            "sender": "You",  # This will be replaced by the receiver
        }

        # Send the message to the specified target
        if target_addr:
            self.message_sender(target_addr, message)
        else:
            # Example broadcast logic would go here
            pass

    def _send_message_to_peer(self, peer_addr, message: dict):
        """
        Send a message to a specific peer.

        Args:
            peer_addr: (host, port) tuple of the recipient
            message: Dictionary containing the message
        """
        host, port = peer_addr
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            # Use the improved send_message function
            send_message(sock, message)
            sock.close()
            print(f"Sent chunk of size {len(message.get('data', ''))} to {peer_addr}")
        except Exception as e:
            print(f"Error in _send_message_to_peer({peer_addr}): {e}")
