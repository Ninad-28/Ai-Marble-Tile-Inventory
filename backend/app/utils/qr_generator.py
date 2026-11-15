import os
import qrcode

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
QR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "qrcodes")
)
os.makedirs(QR_DIR, exist_ok=True)


def get_qr_filename(tile_id: int) -> str:
    return f"tile_{tile_id}.png"


def get_qr_url(tile_id: int) -> str:
    return f"/static/qrcodes/{get_qr_filename(tile_id)}"


def ensure_tile_qr(tile_id: int, force: bool = False) -> str:
    """Generates a high-contrast QR PNG pointing to /scan/{tile_id} if missing."""
    filepath = os.path.join(QR_DIR, get_qr_filename(tile_id))
    if not force and os.path.exists(filepath):
        return get_qr_url(tile_id)

    scan_url = f"{FRONTEND_BASE_URL}/scan/{tile_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(scan_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)
    return get_qr_url(tile_id)