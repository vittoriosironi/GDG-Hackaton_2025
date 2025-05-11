
import pywinctl as pwc

def get_current_visible_windows() -> list[str]:
    """
    Get the current windows in the system.
    """
    windows = pwc.getWindows()
    current_windows = []
    for window in windows:
        if window.isVisible and not window.isMinimized:
            current_windows.append(window.getAppName())
    return current_windows
    
def get_current_active_window() -> str:
    """
    Get the current active window in the system.
    """
    active_window = pwc.getActiveWindow()
    if active_window:
        return active_window.getAppName()
    return "unknown"


def minimize_app(app_name) -> bool:
    """
    Minimize the application with the given name.
    """
    windows = pwc.getWindows()
    for window in windows:
        if window.getAppName() == app_name:
            window.minimize()
            return True
    return False
    
def move_and_resize(app_name, x, y, width, height) -> bool:
    """
    Move and resize the application with the given name.
    """
    windows = pwc.getWindows()
    for window in windows:
        if window.getAppName() == app_name:
            window.move(x, y)
            window.resize(width, height)
            return True
    return False