
import os
import sys
import rumps
import time

class MenuBarApp(rumps.App):
    def __init__(self, name, icon_path):
        super(MenuBarApp, self).__init__(name, icon=icon_path, template=True)
        self.menu = ["Show StudyWiz", None, "Quit"]
        
    @rumps.clicked("Show StudyWiz")
    def show_app(self, _):
        # Use AppleScript to activate the main app
        import subprocess
        script = '''
        tell application "System Events"
            set frontmost of process "Python" to true
        end tell
        '''
        subprocess.run(["osascript", "-e", script])
        
        # Also write to a file that the main app can check
        with open("/tmp/studywiz_show", "w") as f:
            f.write("show")
    
    @rumps.clicked("Quit")
    def quit_app(self, _):
        # Signal the main app to quit
        with open("/tmp/studywiz_quit", "w") as f:
            f.write("quit")
        rumps.quit_application()

if __name__ == "__main__":
    # Get icon path from command line arguments
    icon_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Verify the icon exists
    if not icon_path or not os.path.exists(icon_path):
        print(f"Icon not found: {icon_path}")
        sys.exit(1)
        
    app = MenuBarApp("StudyWiz", icon_path)
    app.run()
    