import time
from datetime import datetime, timedelta
import signal
import sys
import subprocess

def show_notification(title: str, message: str, sound: bool = False):
    """
    Show a macOS notification using terminal-notifier with a custom icon
    """
    cmd = ['terminal-notifier',
           '-title', title,
           '-message', message,
           '-subtitle', 'Timer',
           '-appIcon', '/System/Applications/Calendar.app/Contents/Resources/Calendar.icns']
    if sound:
        cmd.extend(['-sound', 'default'])
    subprocess.run(cmd)

def timer(minutes: int):
    """
    Create a macOS timer that runs for the specified number of minutes.
    
    Args:
        minutes (int): Number of minutes to set the timer for
    """
    print(f"Timer started for {minutes} minutes")
    
    # Show start notification with duration
    show_notification(
        title=f"Timer Started - {minutes} minutes",
        message="The timer has started"
    )
    
    # Calculate end time
    end_time = datetime.now() + timedelta(minutes=minutes)
    
    # Show countdown
    while datetime.now() < end_time:
        remaining = end_time - datetime.now()
        remaining_minutes = remaining.seconds // 60
        remaining_seconds = remaining.seconds % 60
        print(f"Time remaining: {remaining_minutes:02d}:{remaining_seconds:02d}", end="\r")
        time.sleep(1)
    
    print("\nTimer complete!")
    
    # Show completion notification with sound
    show_notification(
        title="Timer Complete!",
        message=f"Your {minutes} minute timer has finished!",
        sound=True
    )

def signal_handler(sig, frame):
    """
    Handle Ctrl+C to stop the timer gracefully
    """
    print("\nTimer stopped by user")
    show_notification(
        title="Timer Stopped",
        message="Timer was stopped by user",
        sound=True
    )
    sys.exit(0)

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    # Check if a duration was passed as a command line argument
    if len(sys.argv) > 1:
        try:
            minutes = int(sys.argv[1])
            timer(minutes)
        except ValueError:
            print("Please provide a valid number of minutes")
            sys.exit(1)
    else:
        print("Usage: python macos_timer.py <minutes>")
        sys.exit(1)
