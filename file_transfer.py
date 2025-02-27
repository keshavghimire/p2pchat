import os
import uuid
import base64

CHUNK_SIZE = 8192  # 8KB, adjust as needed


class FileTransfer:
    def __init__(self, message_sender, downloads_folder="downloads"):
        """
        :param message_sender: a callable or function reference that can send a dict message to a peer
                               e.g., send_message(peer_addr, message)
        :param downloads_folder: location for saving received files
        """
        self.message_sender = message_sender
        self.downloads_folder = downloads_folder
        os.makedirs(self.downloads_folder, exist_ok=True)

        # Storing incoming files: transfer_id -> {"filename": str, "data": bytearray()}
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

        Expected message fields:
            - "type": "file_chunk"
            - "transfer_id": str
            - "filename": str
            - "data": bytes
            - "is_last": bool
        """
        transfer_id = message.get("transfer_id")
        filename = message.get("filename")
        data_chunk = message.get("data", "")
        # data_chunk = (
        #     bytes.fromhex(message.get("data", ""))
        #     if isinstance(message.get("data"), str)
        #     else message.get("data", b"")
        # )
        encoded_data = message.get("data", "")
        is_last = message.get("is_last", False)

        if not transfer_id or not filename:
            print("[FileTransfer] Invalid file chunk message")
            return

        # Decode from base64 if it's a string
        if isinstance(data_chunk, str) and data_chunk:
            data_chunk = base64.b64decode(data_chunk)

        # # Decode Base64 data into raw bytes
        # chunk = base64.b64decode(encoded_data)

        # If starting a new transfer, initialize
        if transfer_id not in self.incoming_transfers:
            self.incoming_transfers[transfer_id] = {
                "filename": filename,
                "data": bytearray(),
            }

        self.incoming_transfers[transfer_id]["data"].extend(data_chunk)

        if is_last:
            # Write the file to disk
            file_data = self.incoming_transfers[transfer_id]["data"]
            save_path = os.path.join(self.downloads_folder, filename)

            with open(save_path, "wb") as f:
                f.write(file_data)

            # Clean up
            del self.incoming_transfers[transfer_id]
            print(f"[FileTransfer] File '{filename}' saved to {save_path}")

    def _send_chunk(
        self, transfer_id, filename, chunk, is_last_chunk, target_addr=None
    ):
        """
        Create a file chunk message and send it via message_sender.
        """
        # Encode binary data as base64 string
        if isinstance(chunk, bytes):
            chunk = base64.b64encode(chunk).decode("ascii")
        # Base64-encode the binary chunk
        # encoded_chunk = base64.b64encode(chunk).decode("ascii")

        message = {
            "type": "file_chunk",
            "transfer_id": transfer_id,
            "filename": filename,
            "data": chunk,
            # "data": (
            #     chunk.hex() if isinstance(chunk, bytes) else chunk
            # ),  # Convert bytes to hex string,
            "is_last": is_last_chunk,
        }

        # If target_addr is specified, send directly. Otherwise, your logic could broadcast.
        if target_addr:
            self.message_sender(target_addr, message)
        else:
            # Example broadcast loop; adapt as needed for your peer list
            # for peer, info in self.peers.items():
            #     self.message_sender(info["addr"], message)
            pass
