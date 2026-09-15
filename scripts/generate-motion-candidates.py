from __future__ import annotations

import json
import math
import os
import shutil
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "src" / "assets" / "artworks"
OUTPUT_DIR = ROOT / "public" / "motion-candidates-v1"
ARTWORKS = json.loads((ROOT / "src" / "data" / "artworks.json").read_text(encoding="utf-8"))
ARTWORK_BY_ID = {item["id"]: item for item in ARTWORKS}

# These candidates are the 18 motion studies selected from the full 108-image audit.
# Each recipe uses a small, reversible amplitude so frame 12 joins frame 1 cleanly.
CANDIDATES = OrderedDict(
    [
        ("108", {"effect": "optical phase", "treatment": "Low-amplitude moire phase shift and radial breathing."}),
        ("101", {"effect": "refraction", "treatment": "Cyclic water ripple and gentle refraction."}),
        ("086", {"effect": "smoke", "treatment": "Smoke tendrils curl and return with a soft opacity breath."}),
        ("066", {"effect": "sound pulse", "treatment": "Concentric rings pulse outward and inward."}),
        ("064", {"effect": "fire", "treatment": "Flame brightness, ember drift, and restrained smoke movement."}),
        ("078", {"effect": "ocean current", "treatment": "Opposing current flow with bioluminescent pulse layers."}),
        ("080", {"effect": "rain refraction", "treatment": "Droplets descend and merge while highlights shimmer."}),
        ("107", {"effect": "impossible parallax", "treatment": "Tiny depth shift along the impossible architecture."}),
        ("104", {"effect": "vanishing grid", "treatment": "Grid emphasis and ghost-dot breathing around stable linework."}),
        ("057", {"effect": "helix", "treatment": "DNA twist with restrained base-pair shimmer."}),
        ("052", {"effect": "black hole", "treatment": "Accretion-ring rotation and event-horizon glow."}),
        ("087", {"effect": "neural circuit", "treatment": "Circuit pulses and neural-light flickers."}),
        ("004", {"effect": "four dimensions", "treatment": "Translucent geometric layers shift in depth."}),
        ("090", {"effect": "waterfall", "treatment": "Continuous waterfall and mist movement while the negative-space figure stays legible."}),
        ("100", {"effect": "mirage", "treatment": "Heat shimmer and reflected-form ripple."}),
        ("003", {"effect": "big bang", "treatment": "Controlled radial expansion with drifting particles."}),
        ("089", {"effect": "traffic swarm", "treatment": "Headlights flow through the road network and return symmetrically."}),
        ("110", {"effect": "psychedelic portals", "treatment": "Checkerboard, portals, and layered parallax breathe together."}),
    ]
)

FPS = 24
FRAME_COUNT = 12
SIZE = 768
BACKGROUND = (12, 10, 20, 255)


def resize_square(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    if image.size != (SIZE, SIZE):
        image.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), BACKGROUND)
        canvas.alpha_composite(image, ((SIZE - image.width) // 2, (SIZE - image.height) // 2))
        image = canvas
    return image


def transform_affine(image: Image.Image, x_shift: float = 0, y_shift: float = 0, angle: float = 0) -> Image.Image:
    if angle:
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=BACKGROUND)
    if x_shift or y_shift:
        image = image.transform(
            image.size,
            Image.Transform.AFFINE,
            (1, 0, -x_shift, 0, 1, -y_shift),
            resample=Image.Resampling.BICUBIC,
            fillcolor=BACKGROUND,
        )
    return image


def zoom_center(image: Image.Image, amount: float) -> Image.Image:
    if abs(amount) < 1e-5:
        return image
    width, height = image.size
    factor = 1 + amount
    resized = image.resize((max(2, round(width * factor)), max(2, round(height * factor))), Image.Resampling.BICUBIC)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    cropped = resized.crop((left, top, left + width, top + height))
    if cropped.size != image.size:
        cropped = cropped.resize(image.size, Image.Resampling.BICUBIC)
    return cropped


def wave(image: Image.Image, amount: float, period: float, phase: float, vertical: bool = False) -> Image.Image:
    array = np.asarray(image.convert("RGBA"))
    height, width = array.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    if vertical:
        xx = xx + amount * np.sin((yy / period) * (2 * math.pi) + phase)
    else:
        yy = yy + amount * np.sin((xx / period) * (2 * math.pi) + phase)
    map_x = np.clip(xx, 0, width - 1)
    map_y = np.clip(yy, 0, height - 1)
    warped = cv2.remap(array, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    return Image.fromarray(warped, "RGBA")


def brightness(image: Image.Image, amount: float) -> Image.Image:
    return ImageEnhance.Brightness(image).enhance(max(0.1, 1 + amount))


def color(image: Image.Image, amount: float) -> Image.Image:
    return ImageEnhance.Color(image).enhance(max(0.1, 1 + amount))


def contrast(image: Image.Image, amount: float) -> Image.Image:
    return ImageEnhance.Contrast(image).enhance(max(0.1, 1 + amount))


def hue_shift(image: Image.Image, degrees: float) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA"))
    rgb = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2HSV)
    rgb[:, :, 0] = (rgb[:, :, 0].astype(np.int16) + round(degrees / 2)) % 180
    shifted = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_HSV2RGB)
    return Image.fromarray(np.dstack([shifted, rgba[:, :, 3]]), "RGBA")


def glow(image: Image.Image, amount: float) -> Image.Image:
    blurred = image.filter(ImageFilter.GaussianBlur(12))
    return Image.blend(image, blurred, max(0, min(0.35, amount)))


def apply_effect(image: Image.Image, effect: str, phase: float) -> Image.Image:
    # phase is a cosine sample, so the first/last transition has a gentle slope.
    if effect == "optical phase":
        image = zoom_center(image, 0.018 * phase)
        image = wave(image, 2.2 * phase, 92, phase * math.pi, vertical=True)
        image = contrast(image, 0.025 * phase)
    elif effect == "refraction":
        image = wave(image, 5.5 * phase, 82, phase * math.pi)
        image = wave(image, 2.5 * phase, 130, phase * math.pi + 1.2, vertical=True)
        image = brightness(image, 0.025 * phase)
    elif effect == "smoke":
        image = wave(image, 7 * phase, 145, phase * math.pi + 0.8)
        image = transform_affine(image, 0, 4 * phase, 0.35 * phase)
        image = brightness(image, 0.04 * phase)
    elif effect == "sound pulse":
        image = zoom_center(image, 0.016 * phase)
        image = brightness(image, 0.055 * phase)
        image = glow(image, 0.16 + 0.05 * phase)
    elif effect == "fire":
        image = wave(image, 4 * phase, 56, phase * math.pi + 0.5)
        image = brightness(image, 0.075 * phase)
        image = color(image, 0.08 * phase)
        image = hue_shift(image, 1.2 * phase)
    elif effect == "ocean current":
        image = wave(image, 5.5 * phase, 105, phase * math.pi)
        image = wave(image, 3.0 * phase, 170, phase * math.pi + 1.8, vertical=True)
        image = brightness(image, 0.045 * phase)
        image = hue_shift(image, 2.0 * phase)
    elif effect == "rain refraction":
        image = wave(image, 3.4 * phase, 74, phase * math.pi)
        image = transform_affine(image, 0, 4.5 * phase, 0)
        image = brightness(image, 0.04 * phase)
    elif effect == "impossible parallax":
        image = zoom_center(image, 0.012 * phase)
        image = transform_affine(image, 2.2 * phase, 1.2 * phase, 0.8 * phase)
        image = brightness(image, 0.025 * phase)
    elif effect == "vanishing grid":
        image = zoom_center(image, 0.01 * phase)
        image = transform_affine(image, 1.3 * phase, 0, 0.35 * phase)
        image = contrast(image, 0.035 * phase)
        image = brightness(image, 0.025 * phase)
    elif effect == "helix":
        image = wave(image, 4.0 * phase, 96, phase * math.pi)
        image = transform_affine(image, 0, 0, 1.1 * phase)
        image = brightness(image, 0.035 * phase)
    elif effect == "black hole":
        image = transform_affine(image, 0, 0, 1.1 * phase)
        image = zoom_center(image, 0.018 * phase)
        image = brightness(image, 0.05 * phase)
        image = glow(image, 0.14 + 0.06 * phase)
    elif effect == "neural circuit":
        image = wave(image, 3.0 * phase, 66, phase * math.pi)
        image = brightness(image, 0.065 * phase)
        image = hue_shift(image, 2.5 * phase)
    elif effect == "four dimensions":
        image = zoom_center(image, 0.016 * phase)
        image = transform_affine(image, 2.5 * phase, 0.8 * phase, 0.7 * phase)
        image = brightness(image, 0.035 * phase)
    elif effect == "waterfall":
        image = wave(image, 4.6 * phase, 64, phase * math.pi, vertical=True)
        image = transform_affine(image, 0, 4.0 * phase, 0)
        image = brightness(image, 0.03 * phase)
    elif effect == "mirage":
        image = wave(image, 6.5 * phase, 58, phase * math.pi)
        image = wave(image, 2.3 * phase, 120, phase * math.pi + 1.4, vertical=True)
        image = brightness(image, 0.035 * phase)
    elif effect == "big bang":
        image = zoom_center(image, 0.02 * phase)
        image = wave(image, 2.0 * phase, 120, phase * math.pi)
        image = brightness(image, 0.05 * phase)
        image = glow(image, 0.12 + 0.05 * phase)
    elif effect == "traffic swarm":
        image = wave(image, 4.0 * phase, 42, phase * math.pi)
        image = transform_affine(image, 3.0 * phase, 0, 0)
        image = brightness(image, 0.045 * phase)
    elif effect == "psychedelic portals":
        image = zoom_center(image, 0.02 * phase)
        image = transform_affine(image, 1.8 * phase, 1.2 * phase, 0.8 * phase)
        image = hue_shift(image, 3.0 * phase)
        image = brightness(image, 0.04 * phase)
    return image


def source_for(item: dict) -> Path:
    path = SOURCE_DIR / item["file"]
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for candidate_id, recipe in CANDIDATES.items():
        artwork = ARTWORK_BY_ID[candidate_id]
        candidate_dir = OUTPUT_DIR / candidate_id
        frames_dir = candidate_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for old in frames_dir.glob("frame-*.webp"):
            old.unlink()
        source = resize_square(Image.open(source_for(artwork)))
        frames = []
        for index in range(FRAME_COUNT):
            phase = math.cos((2 * math.pi * index) / FRAME_COUNT)
            frame = apply_effect(source.copy(), recipe["effect"], phase).convert("RGBA")
            frames.append(frame)
            frame.save(frames_dir / f"frame-{index + 1:02d}.webp", "WEBP", quality=86, method=6)
        loop_path = candidate_dir / "loop.webp"
        frames[0].save(
            loop_path,
            "WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=round(1000 / FPS),
            loop=0,
            quality=84,
            method=6,
        )
        manifest.append(
            {
                "id": candidate_id,
                "title": artwork["title"],
                "slug": artwork["slug"],
                "groupSlug": artwork["groupSlug"],
                "source": artwork["file"],
                "effect": recipe["effect"],
                "treatment": recipe["treatment"],
                "frames": FRAME_COUNT,
                "fps": FPS,
                "durationSeconds": FRAME_COUNT / FPS,
                "loop": f"{candidate_id}/loop.webp",
                "frameDirectory": f"{candidate_id}/frames/",
            }
        )
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest)} candidates x {FRAME_COUNT} frames at {SIZE}px: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
