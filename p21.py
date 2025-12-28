#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Optional

from matplotlib import image
import serial
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont

# Printer / label geometry constants
LABEL_WIDTH_PX = 284
LABEL_HEIGHT_PX = 96
ROTATED_WIDTH_PX = LABEL_HEIGHT_PX      # 96
ROTATED_HEIGHT_PX = LABEL_WIDTH_PX      # 284
BYTES_PER_ROW = ROTATED_WIDTH_PX // 8   # 96 px / 8 = 12 bytes
EXPECTED_BYTES = ROTATED_HEIGHT_PX * BYTES_PER_ROW  # 284 * 12 = 3408

DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DEFAULT_FONT_SIZE = 30
DEFAULT_DENSITY = 7
DEFAULT_COPIES = 1
DEFAULT_DEVICE = "/dev/rfcomm0"

def load_image(image_path, preview=False, threshold=180):
    """
    Load an image, normalize it to a clean 1-bit 96×284 bitmap for the printer,
    with minimal dithering artefacts.
    """
    img = Image.open(image_path)

    # Work in grayscale
    img = ImageOps.grayscale(img)

    # Rotate so the longer side is vertical (to match 96×284)
    if img.width > img.height:
        img = img.rotate(90, expand=True, fillcolor=255)

    img.thumbnail((ROTATED_WIDTH_PX, ROTATED_HEIGHT_PX), Image.LANCZOS)
    img = img.point(lambda p: 0 if p < threshold else 255, mode="1")

    if preview:
        img.rotate(-90, expand=True, fillcolor=255).show(title="Image label (printer orientation 96×284)")

    bitdata = img.tobytes()
    if len(bitdata) < EXPECTED_BYTES:
        bitdata = bitdata.ljust(EXPECTED_BYTES, b"\xff")
    elif len(bitdata) > EXPECTED_BYTES:
        bitdata = bitdata[:EXPECTED_BYTES]

    return bitdata


def render_text_label(
    text: str,
    width: int = LABEL_WIDTH_PX,
    height: int = LABEL_HEIGHT_PX,
    font_path: str = DEFAULT_FONT_PATH,
    font_size: int = DEFAULT_FONT_SIZE,
    preview: bool = False,
) -> bytes:
    """
    Render centered bold text into a 284x96 image,
    rotate to 96x284 for the printer, and return packed bitmap bytes.

    In preview mode, shows only the pre-rotation (readable) 284x96 image.
    """
    # Work in label orientation (human-readable)
    img = Image.new("1", (width, height), 1)  # white background
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (width - text_w) // 2 - bbox[0]
    y = (height - text_h) // 2 - bbox[1]

    draw.text((x, y), text, font=font, fill=0)  # black text

    if preview:
        img.show(title="Text label (readable orientation)")

    # Rotate 90° clockwise to get 96x284 for the printer
    rotated = img.rotate(-90, expand=True)

    if rotated.size != (ROTATED_WIDTH_PX, ROTATED_HEIGHT_PX):
        rotated = rotated.resize((ROTATED_WIDTH_PX, ROTATED_HEIGHT_PX), Image.NEAREST)

    bitdata = rotated.tobytes()
    if len(bitdata) < EXPECTED_BYTES:
        bitdata = bitdata.ljust(EXPECTED_BYTES, b"\xff")
    elif len(bitdata) > EXPECTED_BYTES:
        bitdata = bitdata[:EXPECTED_BYTES]

    return bitdata


def build_print_command(imagedata: bytes, density: int, copies: int) -> bytes:
    """
    Build the raw command stream for the printer using BITMAP.
    """
    header = (
        f"SIZE 14.0 mm,40.0 mm\r\n"
        f"GAP 5.0 mm,0 mm\r\n"
        f"DIRECTION 1,1\r\n"
        f"DENSITY {density}\r\n"
        f"CLS\r\n"
        f"BITMAP 0,0,{BYTES_PER_ROW},{ROTATED_HEIGHT_PX},0,"
    ).encode()

    footer = f"\r\nPRINT {copies}\r\n".encode()
    
    return header + imagedata + footer


def send_to_printer(device: str, payload: bytes) -> Optional[bytes]:
    """
    Open the serial device, send payload, and read a single response line.
    """
    try:
        with serial.Serial(device, 115200, timeout=3) as s:
            s.write(payload)
            return s.readline()
    except serial.SerialException as exc:
        print(f"Serial error: {exc}")
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print image or text label to a P21-compatible printer."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-i",
        "--image",
        type=Path,
        help="Path to an image file to print.",
    )
    group.add_argument(
        "-t",
        "--text",
        type=str,
        help="Text to render as a centered label.",
    )

    parser.add_argument(
        "--font-size",
        type=int,
        default=DEFAULT_FONT_SIZE,
        help=f"Font size for text mode (default: {DEFAULT_FONT_SIZE}).",
    )
    parser.add_argument(
        "--font-path",
        type=str,
        default=DEFAULT_FONT_PATH,
        help=f"Path to a TTF font (default: {DEFAULT_FONT_PATH}).",
    )
    parser.add_argument(
        "--density",
        type=int,
        default=DEFAULT_DENSITY,
        help=f"Print density (default: {DEFAULT_DENSITY}).",
    )
    parser.add_argument(
        "--copies",
        type=int,
        default=DEFAULT_COPIES,
        help=f"Number of copies to print (default: {DEFAULT_COPIES}).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=DEFAULT_DEVICE,
        help=f"Serial device for printer (default: {DEFAULT_DEVICE}).",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help=(
            "Preview the label only and exit. "
            "Nothing is sent to the printer."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.preview_only:
        # Preview path: show only pre-rotated / human-readable images, no printing.
        if args.image:
            load_image(str(args.image), preview=True)
        else:
            render_text_label(
                text=args.text,
                font_path=args.font_path,
                font_size=args.font_size,
                preview=True,
            )
        return

    # Normal print path, no preview.
    if args.image:
        bitdata = load_image(str(args.image), preview=False)
    else:
        bitdata = render_text_label(
            text=args.text,
            font_path=args.font_path,
            font_size=args.font_size,
            preview=False,
        )

    command = build_print_command(bitdata, args.density, args.copies)
    response = send_to_printer(args.device, command)

    if response is not None:
        print(response)


if __name__ == "__main__":
    main()
