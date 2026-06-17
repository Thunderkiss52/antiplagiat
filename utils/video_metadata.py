"""Video metadata handling using ffmpeg."""
import subprocess


def clean_video(input_path: str, output_path: str):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-map_metadata', '-1',
        '-c:v', 'copy', '-c:a', 'copy',
        '-map', '0',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-map_metadata', '-1',
            '-c:v', 'libx264', '-crf', '18', '-preset', 'slow',
            '-c:a', 'aac', '-b:a', '192k',
            '-map', '0',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)


def set_video_metadata(input_path: str, output_path: str, metadata: dict):
    meta_args = []
    for key, value in metadata.items():
        if key == 'author':
            meta_args.extend(['-metadata', f'artist={value}'])
        elif key == 'title':
            meta_args.extend(['-metadata', f'title={value}'])

    cmd = ['ffmpeg', '-y', '-i', input_path] + meta_args + [
        '-c:v', 'copy', '-c:a', 'copy',
        '-map', '0',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        cmd = ['ffmpeg', '-y', '-i', input_path] + meta_args + [
            '-c:v', 'libx264', '-crf', '18', '-preset', 'slow',
            '-c:a', 'aac', '-b:a', '192k',
            '-map', '0',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
