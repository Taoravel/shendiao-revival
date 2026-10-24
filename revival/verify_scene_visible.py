"""Fail on the exact black-world symptom in a current screenshot.

Samples the upper central playfield, excluding HUD and lower/right dialogs.
This is a visual signal, not a claim about the cause of missing rendering.
"""
import argparse
import json
from pathlib import Path
from PIL import Image


def measure(path):
    picture = Image.open(path).convert('RGB')
    w, h = picture.size
    box = (int(w*.22), int(h*.16), int(w*.68), int(h*.39))
    pixels = list(picture.crop(box).get_flattened_data())
    black = sum(max(p) <= 3 for p in pixels)/len(pixels)
    result = dict(image=str(Path(path).resolve()), dimensions=[w,h], region=box,
                  black_ratio=black, black_world=black >= .98)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('image')
    parser.add_argument('--report')
    args = parser.parse_args(); result = measure(args.image)
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result)); raise SystemExit(1 if result['black_world'] else 0)
