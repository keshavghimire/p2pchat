# chat.py
import tkinter as tk
from tkinter import Tk, Label, Entry, Button, Text, Frame, Scrollbar, PhotoImage, messagebox
import threading
from p2p_chat import P2PChat

class ChatUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Chat")
        self.root.geometry("360x640")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.chat_instance = None
        self.username = ""
        self.chat_display = None
        self.setup_welcome_screen()

    def setup_welcome_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        welcome_label = tk.Label(self.root, text="Welcome to P2P Chat", font=("Helvetica", 24, 'bold'), pady=20)
        welcome_label.pack()

        intro_text = tk.Label(
            self.root, 
            text="Connect directly with friends using peer-to-peer technology. No servers, no tracking, just private communication.", 
            font=("Helvetica", 12), 
            wraplength=300, 
            justify="center"
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

        username_label = tk.Label(self.root, text="Please enter your username:", font=("Helvetica", 14))
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
            command=self.on_create_chat
        )
        create_button.pack(pady=10, ipady=5, ipadx=10)

        join_button = tk.Button(
            button_frame, 
            text="  Join Chat  ", 
            font=("Helvetica", 14), 
            bg="white", 
            fg="#2196F3", 
            relief="flat", 
            command=self.show_join_screen
        )
        join_button.pack(pady=10, ipady=5, ipadx=10)
        join_button.config(highlightthickness=2, highlightbackground="#2196F3", highlightcolor="#2196F3")

    def on_create_chat(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
        
        self.username = username
        self.setup_chat_screen()
        self.chat_instance = P2PChat(username, ui_callback=self.update_chat_display)
        self.update_chat_display(f"You are connected as {self.username}.")
        self.update_chat_display(f"Your chat is running on port {self.chat_instance.port}.")

    def show_join_screen(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
        
        self.username = username
        for widget in self.root.winfo_children():
            widget.destroy()

        join_label = tk.Label(self.root, text="Join Existing Chat", font=("Helvetica", 20, 'bold'), pady=20)
        join_label.pack()

        host_label = tk.Label(self.root, text="Host address:", font=("Helvetica", 14))
        host_label.pack(pady=5)

        self.host_entry = tk.Entry(self.root, font=("Helvetica", 14))
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(pady=5)

        port_label = tk.Label(self.root, text="Port:", font=("Helvetica", 14))
        port_label.pack(pady=5)

        self.port_entry = tk.Entry(self.root, font=("Helvetica", 14))
        self.port_entry.pack(pady=5)

        button_frame = Frame(self.root)
        button_frame.pack(pady=20)

        join_button = tk.Button(
            button_frame, 
            text="Connect", 
            font=("Helvetica", 14), 
            bg="#2196F3", 
            fg="white", 
            relief="flat", 
            command=self.on_join_chat
        )
        join_button.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)

        back_button = tk.Button(
            button_frame, 
            text="Back", 
            font=("Helvetica", 14), 
            bg="white", 
            fg="#2196F3", 
            relief="flat", 
            command=self.setup_welcome_screen
        )
        back_button.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        back_button.config(highlightthickness=2, highlightbackground="#2196F3", highlightcolor="#2196F3")

    def on_join_chat(self):
        try:
            host = self.host_entry.get().strip()
            port = int(self.port_entry.get().strip())
            self.setup_chat_screen()
            self.chat_instance = P2PChat(self.username, ui_callback=self.update_chat_display)
            success = self.chat_instance.join_network(host, port)
            if success:
                self.update_chat_display(f"You are connected as {self.username}.")
                self.update_chat_display(f"Your chat is running on port {self.chat_instance.port}.")
                self.update_chat_display(f"Successfully connected to {host}:{port}")
            else:
                messagebox.showerror("Error", f"Failed to connect to {host}:{port}")
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to join chat: {e}")

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
            pady=10
        )
        username_label.pack(side=tk.LEFT, padx=10)

        peers_button = Button(
            header_frame, 
            text="Peers", 
            font=("Helvetica", 12), 
            bg="#0d47a1", 
            fg="white", 
            relief="flat", 
            command=self.show_peers
        )
        peers_button.pack(side=tk.RIGHT, padx=10, pady=5)

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
            command=self.send_message
        )
        send_button.pack(side=tk.RIGHT, padx=10)

    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        if message:
            if message.lower() == '/quit':
                self.on_closing()
                return
            
            self.update_chat_display(f"{self.username}: {message}")
            if self.chat_instance:
                self.chat_instance.broadcast_message(message)
            self.message_entry.delete(0, tk.END)

    def update_chat_display(self, message):
        if not hasattr(self, 'chat_display') or self.chat_display is None:
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
                    self.chat_display.tag_configure("center", justify="center", foreground="gray", font=("Helvetica", 10))
                    self.chat_display.insert(tk.END, f"{content}\n\n", "center")
                elif username == self.username:
                    # Right-align your messages
                    self.chat_display.tag_configure("right", justify="right", foreground="blue", font=("Helvetica", 12))
                    self.chat_display.insert(tk.END, f"{username}:\n", "right")
                    self.chat_display.insert(tk.END, f"{content}\n\n", "right")
                else:
                    # Left-align others' messages
                    self.chat_display.tag_configure("left", justify="left", foreground="green", font=("Helvetica", 12))
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
        if not self.chat_instance:
            return

        peers_str = "Connected Peers:\n"
        with self.chat_instance.lock:
            if not self.chat_instance.peers:
                peers_str += "No peers connected."
            else:
                for peer, info in self.chat_instance.peers.items():
                    peers_str += f"- {peer} ({info['address']}:{info['port']})\n"

        messagebox.showinfo("Peers", peers_str)

    def on_closing(self):
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