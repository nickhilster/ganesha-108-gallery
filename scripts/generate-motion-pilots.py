"""Generate two element-level motion pilots.

Each output frame is built as ``locked base + transparent motion layer``. The
source artwork is never transformed, so the named locked region stays exactly
the same in every frame. This is deliberately separate from the v1 studies,
which moved the complete raster and are retained for comparison.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "src" / "assets" / "artworks"
OUTPUT_DIR = ROOT / "public" / "motion-pilots-v2"
SIZE = 768
FRAME_COUNT = 12
FPS = 24
FRAME_DURATION_MS = round(1000 / FPS)


def load_base(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    image.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (12, 10, 20, 255))
    canvas.alpha_composite(image, ((SIZE - image.width) // 2, (SIZE - image.height) // 2))
    return canvas


def apply_lock_mask(layer: Image.Image, lock_mask: Image.Image) -> Image.Image:
    """Remove overlay alpha from the central region that must remain locked."""

    allowed = ImageChops.invert(lock_mask)
    alpha = ImageChops.multiply(layer.getchannel("A"), allowed)
    layer.putalpha(alpha)
    return layer


def add_soft_glow(target: Image.Image, source: Image.Image, radius: int, opacity: int) -> None:
    glow = source.filter(ImageFilter.GaussianBlur(radius))
    glow_alpha = glow.getchannel("A").point(lambda value: value * opacity // 255)
    glow.putalpha(glow_alpha)
    target.alpha_composite(glow)


def ellipse_mask(box: tuple[int, int, int, int]) -> Image.Image:
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    return mask


def sound_wave_layer(frame_index: int, lock_mask: Image.Image) -> Image.Image:
    phase = 2 * math.pi * frame_index / FRAME_COUNT
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ink = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ink)
    center = (384, 395)

    # A few outer rings breathe in place. The artwork and Ganesha remain the
    # base layer; only these selected wave accents receive motion.
    for index, radius in enumerate((232, 284, 336)):
        breathe = 11 * math.sin(phase + index * 0.7)
        x_radius = int(radius + breathe)
        y_radius = int((radius * 0.84) + breathe * 0.65)
        box = (
            center[0] - x_radius,
            center[1] - y_radius,
            center[0] + x_radius,
            center[1] + y_radius,
        )
        color = (246, 191, 86, 126 if index == 0 else 96)
        draw.ellipse(box, outline=color, width=3 if index == 0 else 2)

        # A moving highlight segment makes the ring motion readable without
        # rotating or warping the source image.
        start = -25 + math.degrees(phase) + index * 92
        draw.arc(box, start=start, end=start + 48, fill=(136, 211, 255, 188), width=4)

    # Sparse orbiting sparks stay outside the locked Ganesha region.
    for index in range(14):
        angle = (2 * math.pi * index / 14) + phase * 0.42
        radius = 300 + 16 * math.sin(phase * 1.5 + index)
        x = int(center[0] + math.cos(angle) * radius)
        y = int(center[1] + math.sin(angle) * radius * 0.77)
        size = 2 if index % 3 else 3
        draw.ellipse((x - size, y - size, x + size, y + size), fill=(255, 222, 139, 170))

    apply_lock_mask(ink, lock_mask)
    add_soft_glow(layer, ink, radius=9, opacity=90)
    layer.alpha_composite(ink)
    # The blur can spread beyond the ink's original pixels, so enforce the
    # boundary once more after compositing the glow.
    return apply_lock_mask(layer, lock_mask)


def rain_layer(frame_index: int, lock_mask: Image.Image) -> Image.Image:
    phase = frame_index / FRAME_COUNT
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ink = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ink)

    # Selected edge drops travel down the glass. The modulo makes the motion
    # periodic, while the central figure and bokeh stay pixel-locked.
    drops = (
        (48, 86, 26, 2),
        (104, 410, 38, 2),
        (151, 224, 20, 2),
        (618, 144, 31, 2),
        (674, 492, 42, 2),
        (721, 286, 24, 2),
    )
    for index, (x, seed, length, width) in enumerate(drops):
        y = 28 + ((seed + phase * 730) % 710)
        alpha = 144 + int(30 * math.sin(2 * math.pi * phase + index))
        color = (186, 225, 255, alpha)
        draw.line((x, y, x - 3, y + length), fill=color, width=width)
        draw.ellipse((x - 4, y - 4, x + 2, y + 3), fill=(226, 247, 255, min(210, alpha + 35)))

    # A pair of slim reflection bands slide along the outer glass edges.
    for index, x in enumerate((72, 700)):
        travel = int(((phase + index * 0.5) % 1) * 470)
        y = 120 + travel
        draw.line((x, y, x + (3 if index else -3), y + 128), fill=(143, 201, 255, 86), width=4)

    apply_lock_mask(ink, lock_mask)
    add_soft_glow(layer, ink, radius=7, opacity=100)
    layer.alpha_composite(ink)
    return apply_lock_mask(layer, lock_mask)


PILOTS = (
    {
        "id": "066",
        "title": "Ganesha as Sound Waves",
        "source": SOURCE_DIR / "066-ganesha-as-sound-waves.webp",
        "layer": sound_wave_layer,
        "locked": "Ganesha body, face, hands, and inner glow",
        "animated": "outer sound-wave rings and sparse orbiting particles",
        "lock_box": (160, 90, 608, 720),
    },
    {
        "id": "080",
        "title": "Ganesha as Glass + Rain",
        "source": SOURCE_DIR / "080-ganesha-as-glass-rain.webp",
        "layer": rain_layer,
        "locked": "Ganesha and the surrounding city bokeh",
        "animated": "selected raindrops, rivulets, and edge-glass highlights",
        "lock_box": (175, 125, 593, 700),
    },
)


def save_animation(frames: list[Image.Image], path: Path, *, lossless: bool) -> None:
    frames[0].save(
        path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        lossless=lossless,
        method=6,
    )


def locked_region_matches(image: Image.Image, base: Image.Image, lock_mask: Image.Image) -> bool:
    difference = ImageChops.difference(image.convert("RGBA"), base).convert("L")
    return ImageChops.multiply(difference, lock_mask).getbbox() is None


def decoded_file_matches(path: Path, base: Image.Image, lock_mask: Image.Image) -> bool:
    with Image.open(path) as image:
        return locked_region_matches(image, base, lock_mask)


def make_pilot(pilot: dict) -> dict:
    pilot_dir = OUTPUT_DIR / pilot["id"]
    frames_dir = pilot_dir / "frames"
    overlays_dir = pilot_dir / "overlays"
    frames_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)

    base = load_base(pilot["source"])
    lock_mask = ellipse_mask(pilot["lock_box"])
    base_hash = hashlib.sha256(base.tobytes()).hexdigest()
    base.save(pilot_dir / "source.webp", format="WEBP", lossless=True, method=6)
    # The mask is useful during review: white is the region guaranteed to be
    # unchanged, and it also documents the pilot's layer boundary.
    lock_mask.save(pilot_dir / "locked-region.webp", format="WEBP", lossless=True, method=6)

    frames: list[Image.Image] = []
    overlays: list[Image.Image] = []
    locked_region_identical = True
    frame_paths: list[Path] = []
    for frame_index in range(FRAME_COUNT):
        overlay = pilot["layer"](frame_index, lock_mask)
        output = Image.alpha_composite(base, overlay)
        frames.append(output)
        overlays.append(overlay)
        frame_name = f"frame-{frame_index + 1:02d}.webp"
        frame_path = frames_dir / frame_name
        output.save(frame_path, format="WEBP", lossless=True, method=6)
        frame_paths.append(frame_path)
        overlay.save(overlays_dir / frame_name, format="WEBP", lossless=True, method=6)

        difference = ImageChops.difference(output, base).convert("L")
        locked_difference = ImageChops.multiply(difference, lock_mask)
        locked_region_identical = locked_region_identical and locked_difference.getbbox() is None

    save_animation(frames, pilot_dir / "loop.webp", lossless=True)
    save_animation(overlays, pilot_dir / "overlay-loop.webp", lossless=True)

    # Reopen encoded assets before writing metadata. This catches a future
    # codec or quality change that could invalidate the layer boundary after
    # the in-memory check above.
    serialized_frames_locked = all(decoded_file_matches(path, base, lock_mask) for path in frame_paths)
    loop_path = pilot_dir / "loop.webp"
    with Image.open(loop_path) as loop:
        encoded_loop_frames = getattr(loop, "n_frames", 1)
        serialized_loop_locked = encoded_loop_frames == FRAME_COUNT
        for frame_index in range(encoded_loop_frames):
            loop.seek(frame_index)
            serialized_loop_locked = serialized_loop_locked and locked_region_matches(loop, base, lock_mask)
    serialized_locked_region_identical = serialized_frames_locked and serialized_loop_locked
    if not serialized_locked_region_identical:
        raise RuntimeError(f"Encoded lock check failed for pilot {pilot['id']}")
    locked_region_identical = locked_region_identical and serialized_locked_region_identical

    return {
        "id": pilot["id"],
        "title": pilot["title"],
        "frames": FRAME_COUNT,
        "fps": FPS,
        "durationSeconds": FRAME_COUNT / FPS,
        "size": [SIZE, SIZE],
        "baseLocked": locked_region_identical,
        "lockedRegionIdentical": locked_region_identical,
        "serializedLockedRegionIdentical": serialized_locked_region_identical,
        "encodedLoopFrames": encoded_loop_frames,
        "frameDurationMs": FRAME_DURATION_MS,
        "encodedDurationMs": FRAME_DURATION_MS * FRAME_COUNT,
        "baseSha256": base_hash,
        "lockedElements": pilot["locked"],
        "animatedElements": pilot["animated"],
        "source": pilot["source"].name,
        "reviewFiles": {
            "source": "source.webp",
            "loop": "loop.webp",
            "overlayLoop": "overlay-loop.webp",
            "lockedRegion": "locked-region.webp",
        },
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": "v2-element-level-pilot",
        "contract": {
            "baseLayer": "pixel-locked source artwork",
            "motionLayer": "transparent overlays only",
            "frames": FRAME_COUNT,
            "fps": FPS,
            "durationSeconds": FRAME_COUNT / FPS,
            "loop": "frame 12 to frame 1",
        },
        "pilots": [make_pilot(pilot) for pilot in PILOTS],
    }
    (OUTPUT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
