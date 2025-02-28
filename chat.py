# chat.py
import os
import sys
import base64
import socket
import json
import tkinter as tk
from tkinter import (
    Tk,
    Label,
    Entry,
    Button,
    Text,
    Frame,
    Scrollbar,
    PhotoImage,
    messagebox,
    Radiobutton,
    StringVar,
    Toplevel,
)
import threading
from tkinter import filedialog
from p2p_chat import P2PChat
import file_transfer
from utils import send_message
from presence_client import PresenceClient


class ChatUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Chat")
        self.root.geometry("360x640")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.chat_instance = None
        self.username = ""
        self.chat_display = None
        self.peer_status = {}  # Track peer status
        self.setup_welcome_screen()
        self.file_transfer = file_transfer.FileTransfer(
            message_sender=self._send_message_to_peer,
            downloads_folder="downloads",
            ui_callback=self.update_chat_display,  # Pass UI callback
        )
        self.presence_client = None

    def _send_message_to_peer(self, peer_addr, message: dict):
        """
        Given a peer address (host, port) and a message dict,
        connect, send the JSON, then close the socket.
        """
        host, port = peer_addr
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            # Use improved send_message function from utils
            send_message(sock, message)
            sock.close()
            print(f"Sent chunk of size {len(message.get('data', ''))} to {peer_addr}")
        except Exception as e:
            print(f"Error in _send_message_to_peer({peer_addr}): {e}")

    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            filename = os.path.basename(file_path)
            self.update_chat_display(f"System: Sending file '{filename}' ...")
            # Option 1: Broadcast file to every known peer
            if self.chat_instance and self.chat_instance.peers:
                for peer_username, peer_info in self.chat_instance.peers.items():
                    target_addr = (peer_info["address"], peer_info["port"])
                    self.file_transfer.send_file(file_path, target_addr=target_addr)
                    self.update_chat_display(
                        f"System: File '{filename}' sent to {peer_username}"
                    )
            else:
                self.update_chat_display("System: No peers to send the file to.")

    def setup_welcome_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        welcome_label = tk.Label(
            self.root,
            text="Welcome to P2P Chat",
            font=("Helvetica", 24, "bold"),
            pady=20,
        )
        welcome_label.pack()

        intro_text = tk.Label(
            self.root,
            text="Connect directly with friends using peer-to-peer technology. No servers, no tracking, just private communication.",
            font=("Helvetica", 12),
            wraplength=300,
            justify="center",
        )
        intro_text.pack(pady=10)

        try:
            image = PhotoImage(file="chat.png")
            image = image.subsample(4, 4)
            image_label = Label(self.root, image=image)
            image_label.image = image
            image_label.pack(pady=20)
        except Exception as e:
            print(f"Could not load image: {e}")
            placeholder = Label(self.root, text="[Chat Icon]", font=("Helvetica", 18))
            placeholder.pack(pady=20)

        username_label = tk.Label(
            self.root, text="Please enter your username:", font=("Helvetica", 14)
        )
        username_label.pack(pady=10)

        self.username_entry = tk.Entry(self.root, font=("Helvetica", 14))
        self.username_entry.pack(pady=10)

        button_frame = Frame(self.root)
        button_frame.pack(pady=20)

        create_button = tk.Button(
            button_frame,
            text="Create Chat",
            font=("Helvetica", 14),
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=self.on_create_chat,
        )
        create_button.pack(pady=10, ipady=5, ipadx=10)

        join_button = tk.Button(
            button_frame,
            text="  Join Chat  ",
            font=("Helvetica", 14),
            bg="white",
            fg="#2196F3",
            relief="flat",
            command=self.show_join_screen,
        )
        join_button.pack(pady=10, ipady=5, ipadx=10)
        join_button.config(
            highlightthickness=2,
            highlightbackground="#2196F3",
            highlightcolor="#2196F3",
        )

    def on_create_chat(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return

        self.username = username
        self.setup_chat_screen()
        # Make sure to pass the file_chunk_callback when creating the chat too
        self.chat_instance = P2PChat(
            username,
            ui_callback=self.update_chat_display,
            file_chunk_callback=self.file_transfer.handle_incoming_file_chunk,
            status_callback=self.update_peer_status,
        )
        self.update_chat_display(f"You are connected as {self.username}.")
        self.update_chat_display(
            f"Your chat is running on port {self.chat_instance.port}."
        )

    def show_join_screen(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return

        self.username = username
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create a container frame for the join options
        join_container = Frame(self.root)
        join_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Add a label
        join_label = Label(
            join_container,
            text="How would you like to connect?",
            font=("Helvetica", 20, "bold"),
        )
        join_label.pack(pady=20)

        # Create a connection method chooser
        connection_method = StringVar()
        connection_method.set("direct")  # Default to direct connection

        # Direct Connection option
        direct_frame = Frame(join_container, relief=tk.RIDGE, borderwidth=2)
        direct_frame.pack(fill=tk.X, pady=10, ipady=10)

        direct_radio = Radiobutton(
            direct_frame,
            text="Direct Connection",
            variable=connection_method,
            value="direct",
            font=("Helvetica", 14),
        )
        direct_radio.pack(anchor=tk.W, padx=10, pady=(10, 5))

        direct_desc = Label(
            direct_frame,
            text="Connect directly to a peer by entering their IP and port.",
            font=("Helvetica", 10),
            wraplength=300,
            justify=tk.LEFT,
        )
        direct_desc.pack(anchor=tk.W, padx=30, pady=(0, 10))

        # Presence Connection option
        presence_frame = Frame(join_container, relief=tk.RIDGE, borderwidth=2)
        presence_frame.pack(fill=tk.X, pady=10, ipady=10)

        presence_radio = Radiobutton(
            presence_frame,
            text="Find Online Users",
            variable=connection_method,
            value="presence",
            font=("Helvetica", 14),
        )
        presence_radio.pack(anchor=tk.W, padx=10, pady=(10, 5))

        presence_desc = Label(
            presence_frame,
            text="See who's online and connect to them.",
            font=("Helvetica", 10),
            wraplength=300,
            justify=tk.LEFT,
        )
        presence_desc.pack(anchor=tk.W, padx=30, pady=(0, 10))

        # Button to proceed based on selection
        next_btn = Button(
            join_container,
            text="Next",
            font=("Helvetica", 14),
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=lambda: self._show_connection_screen(connection_method.get()),
        )
        next_btn.pack(pady=20, ipady=5, ipadx=20)

        # Back button
        back_button = Button(
            join_container,
            text="Back",
            font=("Helvetica", 14),
            bg="white",
            fg="#2196F3",
            relief="flat",
            command=self.setup_welcome_screen,
        )
        back_button.pack(pady=10, ipady=5, ipadx=10)
        back_button.config(
            highlightthickness=2,
            highlightbackground="#2196F3",
            highlightcolor="#2196F3",
        )

    def _show_connection_screen(self, connection_method):
        """Show appropriate connection screen based on selected method"""
        if connection_method == "direct":
            self._show_direct_connection_screen()
        else:  # presence
            self._show_presence_connection_screen()

    def _show_direct_connection_screen(self):
        """Show the direct connection UI (original join screen)"""
        for widget in self.root.winfo_children():
            widget.destroy()

        join_label = Label(
            self.root,
            text="Direct Connection",
            font=("Helvetica", 20, "bold"),
            pady=20,
        )
        join_label.pack()

        host_label = Label(self.root, text="Host address:", font=("Helvetica", 14))
        host_label.pack(pady=5)

        self.host_entry = Entry(self.root, font=("Helvetica", 14))
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(pady=5)

        port_label = Label(self.root, text="Port:", font=("Helvetica", 14))
        port_label.pack(pady=5)

        self.port_entry = Entry(self.root, font=("Helvetica", 14))
        self.port_entry.pack(pady=5)

        button_frame = Frame(self.root)
        button_frame.pack(pady=20)

        join_button = Button(
            button_frame,
            text="Connect",
            font=("Helvetica", 14),
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=self.on_join_chat,
        )
        join_button.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)

        back_button = Button(
            button_frame,
            text="Back",
            font=("Helvetica", 14),
            bg="white",
            fg="#2196F3",
            relief="flat",
            command=self.show_join_screen,  # Go back to connection method selection
        )
        back_button.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        back_button.config(
            highlightthickness=2,
            highlightbackground="#2196F3",
            highlightcolor="#2196F3",
        )

    def _show_presence_connection_screen(self):
        """Show the presence-based connection UI"""
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create and set up the chat instance first
        self.setup_chat_screen()
        self.chat_instance = P2PChat(
            self.username,
            ui_callback=self.update_chat_display,
            file_chunk_callback=self.file_transfer.handle_incoming_file_chunk,
            status_callback=self.update_peer_status,
        )

        # Initialize presence client
        self.presence_client = PresenceClient(self.username, self.chat_instance.port)

        # Try to register with presence server
        if not self.presence_client.register():
            messagebox.showerror(
                "Error",
                "Could not connect to presence server. Please try direct connection.",
            )
            self.show_join_screen()
            return

        # Show the online users dialog
        self.show_online_users_dialog()

    def show_online_users_dialog(self):
        """Show a dialog with online users from the presence server"""
        # If dialog already exists, destroy it first
        if hasattr(self, "online_users_dialog") and self.online_users_dialog:
            self.online_users_dialog.destroy()

        # Create dialog
        self.online_users_dialog = Toplevel(self.root)
        self.online_users_dialog.title("Online Users")
        self.online_users_dialog.geometry("300x400")
        self.online_users_dialog.transient(
            self.root
        )  # Make it appear on top of main window

        # Title
        title_label = Label(
            self.online_users_dialog,
            text="Find Online Users",
            font=("Helvetica", 16, "bold"),
            pady=10,
        )
        title_label.pack()

        # Instructions
        instructions = Label(
            self.online_users_dialog,
            text="Select a user to chat with:",
            font=("Helvetica", 12),
            wraplength=280,
        )
        instructions.pack(pady=(0, 10))

        # Create a frame for the user list
        list_frame = Frame(self.online_users_dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a scrollable canvas to hold the users
        canvas = tk.Canvas(list_frame)
        scrollbar = Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Fetch online users
        online_users = self.presence_client.get_online_users()

        if not online_users:
            no_users_label = Label(
                scrollable_frame,
                text="No online users found",
                font=("Helvetica", 12),
                fg="gray",
                pady=20,
            )
            no_users_label.pack()
        else:
            # Display each user with a connect button
            for user in online_users:
                user_frame = Frame(scrollable_frame, borderwidth=1, relief="groove")
                user_frame.pack(fill=tk.X, pady=5, padx=3)

                username = user.get("username", "Unknown")
                address = user.get("address", "Unknown")
                port = user.get("port", "Unknown")

                # Username label
                user_label = Label(
                    user_frame, text=username, font=("Helvetica", 12, "bold")
                )
                user_label.pack(anchor=tk.W, padx=10, pady=(5, 0))

                # Address and port
                addr_label = Label(
                    user_frame,
                    text=f"{address}:{port}",
                    font=("Helvetica", 10),
                    fg="gray",
                )
                addr_label.pack(anchor=tk.W, padx=10, pady=(0, 5))

                # Connect button
                connect_btn = Button(
                    user_frame,
                    text="Connect",
                    bg="#4CAF50",
                    fg="white",
                    command=lambda a=address, p=port: self.connect_to_presence_user(
                        a, p
                    ),
                )
                connect_btn.pack(anchor=tk.E, padx=10, pady=5)

        # Button frame at bottom
        button_frame = Frame(self.online_users_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Refresh button
        refresh_btn = Button(
            button_frame,
            text="Refresh",
            bg="#2196F3",
            fg="white",
            command=self.show_online_users_dialog,  # Just reopen to refresh
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Cancel button
        cancel_btn = Button(
            button_frame,
            text="Cancel",
            command=lambda: self.online_users_dialog.destroy(),
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)

    def connect_to_presence_user(self, address, port):
        """Connect to a user selected from the online users list"""
        # Close the dialog
        if hasattr(self, "online_users_dialog") and self.online_users_dialog:
            self.online_users_dialog.destroy()

        # Connect to the selected user
        try:
            success = self.chat_instance.join_network(address, port)
            if success:
                self.update_chat_display(f"You are connected as {self.username}.")
                self.update_chat_display(
                    f"Your chat is running on port {self.chat_instance.port}."
                )
                self.update_chat_display(f"Successfully connected to {address}:{port}")
            else:
                messagebox.showerror("Error", f"Failed to connect to {address}:{port}")
                # Show the online users dialog again
                self.show_online_users_dialog()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to join chat: {e}")
            self.show_online_users_dialog()

    def on_join_chat(self):
        try:
            host = self.host_entry.get().strip()
            port = int(self.port_entry.get().strip())
            self.setup_chat_screen()
            self.chat_instance = P2PChat(
                self.username,
                ui_callback=self.update_chat_display,
                file_chunk_callback=self.file_transfer.handle_incoming_file_chunk,
                status_callback=self.update_peer_status,
            )
            success = self.chat_instance.join_network(host, port)
            if success:
                self.update_chat_display(f"You are connected as {self.username}.")
                self.update_chat_display(
                    f"Your chat is running on port {self.chat_instance.port}."
                )
                self.update_chat_display(f"Successfully connected to {host}:{port}")
            else:
                messagebox.showerror("Error", f"Failed to connect to {host}:{port}")
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to join chat: {e}")

    def update_peer_status(self, peer_username, status):
        """Called when a peer's status changes"""
        old_status = self.peer_status.get(peer_username, "unknown")
        self.peer_status[peer_username] = status

        # Only notify about status changes, not initial status
        if old_status != "unknown" and old_status != status:
            if status == "online":
                self.update_chat_display(f"System: {peer_username} is now online")
            else:
                self.update_chat_display(f"System: {peer_username} is now offline")

        # Update the UI if the peers dialog is open
        if hasattr(self, "peers_window") and self.peers_window:
            self.show_peers()

    def setup_chat_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        header_frame = Frame(self.root, bg="#2196F3")
        header_frame.pack(fill=tk.X)

        username_label = Label(
            header_frame,
            text=f"Username: {self.username}",
            font=("Helvetica", 12),
            bg="#2196F3",
            fg="white",
            pady=10,
        )
        username_label.pack(side=tk.LEFT, padx=10)

        peers_button = Button(
            header_frame,
            text="Peers",
            font=("Helvetica", 12),
            bg="#0d47a1",
            fg="white",
            relief="flat",
            command=self.show_peers,
        )
        peers_button.pack(side=tk.RIGHT, padx=10, pady=5)

        # Add a status indicator in the header
        status_label = Label(
            header_frame,
            text="Online",
            font=("Helvetica", 10),
            bg="#4CAF50",  # Green for online
            fg="white",
            padx=8,
            pady=2,
            borderwidth=0,
        )
        status_label.pack(side=tk.RIGHT, padx=10, pady=8)
        self.status_indicator = status_label

        chat_frame = Frame(self.root)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_display = Text(chat_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = Scrollbar(chat_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_display.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.chat_display.yview)

        input_frame = Frame(self.root)
        input_frame.pack(fill=tk.X, pady=10)

        self.message_entry = Entry(input_frame, font=("Helvetica", 12))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.message_entry.bind("<Return>", self.send_message)

        send_button = Button(
            input_frame,
            text="Send",
            font=("Helvetica", 12),
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=self.send_message,
        )
        send_button.pack(side=tk.LEFT, padx=10)

        send_file_button = Button(
            input_frame,
            text="Send File",
            font=("Helvetica", 12),
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=self.select_file,  # Calls the new method below
        )
        send_file_button.pack(side=tk.RIGHT, padx=5)

    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        if message:
            if message.lower() == "/quit":
                self.on_closing()
                return

            self.update_chat_display(f"{self.username}: {message}")
            if self.chat_instance:
                self.chat_instance.broadcast_message(message)
            self.message_entry.delete(0, tk.END)

    # def select_file(self):
    #     # Placeholder method to select a file from the local system
    #     file_path = filedialog.askopenfilename()
    #     if file_path:
    #         print(f"Selected file: {file_path}")

    def update_chat_display(self, message):
        if not hasattr(self, "chat_display") or self.chat_display is None:
            print(f"Can't display message yet: {message}")
            return

        def _update():
            try:
                self.chat_display.config(state=tk.NORMAL)

                # Split the message into username and content
                if ": " in message:
                    username, content = message.split(": ", 1)
                else:
                    username, content = "System", message

                # Determine alignment and styling based on the username
                if username == "System":
                    # Center-align system messages and use 80% of the screen width
                    self.chat_display.tag_configure(
                        "center",
                        justify="center",
                        foreground="gray",
                        font=("Helvetica", 10),
                    )
                    self.chat_display.insert(tk.END, f"{content}\n\n", "center")
                elif username == self.username:
                    # Right-align your messages
                    self.chat_display.tag_configure(
                        "right",
                        justify="right",
                        foreground="blue",
                        font=("Helvetica", 12),
                    )
                    self.chat_display.insert(tk.END, f"{username}:\n", "right")
                    self.chat_display.insert(tk.END, f"{content}\n\n", "right")
                else:
                    # Left-align others' messages
                    self.chat_display.tag_configure(
                        "left",
                        justify="left",
                        foreground="green",
                        font=("Helvetica", 12),
                    )
                    self.chat_display.insert(tk.END, f"{username}:\n", "left")
                    self.chat_display.insert(tk.END, f"{content}\n\n", "left")

                self.chat_display.see(tk.END)  # Scroll to the end
                self.chat_display.config(state=tk.DISABLED)
            except tk.TclError as e:
                print(f"TclError in update_chat_display: {e}")

        # Ensure thread-safe UI updates
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, _update)
        else:
            _update()

    def show_peers(self):
        """Show a dialog with the list of peers and their status"""
        if not self.chat_instance:
            return

        # If the peers window is already open, close it and create a new one
        if hasattr(self, "peers_window") and self.peers_window:
            self.peers_window.destroy()

        # Create a new Toplevel window for the peers list
        self.peers_window = tk.Toplevel(self.root)
        self.peers_window.title("Connected Peers")
        self.peers_window.geometry("300x400")

        # Create a Label for the title
        title_label = Label(
            self.peers_window,
            text="Connected Peers",
            font=("Helvetica", 16, "bold"),
            pady=10,
        )
        title_label.pack()

        # Create a Frame to hold the peer list
        peers_frame = Frame(self.peers_window)
        peers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a scrollable canvas to hold the peers
        canvas = tk.Canvas(peers_frame)
        scrollbar = Scrollbar(peers_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add peer entries
        with self.chat_instance.lock:
            peers_list = list(self.chat_instance.peers.items())

        if not peers_list:
            no_peers_label = Label(
                scrollable_frame, text="No peers connected", font=("Helvetica", 12)
            )
            no_peers_label.pack(pady=10)
        else:
            # Sort peers by status (online first) then by username
            peers_list.sort(
                key=lambda x: (x[1].get("status", "offline") != "online", x[0].lower())
            )

            for peer_username, peer_info in peers_list:
                peer_frame = Frame(scrollable_frame, borderwidth=1, relief="groove")
                peer_frame.pack(fill=tk.X, pady=5, padx=3)

                # Status indicator (colored circle)
                status = peer_info.get("status", "offline")
                status_color = (
                    "#4CAF50" if status == "online" else "#F44336"
                )  # Green if online, red if offline

                status_indicator = Frame(
                    peer_frame, bg=status_color, width=10, height=10
                )
                status_indicator.pack(side=tk.LEFT, padx=10, pady=10)

                # Username and address
                peer_label = Label(
                    peer_frame,
                    text=f"{peer_username}",
                    font=("Helvetica", 12, "bold"),
                )
                peer_label.pack(side=tk.LEFT, padx=5, pady=5)

                address_label = Label(
                    peer_frame,
                    text=f"({peer_info['address']}:{peer_info['port']})",
                    font=("Helvetica", 10),
                    fg="gray",
                )
                address_label.pack(side=tk.LEFT, padx=5, pady=5)

                # Status text
                status_text = "Online" if status == "online" else "Offline"
                status_label = Label(
                    peer_frame,
                    text=status_text,
                    font=("Helvetica", 10),
                    fg=status_color,
                )
                status_label.pack(side=tk.RIGHT, padx=10, pady=5)

        # Add a close button at the bottom
        close_button = Button(
            self.peers_window,
            text="Close",
            font=("Helvetica", 12),
            bg="#2196F3",
            fg="white",
            command=lambda: self.peers_window.destroy(),
        )
        close_button.pack(pady=10)

    def on_closing(self):
        # Unregister from presence server if registered
        if (
            self.presence_client
            and hasattr(self.presence_client, "registered")
            and self.presence_client.registered
        ):
            self.presence_client.unregister()

        # Existing cleanup code
        if self.chat_instance:
            try:
                self.chat_instance.disconnect()
            except Exception:
                pass

        self.root.destroy()
        sys.exit(0)


def main():
    root = tk.Tk()
    app = ChatUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
