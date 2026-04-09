import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
api_key = os.environ["GOOGLE_API_KEY"]
models = ["models/text-embedding-004", "models/embedding-001", "models/text-embedding-004", "models/gemini-embedding-001", "models/gemini-embedding-2-preview"]

for model_name in models:
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)
        res = embeddings.embed_query("hello world")
        print(f"SUCCESS: {model_name}")
        break
    except Exception as e:
        print(f"FAIL: {model_name} - {type(e).__name__}")
        continue
