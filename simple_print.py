#!/usr/bin/env python3
import serial
from PIL import Image, ImageOps, ImageEnhance

def load_image(image):
    # Load the image
    image = Image.open(image)
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    # Rotate the image to its longer side
    if image.width > image.height:
        image = image.rotate(90, expand=True)

    image.thumbnail((96, 284), Image.NEAREST)
    image = image.convert('1', dither=Image.FLOYDSTEINBERG)

    # Convert the image to a bit array
    bitdata = image.tobytes()
    # Pad the image to 3408 bytes, so the printer doesn't fill the rest with black.
    if len(bitdata) < 3408:
       bitdata = bitdata.ljust(3408- len(bitdata), b"\xff")
    return bitdata

def build_print_command(imagedata, density, copies):
    header = f"""SIZE 14.0 mm,40.0 mm\r
GAP 5.0 mm,0 mm\r
DIRECTION 1,1\r
DENSITY {density}\r
CLS\r
BITMAP 0,0,12,284,1,""".encode()
    footer = f"""\r\nPRINT {copies}\r\n""".encode()
    serial_data = header + imagedata + footer
    return serial_data

bitdata = load_image('test-template-2.png')
command = build_print_command(bitdata, 7, 1)

s = serial.Serial('/dev/rfcomm0',115200,timeout=3)
s.write(command)
response = s.readline()
print(response)
s.close()
