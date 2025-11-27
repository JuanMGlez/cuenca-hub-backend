"""Cliente para Supabase Storage"""

import os
import requests
from typing import Optional


def upload_image_to_storage(image_data: bytes, filename: str) -> Optional[str]:
    """Sube imagen al bucket de Supabase Storage"""
    try:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")

        if not url or not key:
            return None

        storage_headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "image/png",
        }

        response = requests.post(
            f"{url}/storage/v1/object/analysis-charts/{filename}",
            headers=storage_headers,
            data=image_data
        )

        if response.status_code == 200:
            return f"{url}/storage/v1/object/public/analysis-charts/{filename}"

        return None

    except Exception:
        return None
