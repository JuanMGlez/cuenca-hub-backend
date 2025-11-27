"""Cliente para Supabase Storage"""

import os
import requests
from typing import Optional


def upload_image_to_storage(image_data: bytes, filename: str) -> Optional[str]:
    """Sube imagen al bucket de Supabase Storage"""
    try:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")

        print(f"🔗 Supabase URL: {url[:50]}..." if url else "❌ No SUPABASE_URL")
        print(f"🔑 API Key: {key[:20]}..." if key else "❌ No SUPABASE_ANON_KEY")

        if not url or not key:
            print("❌ Credenciales Supabase faltantes")
            return None

        storage_headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "image/png",
        }

        upload_url = f"{url}/storage/v1/object/analysis-charts/{filename}"
        print(f"📤 Upload URL: {upload_url}")

        response = requests.post(upload_url, headers=storage_headers, data=image_data)

        print(f"📊 Status: {response.status_code}")
        print(f"📝 Response: {response.text[:200]}")

        if response.status_code == 200:
            public_url = f"{url}/storage/v1/object/public/analysis-charts/{filename}"
            print(f"✅ URL pública: {public_url}")
            return public_url

        return None

    except Exception as e:
        print(f"❌ Error en upload: {str(e)}")
        return None
