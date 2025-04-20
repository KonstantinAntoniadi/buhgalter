import cairosvg
from PIL import Image
from io import BytesIO


def svg_to_png(svg, path_out):
    output = BytesIO()
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=output)
    output.seek(0)
    image = Image.open(output)

    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(
        image, mask=image.split()[3]
    )
    background.save(path_out, "PNG")

    output.close()
    image.close()
