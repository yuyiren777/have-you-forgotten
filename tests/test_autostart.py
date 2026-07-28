from utils.autostart import build_command


def test_background_startup_command_quotes_the_executable_path():
    assert build_command(r"C:\Program Files\AI Memo\AI-Memo.exe") == (
        '"C:\\Program Files\\AI Memo\\AI-Memo.exe" --background'
    )
