"""Video metadata handling using ffmpeg."""
import subprocess
import shutil


def clean_video(input_path: str, output_path: str):
    cmd = [
        'ffmpeg', '-i', input_path,
        '-map_metadata', '-1',
        '-c:v', 'copy', '-c:a', 'copy',
        output_path, '-y'
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def set_video_metadata(input_path: str, output_path: str, metadata: dict):
    cmd = ['ffmpeg', '-i', input_path]

    for key, value in metadata.items():
        if key == 'author':
            cmd.extend(['-metadata', f'artist={value}'])
        elif key == 'title':
            cmd.extend(['-metadata', f'title={value}'])

    cmd.extend(['-c:v', 'copy', '-c:a', 'copy', output_path, '-y'])
    subprocess.run(cmd, capture_output=True, check=True)
