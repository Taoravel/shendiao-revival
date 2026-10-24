"""Replay reported UI colors and compare a pristine atlas, without game edits."""
from pathlib import Path
import hashlib
import io
import json
import numpy as np
from PIL import Image
from pfs import PfsArchive

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'revival/evidence'
SCREENSHOT = Path('C:/Users/11950/AppData/Local/Temp/codex-clipboard-24691c12-391e-4069-8713-d22571270930.png')


def main():
    screenshot = Image.open(SCREENSHOT).convert('RGB').resize((1792, 1388))
    points = [(250,399),(255,589),(246,796),(251,1001),(253,1187)]
    colors = [screenshot.getpixel(p) for p in points]
    blue = sum(b > r + 15 for r,g,b in colors)
    print('BLUE_SKIN_REPLAY', blue, '/5', colors)
    assert blue == 5, 'The saved screenshot no longer reproduces reported blue skin'
    archive = PfsArchive(ROOT / 'artres/ui.pfs')
    raw = archive.read('imagesets/maincontrol20.tga')
    atlas = Image.open(io.BytesIO(raw)).convert('RGBA')
    atlas.save(OUT / 'maincontrol20-original.png')
    # Female top slot uses Yunxi, atlas Head9, independently identified visually.
    portrait = atlas.crop((704,528,904,636))
    screen = np.asarray(screenshot, dtype=np.float32)
    best = None
    # Register with sum(RGB), which is invariant to an R/B channel permutation.
    for width in range(345, 361):
        height = round(width * 108 / 200)
        candidate = np.asarray(portrait.resize((width,height), Image.Resampling.BILINEAR), dtype=np.float32)
        mask = candidate[:,:,3] > 254
        # Avoid hover glow and texture borders; use opaque portrait center.
        mask[:20] = False
        mask[-10:] = False
        source = candidate[:,:,:3]
        source_sum = source.sum(axis=2)
        for x in range(59,75):
            for y in range(285,302):
                target = screen[y:y+height,x:x+width]
                score = float(np.mean((target.sum(axis=2)[mask] - source_sum[mask]) ** 2))
                if best is None or score < best[0]:
                    direct = float(np.mean((target[mask] - source[mask]) ** 2))
                    swapped = float(np.mean((target[mask] - source[:,:,::-1][mask]) ** 2))
                    best = score, x, y, width, height, direct, swapped, int(mask.sum())
    score,x,y,width,height,direct,swapped,count = best
    evidence = {'screenshot_sha256': hashlib.sha256(SCREENSHOT.read_bytes()).hexdigest(),
                'archive_entry': 'artres/ui.pfs:imagesets/maincontrol20.tga',
                'tga_sha256': hashlib.sha256(raw).hexdigest(),
                'skin_samples': colors, 'blue_skin_samples': blue,
                'portrait': 'MainControl20/Head9', 'atlas_rect': [704,528,200,108],
                'registered_screenshot_rect': [x,y,width,height],
                'opaque_pixels_compared': count, 'registration_rgb_sum_mse': score,
                'original_rgb_mse': direct, 'red_blue_permuted_mse': swapped,
                'direct_to_swapped_error_ratio': direct/swapped}
    (OUT / 'color-diagnosis.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__':
    main()
