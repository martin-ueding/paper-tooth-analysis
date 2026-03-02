"""Depth and coarseness measures for uniform shaded paper scans."""

import numpy as np
from scipy import fft, signal

PATCH_DEFAULT = 600
ACF_DECAY_THRESHOLD = 1 / np.e
ACF_HALF_MAX = 0.5


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


def mean_intensity(patch: np.ndarray) -> float:
    """Mean pixel intensity over the patch (0–1 for typical 0–255 scans)."""
    return float(np.mean(patch))


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


def _first_crossing(r: np.ndarray, acf_values: np.ndarray, threshold: float) -> float:
    """First r at which acf_values <= threshold; linear interpolation."""
    valid = ~np.isnan(acf_values)
    if not valid.any():
        return float(r[-1])
    r_v = r[valid]
    a_v = acf_values[valid]
    below = np.where(a_v <= threshold)[0]
    if not below.size:
        return float(r_v[-1])
    i = int(below[0])
    if i == 0:
        return 0.0
    r0, r1 = r_v[i - 1], r_v[i]
    a0, a1 = a_v[i - 1], a_v[i]
    t = (threshold - a0) / (a1 - a0) if a1 != a0 else 0.0
    return float(r0 + t * (r1 - r0))


def correlation_length(r: np.ndarray, acf_values: np.ndarray) -> float:
    """First r (in px) at which radially averaged ACF <= 1/e."""
    return _first_crossing(r, acf_values, ACF_DECAY_THRESHOLD)


def acf_fwhm(r: np.ndarray, acf_values: np.ndarray) -> float:
    """Full width at half maximum of radial ACF (diameter of central peak in px)."""
    r_half = _first_crossing(r, acf_values, ACF_HALF_MAX)
    return 2.0 * r_half


def radial_power_scale(patch: np.ndarray) -> float:
    """Characteristic scale (px) from radial power spectrum: N / k_mean (first moment of k), excluding DC."""
    n = patch.shape[0]
    spec = fft.fft2(patch - np.mean(patch))
    power = np.abs(fft.fftshift(spec)) ** 2
    h, w = power.shape
    cy, cx = h // 2, w // 2
    y = np.arange(h, dtype=np.float64) - cy
    x = np.arange(w, dtype=np.float64) - cx
    k_radius = np.sqrt(np.add.outer(y**2, x**2))
    k_int = np.round(k_radius).astype(np.intp)
    k_flat = k_int.ravel()
    p_flat = power.ravel()
    k_max = int(k_flat.max())
    sum_power = np.zeros(k_max + 1)
    sum_k_power = np.zeros(k_max + 1)
    count = np.zeros(k_max + 1)
    for ki in range(1, k_max + 1):
        mask = k_flat == ki
        if mask.any():
            p_sum = p_flat[mask].sum()
            sum_power[ki] = p_sum
            sum_k_power[ki] = ki * p_sum
            count[ki] = mask.sum()
    total_power = sum_power[1:].sum()
    if total_power <= 0:
        return float("nan")
    k_mean = sum_k_power[1:].sum() / total_power
    if k_mean <= 0:
        return float("nan")
    return float(n) / k_mean


def analyze_patch(patch: np.ndarray) -> dict[str, float]:
    """Compute depth and coarseness metrics for one patch."""
    mean_i = mean_intensity(patch)
    rms = rms_contrast(patch)
    grad = mean_gradient_magnitude(patch)
    acf = acf_2d(patch)
    r, acf_r = radial_average_acf(acf)
    xi = correlation_length(r, acf_r)
    fwhm = acf_fwhm(r, acf_r)
    power_scale = radial_power_scale(patch)
    return {
        "mean_intensity": mean_i,
        "rms_contrast": rms,
        "mean_gradient": grad,
        "correlation_length_px": xi,
        "acf_fwhm_px": fwhm,
        "power_scale_px": power_scale,
    }
