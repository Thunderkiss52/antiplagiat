"""Audio metadata handling using mutagen."""
import shutil
from pathlib import Path

from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC


def get_audio_handler(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == '.mp3':
        return MP3(file_path)
    elif ext == '.m4a':
        return MP4(file_path)
    elif ext == '.ogg':
        return OggVorbis(file_path)
    elif ext == '.flac':
        return FLAC(file_path)
    return None


def clean_audio(input_path: str, output_path: str):
    shutil.copy2(input_path, output_path)
    audio = get_audio_handler(output_path)
    if audio:
        audio.delete()
        audio.save()


def set_audio_metadata(input_path: str, output_path: str, metadata: dict):
    shutil.copy2(input_path, output_path)
    audio = get_audio_handler(output_path)
    if not audio:
        return

    ext = Path(input_path).suffix.lower()

    if 'author' in metadata:
        if ext == '.mp3':
            audio['TPE1'] = metadata['author']
        elif ext == '.m4a':
            audio['\xa9ART'] = metadata['author']
        elif ext in ('.ogg', '.flac'):
            audio['artist'] = metadata['author']

    if 'title' in metadata:
        if ext == '.mp3':
            audio['TIT2'] = metadata['title']
        elif ext == '.m4a':
            audio['\xa9nam'] = metadata['title']
        elif ext in ('.ogg', '.flac'):
            audio['title'] = metadata['title']

    if 'album' in metadata:
        if ext == '.mp3':
            audio['TALB'] = metadata['album']
        elif ext == '.m4a':
            audio['\xa9alb'] = metadata['album']
        elif ext in ('.ogg', '.flac'):
            audio['album'] = metadata['album']

    audio.save()
