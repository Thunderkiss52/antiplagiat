#!/usr/bin/env python3
"""CLI tool for cleaning/updating metadata on audio, video, and image files."""

import argparse
import sys
import os
from pathlib import Path

from utils.audio_metadata import clean_audio, set_audio_metadata
from utils.video_metadata import clean_video, set_video_metadata
from utils.image_metadata import clean_image, set_image_metadata


def get_file_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in ('.mp3', '.wav', '.flac', '.ogg', '.m4a'):
        return 'audio'
    elif ext in ('.mp4', '.webm', '.avi', '.mov', '.mkv'):
        return 'video'
    elif ext in ('.jpg', '.jpeg', '.png', '.webp', '.tiff'):
        return 'image'
    return None


def main():
    parser = argparse.ArgumentParser(description='Metadata cleaner/updater for media files')
    parser.add_argument('input', help='Input file path')
    parser.add_argument('-o', '--output', help='Output file path (default: input_clean.ext)')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean all metadata')
    parser.add_argument('--author', help='Set author/artist name')
    parser.add_argument('--title', help='Set title')
    parser.add_argument('--album', help='Set album (audio only)')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    file_type = get_file_type(args.input)
    if not file_type:
        print(f"Error: Unsupported file type: {args.input}")
        sys.exit(1)

    output = args.output
    if not output:
        p = Path(args.input)
        output = str(p.parent / f"{p.stem}_clean{p.suffix}")

    try:
        if args.clean:
            if file_type == 'audio':
                clean_audio(args.input, output)
            elif file_type == 'video':
                clean_video(args.input, output)
            elif file_type == 'image':
                clean_image(args.input, output)
            print(f"Cleaned: {output}")
        else:
            metadata = {}
            if args.author:
                metadata['author'] = args.author
            if args.title:
                metadata['title'] = args.title
            if args.album:
                metadata['album'] = args.album

            if metadata:
                if file_type == 'audio':
                    set_audio_metadata(args.input, output, metadata)
                elif file_type == 'video':
                    set_video_metadata(args.input, output, metadata)
                elif file_type == 'image':
                    set_image_metadata(args.input, output, metadata)
                print(f"Updated: {output}")
            else:
                print("No action specified. Use --clean or --author/--title/--album")
                sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
