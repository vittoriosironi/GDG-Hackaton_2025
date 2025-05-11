import gemini
from activity_tracker import SessionTracker


def enhanced_chat(question, sessions_tracker: SessionTracker):
    prompt = f"""
    You are an advanced AI assistant. Your task is to provide a detailed and insightful response to the user's question.
    """