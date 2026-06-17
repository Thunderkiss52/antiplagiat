"""Image metadata handling using Pillow."""
import shutil
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifBase


def clean_image(input_path: str, output_path: str):
    img = Image.open(input_path)
    ext = Path(input_path).suffix.lower()

    if ext in ('.jpg', '.jpeg'):
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        clean.save(output_path, 'JPEG')
    else:
        img.save(output_path)


def set_image_metadata(input_path: str, output_path: str, metadata: dict):
    img = Image.open(input_path)
    ext = Path(input_path).suffix.lower()

    if ext in ('.jpg', '.jpeg'):
        exif = img.getexif()
        if 'author' in metadata:
            exif[ExifBase.Artist] = metadata['author']
        if 'title' in metadata:
            exif[ExifBase.ImageDescription] = metadata['title']
        img.save(output_path, exif=exif.tobytes())
    else:
        img.save(output_path)
