"""Stage 9 — Generation-time visual noise augmentations (§27).

All functions operate on a PIL Image and return a new Image.

Public API
----------
apply_generation_noise(img, seed=None) -> PIL.Image
"""

from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def apply_generation_noise(
    img: Image.Image,
    seed: int | None = None,
    salt_pepper_density: float | None = None,
    brightness_factor:   float | None = None,
    contrast_factor:     float | None = None,
    blur_radius:         float | None = None,
    rotation_angle:      float | None = None,
) -> Image.Image:
    """Apply a pipeline of generation-time augmentations to a P&ID image (§27).

    All numeric parameters default to a random value within their design range
    when not specified.  Pass explicit values to fix specific augmentations,
    or ``0`` / ``1.0`` to disable individual steps.

    Args:
        img:                  Source PIL Image (RGB).
        seed:                 Optional RNG seed for reproducibility.
        salt_pepper_density:  Fraction of pixels to corrupt (default 0.002–0.008).
        brightness_factor:    Brightness multiplier (default 0.88–1.12).
        contrast_factor:      Contrast multiplier (default 0.90–1.10).
        blur_radius:          Gaussian blur radius in pixels (default 0.3–0.8).
        rotation_angle:       Rotation angle in degrees (default ±0.3–1.0°).

    Returns:
        Augmented PIL Image.
    """
    rng = random.Random(seed)

    # -----------------------------------------------------------------------
    # Salt & pepper noise
    # -----------------------------------------------------------------------
    density = salt_pepper_density if salt_pepper_density is not None \
              else rng.uniform(0.002, 0.008)
    if density > 0:
        arr = np.array(img, dtype=np.uint8)
        h, w = arr.shape[:2]
        n_pixels = h * w
        # Salt
        n_salt = int(n_pixels * density)
        ys = np.random.randint(0, h, n_salt)
        xs = np.random.randint(0, w, n_salt)
        arr[ys, xs] = 255
        # Pepper
        n_pepper = int(n_pixels * density)
        ys = np.random.randint(0, h, n_pepper)
        xs = np.random.randint(0, w, n_pepper)
        arr[ys, xs] = 0
        img = Image.fromarray(arr)

    # -----------------------------------------------------------------------
    # Brightness jitter
    # -----------------------------------------------------------------------
    bf = brightness_factor if brightness_factor is not None \
         else rng.uniform(0.88, 1.12)
    if bf != 1.0:
        img = ImageEnhance.Brightness(img).enhance(bf)

    # -----------------------------------------------------------------------
    # Contrast jitter
    # -----------------------------------------------------------------------
    cf = contrast_factor if contrast_factor is not None \
         else rng.uniform(0.90, 1.10)
    if cf != 1.0:
        img = ImageEnhance.Contrast(img).enhance(cf)

    # -----------------------------------------------------------------------
    # Gaussian blur (slight out-of-focus effect)
    # -----------------------------------------------------------------------
    br = blur_radius if blur_radius is not None \
         else rng.uniform(0.3, 0.8)
    if br > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=br))

    # -----------------------------------------------------------------------
    # Slight rotation (simulate non-straight scan)
    # -----------------------------------------------------------------------
    angle = rotation_angle if rotation_angle is not None \
            else rng.uniform(-1.0, 1.0)
    if angle != 0:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False,
                         fillcolor=(255, 255, 255))

    return img
