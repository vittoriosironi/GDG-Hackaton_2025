import google.generativeai as genai
from google.generativeai import types


model = None

def init():
    """
    Initialize the Gemini module.
    """
    global model
    # Configure Gemini
    GOOGLE_API_KEY = "AIzaSyDkWDYv3lmKfngo_zN1G8WYxDB3_571dN4"
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        MODEL_NAME = "gemini-2.5-pro-preview-05-06"
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"Warning: Failed to initialize Gemini API: {str(e)}")
        model = None

def query(content, config={"temperature": 0.1}) -> str:
    """
    Query the Gemini API.
    """
    global model
    response = model.generate_content(
        generation_config=config,
        contents=content,
    )
    return response.text