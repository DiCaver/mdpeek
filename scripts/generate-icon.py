"""Generate the multi-resolution Windows icon from the MDPeek design."""

from pathlib import Path

from PIL import Image, ImageDraw


SIZES = (16, 20, 24, 32, 48, 64, 128, 256)
ROOT = Path(__file__).resolve().parents[1]


def render(size: int) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def points(values: tuple[tuple[int, int], ...]) -> list[tuple[int, int]]:
        return [(round(x * scale), round(y * scale)) for x, y in values]

    # Small frames use a wider silhouette and omit the highlight in the pupil.
    edge = 32 if size <= 24 else 48
    fold = 58 if size <= 24 else 56
    draw.polygon(points(((edge, 16), (152, 16), (208, 72), (208, 240), (edge, 240))), fill="#1769aa")
    draw.polygon(points(((152, 16), (152, 16 + fold), (208, 72))), fill="#8fc9f2")
    draw.polygon(points(((68, 145), (88, 123), (111, 113), (128, 111), (145, 113), (168, 123), (188, 145), (168, 167), (145, 177), (128, 179), (111, 177), (88, 167))), fill="white")
    radius = 26
    draw.ellipse((round((128-radius)*scale), round((145-radius)*scale), round((128+radius)*scale), round((145+radius)*scale)), fill="#1769aa")
    if size >= 32:
        draw.ellipse((round(130*scale), round(129*scale), round(144*scale), round(143*scale)), fill="white")
    elif size <= 20:
        center_y = round(size * 0.57)
        draw.polygon(((round(size * 0.25), center_y),
                      (round(size * 0.38), center_y - 2),
                      (round(size * 0.62), center_y - 2),
                      (round(size * 0.75), center_y),
                      (round(size * 0.62), center_y + 2),
                      (round(size * 0.38), center_y + 2)), fill="white")
        center_x = size // 2
        draw.rectangle((center_x - 1, center_y - 1, center_x + 1, center_y + 1), fill="#1769aa")
    return image


def main() -> None:
    images = [render(size) for size in SIZES]
    target = ROOT / "assets" / "mdpeek.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    images[-1].save(target, format="ICO", append_images=images[:-1], sizes=[(size, size) for size in SIZES])
    print(f"Wrote {target} with sizes: {', '.join(map(str, SIZES))}")


if __name__ == "__main__":
    main()
