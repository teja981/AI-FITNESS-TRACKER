import requests
import json

HUGGINGFACE_API_TOKEN = "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" # Replace with your token
HUGGINGFACE_MODEL_URL = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english" # Replace with your URL

user_message = "What is the capital of France?"

headers = {
    "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
    "Content-Type": "application/json"
}
data = {"inputs": user_message}

print(f"Testing URL: {HUGGINGFACE_MODEL_URL}")
print(f"Using Token: {HUGGINGFACE_API_TOKEN}")

try:
    response = requests.post(HUGGINGFACE_MODEL_URL, headers=headers, json=data)
    response.raise_for_status()  # This will raise an HTTPError for bad status codes (4xx or 5xx)

    if response.status_code == 200:
        bot_reply = response.json()[0]["generated_text"]
        print("\nSUCCESS!")
        print("Bot Reply:", bot_reply)
    else:
        print(f"\nFAILURE: Received status code {response.status_code}")
        print("Response Body:", response.text)

except requests.exceptions.RequestException as e:
    print(f"\nAn error occurred: {e}")