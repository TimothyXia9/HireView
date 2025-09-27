import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

# ---------------- CONFIG ----------------
model_path = "qwen25-onnx/model.onnx"  # path to your ONNX model
resume_text = """
Education: Master of Computer Science, NYU
Experience: 2 years software engineer at XYZ Corp, backend development in Java and Python.
Skills: Java, Python, SQL, Docker, AWS
"""
max_new_tokens = 1024  # limit for streaming generation

# ---------------- LOAD MODEL ----------------
so = ort.SessionOptions()
providers = [("QNNExecutionProvider", {})]  # QNN only
session = ort.InferenceSession(model_path, sess_options=so, providers=providers)
tokenizer = AutoTokenizer.from_pretrained("qwen25-onnx")

# ---------------- TOKENIZE PROMPT ----------------
prompt = f"""
You are an experienced hiring manager.

Here is the candidate's resume:
{resume_text}

Instructions:
- ONLY analyze what is explicitly written in the resume.
- DO NOT invent or assume any experiences, skills, or details that are not present in the text.
- If information is missing, say "Not provided".
- Follow the structure below in your response.

Your review must include:

1. Overall Evaluation: A short summary of the strengths and weaknesses of the entire resume.

2. Section-by-Section Feedback:
   For each section of the resume (Education, Experience, Skills, Projects, etc.), do the following:
   - Give a clear evaluation of that section.
   - Provide specific improvement suggestions.
   - If relevant, suggest how one entry could be rewritten for clarity or impact.

Do not add any new sections that are not present in the resume.
"""
enc = tokenizer(prompt, return_tensors="np")
input_ids = enc["input_ids"]
attention_mask = enc["attention_mask"]
position_ids = np.arange(input_ids.shape[1], dtype=np.int64)[None, :]

# ---------------- BUILD EMPTY KV CACHE ----------------
input_names = [i.name for i in session.get_inputs()]
num_layers = sum(1 for n in input_names if n.endswith(".key"))
empty_cache = {}
for i in range(num_layers):
    empty_cache[f"past_key_values.{i}.key"] = np.zeros((1, 2, 0, 64), dtype=np.float32)
    empty_cache[f"past_key_values.{i}.value"] = np.zeros((1, 2, 0, 64), dtype=np.float32)

# ---------------- PREFILL STEP ----------------
feeds = {
    "input_ids": input_ids,
    "attention_mask": attention_mask,
    "position_ids": position_ids,
    **empty_cache
}
outs = session.run(None, feeds)
logits = outs[0]
next_token = logits[:, -1, :].argmax(axis=-1).item()

# ---------------- STORE KV CACHE ----------------
cache = {}
for i in range(num_layers):
    cache[f"past_key_values.{i}.key"] = outs[1 + 2*i]
    cache[f"past_key_values.{i}.value"] = outs[2 + 2*i]

generated = [next_token]
print("Streaming output:\n", end="", flush=True)

# ---------------- AUTOREGRESSIVE LOOP ----------------
for _ in range(max_new_tokens):
    inp = np.array([[next_token]], dtype=np.int64)
    attn = np.ones((1, cache["past_key_values.0.key"].shape[2] + 1), dtype=np.int64)
    pos = np.array([[cache["past_key_values.0.key"].shape[2]]], dtype=np.int64)

    feeds = {
        "input_ids": inp,
        "attention_mask": attn,
        "position_ids": pos,
        **cache
    }
    outs = session.run(None, feeds)
    logits = outs[0]
    next_token = logits[:, -1, :].argmax(axis=-1).item()
    generated.append(next_token)

    for i in range(num_layers):
        cache[f"past_key_values.{i}.key"] = outs[1 + 2*i]
        cache[f"past_key_values.{i}.value"] = outs[2 + 2*i]

    token_text = tokenizer.decode([next_token], skip_special_tokens=True)
    print(token_text, end="", flush=True)

    if next_token == tokenizer.eos_token_id:
        break

print("\n\n=== Complete ===")
print(tokenizer.decode(generated, skip_special_tokens=True))
