# Application icon

Place the supplied square application artwork in this directory as `app-icon.png`.

`installer\make_icon.py` converts it to `app.ico` during packaging. The generated ICO
is embedded in both `AI-Memo.exe` and the installer, so the desktop shortcut displays
the same icon.
