"""Depth and coarseness measures for uniform shaded paper scans."""

import numpy as np
from scipy import signal

PATCH_DEFAULT = 600
ACF_DECAY_THRESHOLD = 1 / np.e


def load_patch(path: str, size: int = PATCH_DEFAULT) -> np.ndarray:
    """Load image from path, take first channel, center-crop to size x size."""
    from matplotlib.pyplot import imread

    img = imread(path)
    if img.ndim == 3:
        img = img[:, :, 0]
    h, w = img.shape
    top = (h - size) // 2
    left = (w - size) // 2
    return img[top : top + size, left : left + size].astype(np.float64)


def rms_contrast(patch: np.ndarray) -> float:
    """Standard deviation of pixel intensity over the patch."""
    return float(np.std(patch))


def mean_gradient_magnitude(patch: np.ndarray) -> float:
    """Mean of gradient magnitude over the patch."""
    gy, gx = np.gradient(patch)
    return float(np.mean(np.hypot(gx, gy)))


def acf_2d(patch: np.ndarray) -> np.ndarray:
    """2D autocorrelation, normalized so center is 1. Same shape as patch."""
    c = signal.correlate(patch, patch, mode="same")
    center = c.max()
    if center <= 0:
        return c
    return c / center


def radial_average_acf(acf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Bin ACF by radial distance from center; return (r_px, mean_acf_per_r)."""
    h, w = acf.shape
    cy, cx = h // 2, w // 2
    y = np.arange(h, dtype=np.float64) - cy
    x = np.arange(w, dtype=np.float64) - cx
    r = np.sqrt(np.add.outer(y**2, x**2))
    r_int = np.round(r).astype(np.intp)
    r_flat = r_int.ravel()
    acf_flat = acf.ravel()
    r_max = int(r_flat.max())
    r_bins = np.arange(r_max + 1, dtype=np.float64)
    mean_acf = np.array(
        [acf_flat[r_flat == ri].mean() if (r_flat == ri).any() else np.nan for ri in range(r_max + 1)]
    )
    return r_bins, mean_acf


def correlation_length(r: np.ndarray, acf_values: np.ndarray) -> float:
    """First r (in px) at which radially averaged ACF <= 1/e. Linear interpolation."""
    valid = ~np.isnan(acf_values)
    if not valid.any():
        return float(r[-1])
    r_v = r[valid]
    a_v = acf_values[valid]
    below = np.where(a_v <= ACF_DECAY_THRESHOLD)[0]
    if not below.size:
        return float(r_v[-1])
    i = int(below[0])
    if i == 0:
        return 0.0
    r0, r1 = r_v[i - 1], r_v[i]
    a0, a1 = a_v[i - 1], a_v[i]
    t = (ACF_DECAY_THRESHOLD - a0) / (a1 - a0) if a1 != a0 else 0.0
    return float(r0 + t * (r1 - r0))


def analyze_patch(patch: np.ndarray) -> dict[str, float]:
    """Compute depth and coarseness metrics for one patch."""
    rms = rms_contrast(patch)
    grad = mean_gradient_magnitude(patch)
    acf = acf_2d(patch)
    r, acf_r = radial_average_acf(acf)
    xi = correlation_length(r, acf_r)
    return {
        "rms_contrast": rms,
        "mean_gradient": grad,
        "correlation_length_px": xi,
    }
