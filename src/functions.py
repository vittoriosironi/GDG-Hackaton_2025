import os
import time
import threading
import google.generativeai as genai
from datetime import datetime
import json
import re

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
    You are an intelligent assistant helping a user manage their study or work sessions.
    Based on the user's input, determine the primary action they want to perform.
    Output ONLY a JSON object with the determined action and any relevant parameters.

    Possible "main_action" values are:
    1. "start_session": If the user wants to start a new study/work session, begin tracking, or set a timer for a session.
    - Include "timer_minutes": <integer> (optional, if a timer duration is specified).
    - Include "session_goals": ["<goal1>", "<goal2>"] (optional, if goals are specified by the user).
    2. "end_session": If the user wants to end the current session or stop tracking.
    3. "during_session_interaction": If the user is asking a question, making a comment, or requesting something that happens *during* an active session (e.g., asking about their productivity, asking for a summary, a general question, or a RAG-type query).
    - Include "user_query": "<the user's original question or statement for further processing>"
    4. "general_command": For other direct commands not fitting above (e.g. "set a 5 minute timer" outside a session context).
    - Include "command_details": "<details of the command>"
    - Include "timer_minutes": <integer> (optional, if a timer duration is specified).

    Responde with a JSON object like this:
    {"action": "general_command"},
    {"action": "start_session", "timer_minutes": 25}

    If the user's intent is unclear or it's a simple conversational turn, use "during_session_interaction" and pass their full input as "user_query".

    User input: "{user_text_input}"

    JSON Output:

    """
    
    try:
        response = model.generate_content([system_prompt, user_input])
        callback_function(response.text)
    except Exception as e:
        callback_function(f"Error connecting to Gemini: {str(e)}")

def process_gemini_response(response, callback_function):
    """
    Process Gemini's response and execute the appropriate action
    
    Args:
        response: The Gemini response object
        callback_function: Function to update the GUI
    """
    try:
        # Get the response text
        response_text = response.text
        
        # Try to parse as JSON
        try:
            # First, find the JSON part in the response
            json_start = response_text.find('```json')
            if json_start != -1:
                # Find the closing ```
                json_end = response_text.find('```', json_start + 7)
                if json_end != -1:
                    # Extract the JSON content
                    json_content = response_text[json_start + 7:json_end].strip()
                    try:
                        response_data = json.loads(json_content)
                        
                        if isinstance(response_data, dict):
                            action = response_data.get('action')
                            if action == 'timer':
                                minutes = response_data.get('minutes')
                                if minutes is not None:
                                    try:
                                        minutes = int(minutes)
                                        if minutes > 0:
                                            start_timer(minutes, callback_function)
                                            callback_function(f"I've started a timer for {minutes} minutes. I'll let you know when it's time!")
                                        else:
                                            callback_function("I'm sorry, but the timer duration needs to be a positive number. Could you please specify how many minutes you'd like to set the timer for?")
                                    except ValueError:
                                        callback_function("I couldn't understand the timer duration. Could you please specify a number of minutes? For example: 'set a timer for 25 minutes'")
                            elif action == 'start_analysis':
                                start_activity_analysis(callback_function)
                                callback_function("I've started tracking your activity. I'll keep an eye on how you're spending your time and provide insights when you're ready!")
                            elif action == 'end_analysis':
                                end_activity_analysis(callback_function)
                                callback_function("I've stopped tracking your activity. You can check the insights in the log files.")
                            else:
                                callback_function("I received an unknown action from Gemini. Please try your command again.")
                        return
                    except json.JSONDecodeError:
                        callback_function("I couldn't understand the JSON response from Gemini. Please try your command again.")
                        return
            
        except Exception as e:
            callback_function(f"Error processing Gemini response: {str(e)}")
            return
            
        # If we didn't find JSON, treat the response as a regular message
        callback_function(response_text)
        
    except Exception as e:
        callback_function(f"Error processing Gemini response: {str(e)}")

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