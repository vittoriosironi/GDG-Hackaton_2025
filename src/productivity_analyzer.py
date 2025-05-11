import gemini
from typing import Optional
from pydantic import BaseModel, Field
import json
from PIL import Image
import logging
from time import time

# Configure logging
# File name is based on the current date and time
logging.basicConfig(
    filename=f"workflow_{time().strftime('%Y%m%d_%H%M%S')}.log"
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ProductivityBrief(BaseModel):
    """
    Model to represent the productivity brief.
    """
    productivity_score: float = Field(..., description="Productivity score from 0 to 1")
    brief_summary: str = Field(..., description="Brief summary of the user's productivity")
    
file = "./sessions/session_0.log"

file_content = []
# Read content of the file
with open(file, 'r') as f:
    content = f.readlines()
    content = [line.strip() for line in content]
    content = [line for line in content if line]  # Remove empty lines
    file_content = content

def detect_screenshots(chunk):
    """
    Detect if there are any screenshots in the chunk.
    """
    screenshots = []
    for line in chunk:
        if "productivity_screenshot" not in line:
            continue

        # Get string after "productivity_screenshot - "
        raw_screenshot = line.split("productivity_screenshot - ")[1].replace("'", '"')
        logging.info(f"Raw screenshot data: {raw_screenshot}")
        screenshot_data = json.loads(raw_screenshot)

        screenshots.append(
            Image.open(screenshot_data['path'])
        )

    return screenshots

def analyze_productivity_chunk(chunk, previous_analysis):
    avg_coeff = 0.4
    base_prompt = """
    You are a productivity analyzer. You will be given a portion of a log file from a user.
    Your task is to analyze the log file and provide a summary of the user's productivity.

    Try not to repeat the previous analysis.
    
    Suggestions should be optional and not redundant.
    
    You can also see some relevant screenshots of the user activity.
    
    Previous analysis:
    {previous_analysis}
    

    Here is the log file content:
    {file_content}
    """
    
    prompt = base_prompt.format(
        file_content=chunk,
        previous_analysis=previous_analysis[-5:] if len(previous_analysis) > 0 else ""
    )
    
    screenshots = detect_screenshots(chunk)
    
    
    response = gemini.query(content=[prompt] + screenshots, config={
        "response_mime_type": "application/json",
        "response_schema": ProductivityBrief
    })
    response = json.loads(response)
    logging.info(f"{response}")
    # Running average of productivity score
    if avg_productivity is None:
        avg_productivity = response['productivity_score']
    else:
        # Weighted average
        avg_productivity = avg_productivity * avg_coeff + response['productivity_score'] * (1 - avg_coeff)
    previous_analysis.append(response)
    
    logging.info(f"{response}")
    
    if avg_productivity <= 0.5:
        suggestion_prompt = """
        Provide a suggestion to improve productivity based on the analysis.
        
        Previous analysis:
        {previous_analysis}
        """
        suggestion_prompt = suggestion_prompt.format(
            previous_analysis=previous_analysis[-5:] if len(previous_analysis) > 0 else ""
        )
        
        suggestion_response = gemini.query(content=suggestion_prompt, config={
            "response_mime_type": "application/json",
            "response_schema": str
        })
        logging.info(f"{suggestion_response}")

def __main__():
    """
    Main function to run the productivity analyzer.
    """
    gemini.init()
    previous_analysis = []
    for i in range(0, len(file_content), 10):
        chunk = file_content[i:i+10]
        analyze_productivity_chunk(chunk, previous_analysis)

if __name__ == "__main__":
    __main__()