import os
import json
from imagine import ImagineClient

# Config json
HISTORY_FILE = "conversation_history.json"
MAX_HISTORY = 50 # 50 history messages

# Config Cirrascale
client = ImagineClient(
    debug=False,
    max_retries=3,
    endpoint="",
    api_key=""
)

# chat history
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                conversation_history = list(data.values())[0] if data else []
            elif isinstance(data, list):
                conversation_history = data
            else:
                conversation_history = []
    except Exception:
        conversation_history = []
else:
    conversation_history = []

# save chat history
def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(conversation_history, f, ensure_ascii=False, indent=2)

# interface
def chat_with_cirrascale(user_input: str) -> str:
    try:
        global conversation_history
        messages = conversation_history

        # history messages < 50
        if len(messages) > MAX_HISTORY:
            messages = messages[-MAX_HISTORY:]

        # append user input
        messages.append({"role": "user", "content": user_input})

        # Cirrascale Chat reply
        chat_response = client.chat(
            messages=messages,
            model="Llama-3.1-8B",
            max_tokens=512
        )

        assistant_reply = chat_response.first_content

        # append llmama output
        messages.append({"role": "assistant", "content": assistant_reply})
        conversation_history = messages
        save_history()

        return assistant_reply

    except Exception as e:
        return f"Error: {str(e)}"

response = chat_with_cirrascale("What is 1+1?")
print(response)