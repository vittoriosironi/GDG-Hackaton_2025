import google.generativeai as genai
from google.generativeai import types


model = None

def init():
    """
    Initialize the Gemini module.
    """
    global model
    # Configure Gemini
    GOOGLE_API_KEY = "AIzaSyC8K8ymeN6RTDmGsXVnKUGfEDQBSlMBp0I"
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        MODEL_NAME = "gemini-2.0-flash-lite"
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"Warning: Failed to initialize Gemini API: {str(e)}")
        model = None

def query(content, config=None) -> str:
    """
    Query the Gemini API.
    """
    global model
    response = model.generate_content(
        generation_config=config,
        contents=content,
    )
    return response.text