# peer_status_tracker.py

import time
from typing import Dict, Callable, Optional


class PeerStatusTracker:
    """
    Tracks the online/offline status of peers in the P2P network.
    """

    def __init__(self, status_change_callback: Optional[Callable] = None):
        # Dictionary to store peer status: username -> {"status": "online"|"offline", "last_updated": timestamp}
        self.peers: Dict[str, dict] = {}
        self.status_change_callback = status_change_callback

    def update_peer_status(self, username: str, status: str):
        """Update a peer's status and invoke callback if it changed"""
        current_time = time.time()

        # Check if this is a status change
        if username in self.peers:
            old_status = self.peers[username].get("status")
            if old_status != status:
                # Status changed, invoke callback
                if self.status_change_callback:
                    self.status_change_callback(username, status, old_status)
        else:
            # New peer
            if self.status_change_callback:
                self.status_change_callback(username, status, None)

        # Update the status
        self.peers[username] = {"status": status, "last_updated": current_time}

    def get_peer_status(self, username: str) -> str:
        """Get a peer's current status"""
        if username in self.peers:
            return self.peers[username].get("status", "unknown")
        return "unknown"

    def get_all_peers(self) -> Dict[str, str]:
        """Get all peers and their statuses"""
        return {username: info["status"] for username, info in self.peers.items()}

    def get_online_peers(self) -> Dict[str, dict]:
        """Get all online peers"""
        return {
            username: info
            for username, info in self.peers.items()
            if info.get("status") == "online"
        }

    def get_offline_peers(self) -> Dict[str, dict]:
        """Get all offline peers"""
        return {
            username: info
            for username, info in self.peers.items()
            if info.get("status") == "offline"
        }
