"""Windows startup registration for the packaged desktop application."""
import os
import sys


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "HaveYouForgotten"


def is_supported() -> bool:
    """Startup registration is only safe for the packaged Windows executable."""
    return os.name == "nt" and bool(getattr(sys, "frozen", False))


def build_command(executable: str | None = None) -> str:
    executable = executable or sys.executable
    return f'"{executable}" --background'


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command, _ = winreg.QueryValueEx(key, VALUE_NAME)
        return str(command) == build_command()
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """Create or remove the per-user startup entry without admin rights."""
    if not is_supported():
        return False
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, build_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
