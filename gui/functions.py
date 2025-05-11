import os
import time
import threading
import google.generativeai as genai
from datetime import datetime

# Configure Gemini API
def configure_gemini():
    api_key = "AIzaSyC8K8ymeN6RTDmGsXVnKUGfEDQBSlMBp0I"
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

# Global variables
activity_log = []
timer_thread = None
timer_active = False
analysis_active = False

def process_user_input(user_input, callback_function):
    """
    Process user input and determine which action to take
    
    Args:
        user_input (str): The user's input text
        callback_function (function): Function to handle Gemini's response
    """
    model = configure_gemini()
    
    # Create a system prompt that instructs Gemini on the available actions
    system_prompt = """
    You are a productivity assistant that helps with focus sessions.
    Based on user input, determine which of these actions to take:
    1. Start a timer for X minutes (where X is a number mentioned by the user)
    2. Start activity analysis (begin tracking what the user is doing)
    3. End activity analysis (stop tracking and provide insights)
    
    Respond in JSON format with:
    {"action": "timer", "minutes": X} OR
    {"action": "start_analysis"} OR
    {"action": "end_analysis"}
    """
    
    try:
        response = model.generate_content([system_prompt, user_input])
        process_gemini_response(response, callback_function)
    except Exception as e:
        callback_function(f"Error connecting to Gemini: {str(e)}")

def process_gemini_response(response, callback_function):
    """
    Process Gemini's response and execute the appropriate action
    
    Args:
        response: The response from Gemini
        callback_function: Function to update the GUI
    """
    try:
        # Extract the action from Gemini's response
        response_text = response.text
        
        if "timer" in response_text.lower() and "minute" in response_text.lower():
            # Extract minutes
            import re
            minutes_match = re.search(r'(\d+)\s*minute', response_text.lower())
            if minutes_match:
                minutes = int(minutes_match.group(1))
                # Start activity analysis along with timer
                start_activity_analysis(callback_function)
                start_timer(minutes, callback_function)
                callback_function(f"Starting timer for {minutes} minutes and beginning activity tracking")
            else:
                callback_function("I couldn't determine how many minutes to set the timer for.")
        
        elif "start" in response_text.lower() and "analysis" in response_text.lower():
            start_activity_analysis(callback_function)
            callback_function("Starting activity analysis. I'll track your work session.")
        
        elif "end" in response_text.lower() and "analysis" in response_text.lower():
            end_activity_analysis(callback_function)
        
        else:
            callback_function("I'm not sure what action to take. You can ask me to start a timer, start activity analysis, or end activity analysis.")
    
    except Exception as e:
        callback_function(f"Error processing response: {str(e)}")

def start_timer(minutes, callback_function):
    """
    Start a timer for the specified number of minutes
    
    Args:
        minutes (int): Timer duration in minutes
        callback_function: Function to update the GUI when timer completes
    """
    global timer_thread, timer_active
    
    # Cancel existing timer if running
    if timer_thread and timer_thread.is_alive():
        timer_active = False
        timer_thread.join(0.1)
    
    timer_active = True
    
    def timer_worker():
        end_time = time.time() + (minutes * 60)
        while time.time() < end_time and timer_active:
            time.sleep(1)
        
        if timer_active:  # Only notify if timer wasn't cancelled
            callback_function(f"Timer for {minutes} minutes has finished!")
    
    timer_thread = threading.Thread(target=timer_worker)
    timer_thread.daemon = True
    timer_thread.start()

def cancel_timer():
    """Cancel the currently running timer"""
    global timer_active
    timer_active = False

def start_activity_analysis(callback_function):
    """
    Start tracking user activity
    
    Args:
        callback_function: Function to update the GUI
    """
    global activity_log, analysis_active
    
    # Only initialize if not already active
    if not analysis_active:
        activity_log = []
        activity_log.append({"type": "session_start", "timestamp": datetime.now().isoformat()})
        analysis_active = True

def log_activity(activity_type, description=""):
    """
    Add an activity entry to the log
    
    Args:
        activity_type (str): Type of activity
        description (str): Description of the activity
    """
    global activity_log, analysis_active
    
    if analysis_active:
        activity_log.append({
            "type": activity_type,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })

def end_activity_analysis(callback_function):
    """
    End activity analysis and provide insights
    
    Args:
        callback_function: Function to update the GUI with analysis results
    """
    global activity_log, analysis_active
    
    if not analysis_active or not activity_log:
        callback_function("No activity analysis session in progress.")
        return
    
    activity_log.append({"type": "session_end", "timestamp": datetime.now().isoformat()})
    analysis_active = False
    
    # Send activity log to Gemini for analysis
    model = configure_gemini()
    
    system_prompt = """
    You are an activity analysis assistant. Based on the provided activity log,
    provide insights on productivity, focus, and suggestions for improvement.
    Keep your analysis concise but insightful. Structure your response with these sections:
    1. Session Overview
    2. Key Observations
    3. Recommendations
    """
    
    try:
        response = model.generate_content([
            system_prompt,
            f"Here is the activity log for analysis: {activity_log}"
        ])
        callback_function(f"Activity Analysis Results:\n\n{response.text}")
    except Exception as e:
        callback_function(f"Error analyzing activity: {str(e)}")
    
    # Clear the activity log after analysis
    activity_log = []