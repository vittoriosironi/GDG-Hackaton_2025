import time
import json
import psutil
import platform
import pywinctl as pwc
from datetime import datetime
from pynput import mouse, keyboard
import threading
import re
import logging

class SessionTracker:
    def __init__(self, session_name, user_goals=None):
        self.session_name = session_name
        self.user_goals = user_goals or []
        self.start_time = datetime.now()
        self.end_time = None
        self.events = []
        self.active_window_log = []
        self.activity_summary = {}
        self.interaction_count = 0
        self.app_usage_time = {}
        self.context_switches = 0
        self.activity_clusters = []
        self.is_tracking = False
        self.last_activity_time = time.time()
        self.idle_threshold = 10  # seconds
        self.summarization_interval = 5 * 60  # seconds
        self.tracking_threads = []
        
        # Typing tracking variables
        self.typing_start_time = None
        self.typing_active = False
        self.typing_timeout = 1.5  # seconds of inactivity before typing is considered stopped
        self.typing_monitor_thread = None
        self.total_typing_time = 0  # Total cumulative typing time in seconds
        self.typing_sessions_count = 0  # Count of typing sessions
        
        # Configure logging
        logging.basicConfig(level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s',
                           filename=f"session_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log")
        
        self.logger = logging.getLogger(__name__)
        
    def start_tracking(self):
        """Start all tracking mechanisms"""
        self.is_tracking = True
        self.log_event("session_start", {"goals": self.user_goals}, track_idle=False)
        
        # Start window tracking thread
        window_thread = threading.Thread(target=self._track_active_windows)
        window_thread.daemon = True
        window_thread.start()
        self.tracking_threads.append(window_thread)
        
        # Start input tracking
        self._setup_input_listeners()
        
        # Start idle detection thread
        idle_thread = threading.Thread(target=self._monitor_idle)
        idle_thread.daemon = True
        idle_thread.start()
        self.tracking_threads.append(idle_thread)
        
        # Start typing monitor thread
        typing_thread = threading.Thread(target=self._monitor_typing)
        typing_thread.daemon = True
        typing_thread.start()
        self.tracking_threads.append(typing_thread)
        
        # # Start periodic summary thread
        summary_thread = threading.Thread(target=self._periodic_summarization)
        summary_thread.daemon = True
        summary_thread.start()
        self.tracking_threads.append(summary_thread)
        
        self.logger.info(f"Session tracking started: {self.session_name}")
        
    def stop_tracking(self):
        """Stop all tracking and generate final report"""
        if not self.is_tracking:
            return
            
        # End any active typing session before stopping
        if self.typing_active:
            self._end_typing_session()
            
        self.is_tracking = False
        self.end_time = datetime.now()
        
        # Include typing stats in the session end event
        self.log_event("session_end", {
            "duration": str(self.end_time - self.start_time),
            "total_typing_time": round(self.total_typing_time, 2),
            "typing_sessions_count": self.typing_sessions_count,
            "typing_percentage": round((self.total_typing_time / (self.end_time - self.start_time).total_seconds()) * 100, 2) if self.total_typing_time > 0 else 0
        })
                
        self.logger.info(f"Session tracking stopped: {self.session_name} - Total typing time: {round(self.total_typing_time, 2)}s across {self.typing_sessions_count} sessions")
        
    def log_event(self, event_type, data=None, track_idle=True):
        """Log a specific event with timestamp"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data or {}
        }
        self.events.append(event)
        if track_idle:
            self.last_activity_time = time.time()
        
        self.logger.info(f"Event: {event_type} - {data}")
    
    def add_manual_checkpoint(self, description):
        """Allow user to manually mark an important moment"""
        self.log_event("manual_checkpoint", {"description": description})
    
    def _track_active_windows(self):
        """Track active window changes"""
        last_active_window = None
        last_change_time = time.time()
        
        while self.is_tracking:
            
            try:
                # Get current active window
                active_window = pwc.getActiveWindow()

                if active_window:
                    # Get window title safely
                    try:
                        current_window = {
                            "title": active_window.title,
                            "app": active_window.getAppName(),
                        }
                    except Exception as e:
                        self.logger.error(f"Error getting window title: {str(e)}")
                        current_window = {
                            "title": "unknown_app",
                            "app": "unknown_app"
                        }
                    
                    if last_active_window == None:
                        last_active_window = current_window
                        self.log_event("app_change", {
                            "from": None,
                            "to": current_window,
                            "duration_previous": 0
                        })
                    
                    # If window changed
                    if last_active_window["title"] != current_window["title"] or \
                          last_active_window["app"] != current_window["app"]:
                        now = time.time()
                        
                        # Log previous window duration if it exists
                        if last_active_window:
                            duration = now - last_change_time
                            self._update_app_usage(last_active_window, duration)
                            
                            self.log_event("app_change", {
                                "from": last_active_window,
                                "to": current_window,
                                "duration_previous": round(duration, 2)
                            })
                            
                            self.context_switches += 1
                        
                        last_active_window = current_window
                        last_change_time = now
                        
                        
            
                    # Log active window every 10 seconds for timeline
                    self.active_window_log.append({
                        "time": datetime.now().isoformat(),
                        "window": current_window["title"],
                    })
                
            except Exception as e:
                self.logger.error(f"Error tracking windows: {e}")
                # Continue tracking even after an error
                
            time.sleep(1)
    
    def _setup_input_listeners(self):
        """Setup keyboard and mouse event listeners"""
        # Keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
        
        # Mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll)
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
    
    def _on_key_press(self, key):
        """Handle key press events"""
        if not self.is_tracking:
            return False
            
        self.interaction_count += 1
        self.last_activity_time = time.time()
        
        # Start or continue typing session
        current_time = time.time()
        if not self.typing_active:
            self.typing_active = True
            self.typing_start_time = current_time
            self.logger.debug(f"Started new typing session (total sessions so far: {self.typing_sessions_count})")

    
    def _on_key_release(self, key):
        """Handle key release events"""
        if not self.is_tracking:
            return False
            
        # Update the typing activity - this keeps the typing session active
        # but we don't need to start a new one here, as that happens on key press
        if self.typing_active:
            self.last_activity_time = time.time()
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        if not self.is_tracking or not pressed:
            return
            
        self.interaction_count += 1
        
        self.log_event("user_input", {"type": "mouse_click"})
        
    def _on_mouse_move(self, x, y):
        """Handle mouse move events"""
        if not self.is_tracking:
            return
            
        self.interaction_count += 1
        self.last_activity_time = time.time()
        
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll events"""
        if not self.is_tracking:
            return
            
        if dx == 0 and dy == 0:
            return
            
        self.interaction_count += 1
        self.last_activity_time = time.time()
        
    def _monitor_idle(self):
        """Monitor for idle periods"""
        idle_start = None
        is_idle = False
        
        while self.is_tracking:
            time_since_activity = time.time() - self.last_activity_time
            
            # Transition to idle
            if not is_idle and time_since_activity > self.idle_threshold:
                idle_start = time.time()
                is_idle = True
                self.log_event("idle_start", {"after_seconds": round(time_since_activity, 2)}, track_idle=False)
                
                # If typing was active, end it
                if self.typing_active:
                    self._end_typing_session()
            
            # Transition from idle back to active
            elif is_idle and time_since_activity <= self.idle_threshold:
                
                idle_duration = time.time() - (idle_start or time.time())
                is_idle = False
                self.log_event("idle_end", {"duration_seconds": round(idle_duration, 2)}, track_idle=False)
            
            time.sleep(1)
    
    def _periodic_summarization(self):
            """Periodically create summaries of recent activity"""
            while self.is_tracking:
                # Sleep for 5 minutes
                time.sleep(self.summarization_interval)
                
                # Create a summary
                recent_events = self.events[-100:] if len(self.events) > 100 else self.events
                event_types = {}
                for event in recent_events:
                    event_type = event["type"]
                    if event_type in event_types:
                        event_types[event_type] += 1
                    else:
                        event_types[event_type] = 1
                
                # Get most used applications in this period
                recent_apps = {}
                for app, duration in self.app_usage_time.items():
                    if app not in recent_apps:
                        recent_apps[app] = duration
                
                # Sort by usage time
                sorted_apps = sorted(recent_apps.items(), key=lambda x: x[1], reverse=True)
                top_apps = sorted_apps[:3] if len(sorted_apps) > 3 else sorted_apps
                
                # Get window information using PyWinCtl
                try:
                    current_windows = []
                    all_windows = pwc.getAllWindows()
                    # Filter to visible windows only
                    visible_windows = [w for w in all_windows if w.isVisible and w.title]
                    # Get top 5 visible windows
                    for win in visible_windows[:5]:
                        current_windows.append({
                            "title": win.title,
                            "app": win.getAppName()
                        })
                except Exception as e:
                    self.logger.error(f"Error getting current windows: {str(e)}")
                    current_windows = []
                
                # Calculate typing statistics for this period
                typing_events = [e for e in recent_events if e["type"] == "typed_for"]
                typing_time_in_period = sum(e["data"].get("duration_seconds", 0) for e in typing_events)
                
                summary = {
                    "period": "last_5_minutes",
                    "event_distribution": event_types,
                    "top_applications": {app: round(duration, 2) for app, duration in top_apps},
                    "interaction_count": self.interaction_count,
                    "context_switches": self.context_switches,
                    "current_windows": current_windows,
                    "typing_stats": {
                        "total_typing_time": round(self.total_typing_time, 2),
                        "typing_sessions_count": self.typing_sessions_count,
                        "typing_time_in_period": round(typing_time_in_period, 2),
                        "avg_session_duration": round(self.total_typing_time / self.typing_sessions_count, 2) if self.typing_sessions_count > 0 else 0
                    }
                }
                
                self.log_event("periodic_summary", summary, track_idle=False)
        
    def _update_app_usage(self, window, duration):
        """Update application usage time tracking"""
        app_name = window["app"]
        if app_name in self.app_usage_time:
            self.app_usage_time[app_name] += duration
        else:
            self.app_usage_time[app_name] = duration
    
    def _monitor_typing(self):
        """Monitor typing activity and log when typing stops"""
        while self.is_tracking:
            
            # Check if typing is active but no recent keypress
            if self.typing_active and self.typing_start_time is not None:
                time_since_last_keystroke = time.time() - self.last_activity_time
                
                # If no keystroke for typing_timeout seconds, end typing session
                if time_since_last_keystroke > self.typing_timeout:
                    self._end_typing_session()
                
            time.sleep(0.5)  # Check more frequently than other monitors
    
    def _end_typing_session(self):
        """End the current typing session and log the duration"""
        if not self.typing_active or self.typing_start_time is None:
            return
        
        typing_duration = time.time() - self.typing_start_time
        # Only log if typing lasted more than 1 second
        if typing_duration > 1.0:
            # Update cumulative typing stats
            self.total_typing_time += typing_duration
            self.typing_sessions_count += 1
            
            # Get the current active window for context
            try:
                active_window = pwc.getActiveWindow()
                window_context = {
                    "title": active_window.title if active_window else "Unknown",
                    "app": active_window.getAppName() if active_window else "Unknown"
                }
            except Exception:
                window_context = {"title": "Unknown", "app": "Unknown"}
                
            # Log the typing session with context
            self.log_event("typed_for", {
                "duration_seconds": round(typing_duration, 2),
                "total_typing_time": round(self.total_typing_time, 2),
                "window_context": window_context,
                "session_number": self.typing_sessions_count
            })
            
        # Reset typing state
        self.typing_active = False
        self.typing_start_time = None
        # We don't reset interaction_count because it's a session-wide metric
   
# Example usage
if __name__ == "__main__":
    # Initialize the tracker with session name and goals
    tracker = SessionTracker(
        session_name="Generic Session",
        user_goals=["Write code for an hackaton app", "Using the LLM to generate code"]
    )
    
    # Start tracking
    tracker.start_tracking()
    
    try:
        # This would run in your main application loop
        print("Tracking session... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop tracking and generate report
        tracker.stop_tracking()
        
        #print(json.dumps(llm_data, indent=2))