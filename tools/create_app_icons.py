"""Create cross-platform application icons from the approved master artwork."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/home/ubuntu/upload/pasted_file_E8J1PW_image.png")
ASSETS = ROOT / "assets"
ICONSET = ASSETS / "icons"

SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Approved icon was not found: {SOURCE}")

    ASSETS.mkdir(exist_ok=True)
    ICONSET.mkdir(parents=True, exist_ok=True)

    with Image.open(SOURCE) as image:
        master = image.convert("RGBA")
        if master.width != master.height:
            raise ValueError("The approved application icon must be square.")

        master.save(ASSETS / "rss-reader-pro.png", format="PNG", optimize=True)
        for size in SIZES:
            rendered = master.resize((size, size), Image.Resampling.LANCZOS)
            rendered.save(ICONSET / f"rss-reader-pro-{size}.png", format="PNG", optimize=True)

        master.save(
            ASSETS / "rss-reader-pro.ico",
            format="ICO",
            sizes=[(size, size) for size in SIZES if size <= master.width],
        )


if __name__ == "__main__":
    main()
