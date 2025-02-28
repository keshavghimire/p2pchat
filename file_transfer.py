import os
import uuid
import base64
import socket
from utils import send_message  # Import from utils

CHUNK_SIZE = 8192  # 8KB, adjust as needed


class FileTransfer:
    def __init__(self, message_sender, downloads_folder="downloads", ui_callback=None):
        """
        :param message_sender: a callable or function reference that can send a dict message to a peer
                               e.g., send_message(peer_addr, message)
        :param downloads_folder: location for saving received files
        :param ui_callback: function to call for UI notifications
        """
        self.message_sender = message_sender
        self.downloads_folder = downloads_folder
        self.ui_callback = ui_callback
        os.makedirs(self.downloads_folder, exist_ok=True)

        # Storing incoming files: transfer_id -> {"filename": str, "data": bytearray(), "sender": str}
        self.incoming_transfers = {}

    def send_file(self, file_path, target_addr=None):
        """
        Reads a file from disk, breaks it into chunks, and sends each chunk
        as a separate message.
        :param file_path: local path to the file
        :param target_addr: address of the peer to send to (or None for broadcast)
        """
        if not os.path.isfile(file_path):
            print(f"[FileTransfer] File not found: {file_path}")
            return

        file_name = os.path.basename(file_path)
        transfer_id = str(uuid.uuid4())

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    # Send an empty chunk indicating final
                    self._send_chunk(transfer_id, file_name, b"", True, target_addr)
                    break
                self._send_chunk(transfer_id, file_name, chunk, False, target_addr)

    def handle_incoming_file_chunk(self, message):
        """
        Processes an incoming file chunk message. Saves completed files
        in self.downloads_folder.
        """
        try:
            transfer_id = message.get("transfer_id")
            filename = message.get("filename")
            encoded_data = message.get("data", "")
            is_last = message.get("is_last", False)
            sender = message.get("sender", "Unknown")  # Get sender's username

            if not transfer_id or not filename:
                print("[FileTransfer] Invalid file chunk message")
                return

            # Decode from base64 if it's a string
            data_chunk = base64.b64decode(encoded_data) if encoded_data else b""

            # If starting a new transfer, initialize and notify UI
            if transfer_id not in self.incoming_transfers:
                self.incoming_transfers[transfer_id] = {
                    "filename": filename,
                    "data": bytearray(),
                    "sender": sender,
                }

                # Notify UI when starting to receive a file
                if self.ui_callback:
                    self.ui_callback(f"Receiving file '{filename}' from {sender}...")

            # Add this chunk to the file data
            self.incoming_transfers[transfer_id]["data"].extend(data_chunk)

            if is_last:
                # Write the file to disk
                file_data = self.incoming_transfers[transfer_id]["data"]
                save_path = os.path.join(self.downloads_folder, filename)

                with open(save_path, "wb") as f:
                    f.write(file_data)

                # Notify UI that file is complete
                if self.ui_callback:
                    self.ui_callback(
                        f"File '{filename}' received from {sender} and saved to {save_path}"
                    )

                # Clean up
                del self.incoming_transfers[transfer_id]
                print(f"[FileTransfer] File '{filename}' saved to {save_path}")
        except Exception as e:
            print(f"[FileTransfer] Error handling file chunk: {e}")

    def _send_chunk(
        self, transfer_id, filename, chunk, is_last_chunk, target_addr=None
    ):
        """
        Create a file chunk message and send it via message_sender.
        """
        # Encode binary data as base64 string
        if isinstance(chunk, bytes):
            chunk = base64.b64encode(chunk).decode("ascii")

        message = {
            "type": "file_chunk",
            "transfer_id": transfer_id,
            "filename": filename,
            "data": chunk,
            "is_last": is_last_chunk,
            "sender": "You",  # This will be overridden in p2p_chat.py
        }

        # If target_addr is specified, send directly. Otherwise, your logic could broadcast.
        if target_addr:
            self.message_sender(target_addr, message)
        else:
            # Example broadcast loop; adapt as needed for your peer list
            # for peer, info in self.peers.items():
            #     self.message_sender(info["addr"], message)
            pass

    def _send_message_to_peer(self, peer_addr, message: dict):
        """
        Given a peer address (host, port) and a message dict,
        connect, send the JSON, then close the socket.
        """
        host, port = peer_addr
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            # Use the improved send_message function from utils.py
            send_message(sock, message)
            sock.close()
            print(f"Sent chunk of size {len(message.get('data', ''))} to {peer_addr}")
        except Exception as e:
            print(f"Error in _send_message_to_peer({peer_addr}): {e}")
