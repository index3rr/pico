#!/usr/bin/env python3
"""Capture a webcam frame after allowing the camera to warm up."""
import argparse
from fractions import Fraction
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='/dev/video0')
    parser.add_argument('--warmup', type=int, default=60)
    parser.add_argument('--size', default='640x480')
    parser.add_argument('--fps', default='5', help='Camera capture rate, e.g. 5 or 15/2 (default: 5)')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent / '.thonny/webcam.jpg')
    args = parser.parse_args()
    if not 1 <= args.warmup <= 60:
        parser.error('--warmup must be between 1 and 60 seconds')
    try:
        rate = Fraction(args.fps)
    except (ValueError, ZeroDivisionError):
        parser.error('--fps must be a positive number or fraction')
    if not 0 < rate <= 60:
        parser.error('--fps must be greater than 0 and at most 60')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'v4l2',
                    '-input_format', 'mjpeg', '-framerate', str(rate),
                    '-video_size', args.size, '-i', args.device,
                    '-t', str(args.warmup), '-vf', 'fps=1', '-update', '1', '-y',
                    str(args.output)], check=True)
    print(args.output)


if __name__ == '__main__':
    main()
