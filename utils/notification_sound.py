"""System-integrated audio feedback for schedule reminders."""

import logging

logger = logging.getLogger(__name__)


def play_reminder_sound() -> bool:
    """Play the platform notification sound without delaying the reminder UI."""
    try:
        import winsound

        played = winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        if played is not False:
            return True
    except (ImportError, RuntimeError, OSError) as error:
        logger.debug("Windows reminder sound unavailable: %s", error)

    try:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.beep()
            return True
    except Exception as error:
        logger.debug("Qt reminder sound unavailable: %s", error)
    return False
