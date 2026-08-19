"""QR codes for print CTAs.

Print QRs are scanned at arm's length off matte paper, so they are rendered at
high error correction with a quiet zone — a QR that fails to scan is worse than
no QR at all.

Usage:  python3 scripts/make_qr.py <url> <out.png>
"""
from __future__ import annotations

import sys
from pathlib import Path


def write_qr(url: str, out: Path, box_size: int = 12, border: int = 3) -> Path:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H,
                       box_size=box_size, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    path = write_qr(sys.argv[1], Path(sys.argv[2]))
    print(f"wrote {path}")
