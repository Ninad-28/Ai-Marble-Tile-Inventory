import cv2
import numpy as np
from PIL import Image
import io

def enhance_blur_sharpness(img_array: np.ndarray) -> np.ndarray:
    """
    Use unsharp masking to enhance details and counteract blur.
    Helps with blurry or distorted tile images.
    """
    gaussian = cv2.GaussianBlur(img_array, (5, 5), 1.0)
    sharpened = cv2.addWeighted(img_array, 1.5, gaussian, -0.5, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)

def normalize_lighting(img_array: np.ndarray) -> np.ndarray:
    """
    Normalize uneven lighting and handle dark images using CLAHE.
    Enhanced to work better with both bright and dark conditions.
    """
    lab = cv2.cvtColor(img_array, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Adaptive histogram equalization with higher clip limit for dark images
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Add slight gamma correction for very dark images
    mean_brightness = np.mean(l)
    if mean_brightness < 80:  # Very dark
        gamma = 1.2
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255
                         for i in np.arange(0, 256)]).astype(np.uint8)
        l = cv2.LUT(l, table)
    
    lab = cv2.merge((l, a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def equalize_histogram(img_array: np.ndarray) -> np.ndarray:
    """Apply histogram equalization to the luminance channel."""
    ycrcb = cv2.cvtColor(img_array, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y_eq = cv2.equalizeHist(y)
    merged = cv2.merge((y_eq, cr, cb))
    return cv2.cvtColor(merged, cv2.COLOR_YCrCb2BGR)

def denoise(img_array: np.ndarray) -> np.ndarray:
    """Noise reduction while preserving edges."""
    return cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)

def color_normalization(img_array: np.ndarray) -> np.ndarray:
    """Normalize colors in LAB space."""
    lab = cv2.cvtColor(img_array, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.normalize(l, None, 0, 255, cv2.NORM_MINMAX)
    a = cv2.normalize(a, None, 0, 255, cv2.NORM_MINMAX)
    b = cv2.normalize(b, None, 0, 255, cv2.NORM_MINMAX)
    lab = cv2.merge((l, a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def correct_perspective(img_array: np.ndarray) -> np.ndarray:
    """Basic perspective correction by finding largest rectangle"""
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if contours:
        largest = max(contours, key=cv2.contourArea)
        area_ratio = cv2.contourArea(largest) / (
            img_array.shape[0] * img_array.shape[1]
        )
        # Only correct if contour covers >30% of image
        if area_ratio > 0.3:
            x, y, w, h = cv2.boundingRect(largest)
            img_array = img_array[y:y+h, x:x+w]

    return img_array

def resize_for_model(img_array: np.ndarray,
                     size: tuple = (224, 224)) -> np.ndarray:
    """Resize to model input size"""
    return cv2.resize(img_array, size, interpolation=cv2.INTER_LANCZOS4)

def preprocess_image(image_input, mode="db") -> Image.Image:
    """
    Light preprocessing pipeline.
    Avoids destroying the marble patterns that DINOv2 needs.
    """
    # Load image
    if isinstance(image_input, (str, bytes)):
        if isinstance(image_input, str):
            img_array = cv2.imread(image_input)
        else:
            nparr = np.frombuffer(image_input, np.uint8)
            img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        # Already a numpy array
        img_array = image_input

    if img_array is None:
        raise ValueError("Could not load image")

    # Run lightweight preprocessing pipeline
    if mode == "query":
        # Only use perspective correction for uploaded queries
        img_array = correct_perspective(img_array)
        
    # Resize
    img_array = resize_for_model(img_array)

    # Convert BGR → RGB → PIL
    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img_rgb)