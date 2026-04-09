import os
from dotenv import load_dotenv
import urllib.request
import json

load_dotenv()
api_key = os.environ["GOOGLE_API_KEY"]
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print("Fetching models...")
try:
    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    for m in data.get('models', []):
        if 'embedContent' in m.get('supportedGenerationMethods', []):
            print(m['name'])
except Exception as e:
    print(f"Error: {e}")
