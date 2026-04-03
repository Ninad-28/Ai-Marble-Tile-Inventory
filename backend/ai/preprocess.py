import cv2
import numpy as np
from PIL import Image
import io

def normalize_lighting(img_array: np.ndarray) -> np.ndarray:
    """Normalize uneven lighting using CLAHE"""
    lab = cv2.cvtColor(img_array, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
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

def preprocess_image(image_input) -> Image.Image:
    """
    Full preprocessing pipeline.
    Accepts: file path (str) or bytes
    Returns: PIL Image ready for model
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

    # Run pipeline
    img_array = normalize_lighting(img_array)
    img_array = correct_perspective(img_array)
    img_array = resize_for_model(img_array)

    # Convert BGR → RGB → PIL
    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img_rgb)