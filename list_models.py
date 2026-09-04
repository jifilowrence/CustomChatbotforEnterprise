import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

response = requests.get(url)
models = response.json().get("models", [])
for m in models:
    name = m.get("name", "")
    if "gemini" in name:
        print(f"Model: {name} | methods: {m.get('supportedGenerationMethods')}")
