import asyncio
import httpx
import json
import requests
import sys
import threading
import time
import yaml

def loading_indicator() -> None:
    """
    Display a loading indicator in the console while the chat request is being processed
    """
    while not stop_loading:
        for _ in range(10):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(0.5)
        sys.stdout.write('\r' + ' ' * 10 + '\r')
        sys.stdout.flush()
    print('')

class Chatbot:
    def __init__(self):
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

        self.api_key = config["api_key"]
        self.base_url = config["model_server_base_url"]
        self.stream = config["stream"]
        self.stream_timeout = config["stream_timeout"]
        self.workspace_slug = config["workspace_slug"]

        if self.stream:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/stream-chat"
        else:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/chat"

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key
        }


    def run(self) -> None:
        """
        Run the chat application loop. The user can type messages to chat with the assistant.
        """
        while True:
            user_message = input("You: ")
            if user_message.lower() in [
                "exit",
                "quit",
                "q",
                "stop",
                "close",
                "bye",
                "exit()" # I always think I am in a python shell lol
            ]:
                break
            print("")
            try:
                self.streaming_chat(user_message) if self.stream \
                    else self.blocking_chat(user_message)
            except Exception as e:
                print("Error! Check the model is correctly loaded. More details in README troubleshooting section.")
                sys.exit(f"Error details: {e}")

    def blocking_chat(self, message: str) -> str:
        """
        Send a chat request to the model server and return the response
        
        Inputs:
        - message: The message to send to the chatbot
        """
        global stop_loading
        stop_loading = False
        loading_thread = threading.Thread(target=loading_indicator)
        loading_thread.start()

        data = {
            "message": message,
            "mode": "chat",
            "sessionId": "example-session-id",
            "attachments": []
        }

        chat_response = requests.post(
            self.chat_url,
            headers=self.headers,
            json=data
        )

        stop_loading = True
        loading_thread.join()

        try:
            print("Agent: ", end="")
            print(chat_response.json()['textResponse'])
            # return text_response
            print("")
        except ValueError:
            return "Response is not valid JSON"
        except Exception as e:
            return f"Chat request failed. Error: {e}"
        
    def streaming_chat(self, message: str) -> None:
        """
        Wrapper to run the asynchronous streaming chat.
        """
        asyncio.run(self.streaming_chat_async(message))

    async def streaming_chat_async(self, message: str) -> None:
        """
        Stream chat responses asynchronously from the model server and display them in real-time.
        Buffers incomplete JSON chunks until a full chunk (terminated by newline) is collected.
        """

        data = {
            "message": message,
            "mode": "chat",
            "sessionId": "example-session-id",
            "attachments": []
        }

        buffer = ""
        try:
            async with httpx.AsyncClient(timeout=self.stream_timeout) as client:
                async with client.stream("POST", self.chat_url, headers=self.headers, json=data) as response:
                    print("Agent: ", end="")
                    async for chunk in response.aiter_text():
                        if chunk:
                            buffer += chunk
                            # Process each complete line
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if line.startswith("data: "):
                                    line = line[len("data: "):]
                                try:
                                    parsed_chunk = json.loads(line.strip())
                                    print(parsed_chunk.get("textResponse", ""), end="", flush=True)

                                    if parsed_chunk.get("close", False):
                                        print("")
                                except json.JSONDecodeError:
                                    # The line is not a complete JSON; wait for more data.
                                    continue
                                except Exception as e:
                                    # generic error handling, quit for debug
                                    print(f"Error processing chunk: {e}")
                                    sys.exit()
        except httpx.RequestError as e:
            print(f"Streaming chat request failed. Error: {e}")

if __name__ == '__main__':
    stop_loading = False
    chatbot = Chatbot()
    chatbot.run()