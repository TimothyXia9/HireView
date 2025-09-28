import gradio as gr
import requests
import yaml
import asyncio
import httpx
import json

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

    def chat(self, message: str) -> str:
        """
        Send a chat request in non-streaming mode.
        """
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
        try:
            return chat_response.json()['textResponse']
        except ValueError:
            return "Response is not valid JSON"
        except Exception as e:
            return f"Chat request failed. Error: {e}"

    def streaming_chat(self, message: str):
        """
        Combined synchronous generator that wraps an asynchronous generator—
        it streams chat responses in chunks and yields the conversation history.
        """
        response_text = ""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def async_stream():
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
                                        yield parsed_chunk.get("textResponse", "")
                                    except json.JSONDecodeError:
                                        continue
                                    except Exception as e:
                                        yield f"Error processing chunk: {e}"
            except httpx.RequestError as e:
                yield f"Streaming chat request failed. Error: {e}"

        agen = async_stream()
        try:
            while True:
                chunk = loop.run_until_complete(agen.__anext__())
                response_text += chunk
                yield response_text
        except StopAsyncIteration:
            pass
        finally:
            loop.close()
        yield response_text

def main():
    chatbot = Chatbot()

    with gr.Blocks() as app:
        gr.Markdown("# Chatbot Interface")
        chatbot_widget = gr.Chatbot(type="messages")
        msg = gr.Textbox()
        clear = gr.Button("Clear")

        def user_message(message, history):
            history.append({"role": "user", "content": message})
            return "", history

        def bot_response(history):
            user_msg = history[-1]["content"]
            if chatbot.stream:
                history.append({"role": "assistant", "content": ""})
                for updated in chatbot.streaming_chat(user_msg):
                    history[-1]["content"] = updated
                    yield history
            else:
                response = chatbot.chat(user_msg)
                history.append({"role": "assistant", "content": response})
                yield history

        msg.submit(user_message, [msg, chatbot_widget], [msg, chatbot_widget], queue=False).then(
            bot_response, chatbot_widget, chatbot_widget
        )
        clear.click(lambda: None, None, chatbot_widget, queue=False)

    app.launch()

if __name__ == "__main__":
    main()