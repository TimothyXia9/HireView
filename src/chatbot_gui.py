import asyncio
import httpx
import json
import requests
import threading
import time
import uuid
import yaml
import tkinter as tk
from tkinter import scrolledtext


class Chatbot:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)

        self.api_key = config["api_key"]
        self.base_url = config["model_server_base_url"]
        self.stream = config["stream"]
        self.stream_timeout = config["stream_timeout"]
        self.workspace_slug = config["workspace_slug"]
        self.session_id = str(uuid.uuid4())  # unique session
        self.stop_event = threading.Event()

        if self.stream:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/stream-chat"
        else:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/chat"

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key,
        }

    def build_payload(self, message: str) -> dict:
        return {
            "message": message,
            "mode": "chat",
            "sessionId": self.session_id,
            "attachments": [],
        }

    def send_message(self, message: str) -> str:
        """Blocking: send message and return response text"""
        data = self.build_payload(message)
        chat_response = requests.post(self.chat_url, headers=self.headers, json=data)
        try:
            response_json = chat_response.json()
            return response_json.get("textResponse", "Unexpected response format")
        except Exception as e:
            return f"Error parsing response: {e}"

    async def send_message_stream(self, message: str, callback) -> None:
        """Streaming: yields text chunks via callback"""
        data = self.build_payload(message)
        buffer = ""
        try:
            async with httpx.AsyncClient(timeout=self.stream_timeout) as client:
                async with client.stream("POST", self.chat_url, headers=self.headers, json=data) as response:
                    async for chunk in response.aiter_text():
                        if chunk:
                            buffer += chunk
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if line.startswith("data: "):
                                    line = line[len("data: "):]
                                try:
                                    parsed = json.loads(line.strip())
                                    text_piece = parsed.get("textResponse", "")
                                    if text_piece:
                                        callback(text_piece)  # pass back to UI
                                    if parsed.get("close", False):
                                        return
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            callback(f"\n[Streaming error: {e}]\n")


# ----------------- GUI -----------------
class ChatbotGUI:
    def __init__(self, chatbot: Chatbot):
        self.chatbot = chatbot
        self.root = tk.Tk()
        self.root.title("Chatbot GUI")
        self.root.geometry("600x400")

        self.chat_log = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state="disabled")
        self.chat_log.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        frame = tk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)

        self.entry = tk.Entry(frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.send_message)

        send_btn = tk.Button(frame, text="Send", command=self.send_message)
        send_btn.pack(side=tk.RIGHT)

    def insert_text(self, speaker: str, text: str):
        self.chat_log.config(state="normal")
        self.chat_log.insert(tk.END, f"{speaker}: {text}\n")
        self.chat_log.see(tk.END)
        self.chat_log.config(state="disabled")

    def send_message(self, event=None):
        user_input = self.entry.get().strip()
        if not user_input:
            return
        
        if user_input.lower() in ["exit", "quit", "q", "stop", "close", "bye", "exit()"]:
            self.insert_text("System", "Goodbye!")
            self.root.quit()   # cleanly exit GUI loop
            return
        
        self.insert_text("You", user_input)
        self.entry.delete(0, tk.END)

        if self.chatbot.stream:
            # Run streaming in a separate thread
            threading.Thread(target=self.run_streaming, args=(user_input,), daemon=True).start()
        else:
            threading.Thread(target=self.run_blocking, args=(user_input,), daemon=True).start()

    def run_blocking(self, message: str):
        response = self.chatbot.send_message(message)
        self.insert_text("Agent", response)

    def run_streaming(self, message: str):
        asyncio.run(self.chatbot.send_message_stream(message, self.stream_callback))

    def stream_callback(self, text_piece: str):
        # Update chat log with streaming text
        self.chat_log.config(state="normal")
        self.chat_log.insert(tk.END, text_piece)
        self.chat_log.see(tk.END)
        self.chat_log.config(state="disabled")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    chatbot = Chatbot()
    gui = ChatbotGUI(chatbot)
    gui.run()
