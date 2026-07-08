"""Generate QR code images with a gradient background."""

import io

import qrcode
from aiogram.types import BufferedInputFile
from PIL import Image, ImageDraw


def generate_qr_image(data: str) -> BufferedInputFile:
    """Generate a QR code on a light green-to-white gradient background."""
    qr = qrcode.QRCode(version=1, box_size=20, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1a1a2e", back_color="white").convert("RGBA")

    qr_w, qr_h = qr_img.size
    padding = 80
    bg_w = qr_w + padding * 2
    bg_h = qr_h + padding * 2

    bg = Image.new("RGBA", (bg_w, bg_h))
    draw = ImageDraw.Draw(bg)

    green_top = (200, 240, 200)
    white_bottom = (255, 255, 255)

    for y in range(bg_h):
        ratio = y / bg_h
        r = int(green_top[0] + (white_bottom[0] - green_top[0]) * ratio)
        g = int(green_top[1] + (white_bottom[1] - green_top[1]) * ratio)
        b = int(green_top[2] + (white_bottom[2] - green_top[2]) * ratio)
        draw.line([(0, y), (bg_w, y)], fill=(r, g, b, 255))

    qr_x = (bg_w - qr_w) // 2
    qr_y = (bg_h - qr_h) // 2
    bg.paste(qr_img, (qr_x, qr_y), qr_img)

    output = io.BytesIO()
    bg.convert("RGB").save(output, format="PNG")
    return BufferedInputFile(file=output.getvalue(), filename="qr_code.png")
