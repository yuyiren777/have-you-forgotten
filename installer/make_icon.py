"""Convert the supplied PNG app icon into a multi-size Windows ICO file."""
from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "resources" / "app-icon.png"
TARGET = ROOT / "resources" / "app.ico"
SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Missing icon source: {SOURCE}")
    image = Image.open(SOURCE).convert("RGBA")
    edge = min(image.size)
    left = (image.width - edge) // 2
    top = (image.height - edge) // 2
    image = image.crop((left, top, left + edge, top + edge))
    image.save(TARGET, format="ICO", sizes=SIZES)
    print(f"Created {TARGET}")


if __name__ == "__main__":
    main()
