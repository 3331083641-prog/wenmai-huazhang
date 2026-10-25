"""Image-only display geometry. No neural models, downloads or network calls."""
import numpy as np
from PIL import Image, ImageFilter

DEPTH_SOURCE = 'image_geometry_v1'


def image_depth(image_path, anchors=None, scene_kind='flat_artwork'):
    """Deterministic brightness/centre/vertical heuristic for limited 2.5D parallax."""
    with Image.open(image_path) as image:
        small = image.convert('RGB').resize((512, 512))
    arr = np.asarray(small, dtype=np.float32) / 255
    lum = arr @ np.array([.299, .587, .114], dtype=np.float32)
    blurred = Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8))
    lum_blur = np.asarray(blurred, dtype=np.float32) / 255
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if anchors:
        if scene_kind == 'flat_artwork':
            # A flat motif must retain a coherent surface rather than invented depth layers.
            return (.5 + .02*(lum_blur-.5)).astype(np.float32)
        weight_sum = np.zeros((h,w), dtype=np.float32)
        depth_sum = np.zeros((h,w), dtype=np.float32)
        for anchor in anchors:
            distance = (xx/(w-1)-anchor['x'])**2 + (yy/(h-1)-anchor['y'])**2
            weight = np.exp(-distance/.09) + 1e-7
            depth_sum += weight*anchor['depth']
            weight_sum += weight
        return np.clip(depth_sum/weight_sum, .1, .9).astype(np.float32)
    radial = np.clip(1 - np.sqrt(((xx-(w-1)/2)/(w*.62))**2 + ((yy-(h-1)/2)/(h*.62))**2), 0, 1)
    depth = .55*lum_blur + .30*radial + .15*(1-yy/max(h-1, 1))
    low, high = np.percentile(depth, [3, 97])
    return np.clip((depth-low)/max(float(high-low), 1e-6), 0, 1).astype(np.float32)
