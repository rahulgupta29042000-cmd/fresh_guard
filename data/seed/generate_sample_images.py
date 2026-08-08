"""Generates deterministic sample product photos used by the inspection
demo ("Use Sample Image" quick-pick in the UI) and by seed.py for
historical inspection records. Not real product photography — synthetic
images with per-pixel texture noise (so they read as "in focus" to the
real image-quality checks) and, where relevant, a darkened elliptical
blotch standing in for a visible defect (bruise/crack/crush mark).

Run: python3 data/seed/generate_sample_images.py
"""
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(__file__)
OUT_DIR = os.path.join(os.path.dirname(HERE), "images", "samples")
SIZE = 400
RNG = np.random.default_rng(11)


def make_image(base_color, blotch=None, noise_sigma=12.0, brightness_scale=1.0):
    arr = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    arr[:, :] = base_color
    noise = RNG.normal(0, noise_sigma, arr.shape)
    arr = arr + noise

    if blotch:
        cy, cx = SIZE / 2, SIZE / 2
        yy, xx = np.mgrid[0:SIZE, 0:SIZE]
        mask = ((xx - cx) ** 2 + (yy - cy) ** 2) <= blotch["radius"] ** 2
        arr[mask] = arr[mask] * blotch["darken"] + np.array(blotch.get("tint", (0, 0, 0))) * (1 - blotch["darken"])

    arr = arr * brightness_scale
    arr = np.clip(arr, 0, 255).astype("uint8")
    return Image.fromarray(arr, "RGB")


def radius_for_ratio(ratio: float) -> float:
    return math.sqrt(ratio * SIZE * SIZE / math.pi)


SAMPLES = [
    {
        "key": "tomato_good",
        "label": "Tomato — no visible defect",
        "product_hint": "tomato",
        "image": make_image((205, 60, 42)),
    },
    {
        "key": "tomato_bruised_review",
        "label": "Tomato — possible bruising",
        "product_hint": "tomato",
        "image": make_image((205, 60, 42), blotch={"radius": radius_for_ratio(0.055), "darken": 0.42, "tint": (60, 30, 20)}),
    },
    {
        "key": "tomato_severe_reject",
        "label": "Tomato — severe visible damage",
        "product_hint": "tomato",
        "image": make_image((205, 60, 42), blotch={"radius": radius_for_ratio(0.16), "darken": 0.35, "tint": (50, 25, 15)}),
    },
    {
        "key": "chips_good",
        "label": "Chips packet — intact",
        "product_hint": "chips",
        "image": make_image((190, 150, 60)),
    },
    {
        "key": "chips_crushed_reject",
        "label": "Chips packet — crushed",
        "product_hint": "chips",
        "image": make_image((190, 150, 60), blotch={"radius": radius_for_ratio(0.15), "darken": 0.4, "tint": (70, 60, 30)}),
    },
    {
        "key": "glass_good",
        "label": "Glass sauce bottle — intact",
        "product_hint": "glass bottle",
        "image": make_image((90, 110, 70)),
    },
    {
        "key": "glass_crack_review",
        "label": "Glass sauce bottle — possible crack",
        "product_hint": "glass bottle",
        "image": make_image((90, 110, 70), blotch={"radius": radius_for_ratio(0.06), "darken": 0.5, "tint": (200, 200, 200)}),
    },
    {
        "key": "dark_blurry",
        "label": "Low quality — too dark / blurry",
        "product_hint": "tomato",
        "image": make_image((205, 60, 42), noise_sigma=1.5, brightness_scale=0.18),
    },
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = []
    for sample in SAMPLES:
        filename = f"{sample['key']}.jpg"
        sample["image"].save(os.path.join(OUT_DIR, filename), format="JPEG", quality=90)
        manifest.append({"key": sample["key"], "label": sample["label"], "product_hint": sample["product_hint"], "file": filename})
        print(f"wrote {filename}")

    import json

    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest.json with {len(manifest)} samples to {OUT_DIR}")


if __name__ == "__main__":
    main()
