"""Cliente Supabase para contadores de reportes y sensores IoT"""

import os
import requests
from typing import Optional

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_ANON_KEY", "")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
    
    def get_reports_count(self) -> int:
        """Obtiene el contador de reportes desde Supabase"""
        try:
            if not self.url or not self.key:
                return 0
                
            response = requests.get(
                f"{self.url}/rest/v1/reports?select=count",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data) if isinstance(data, list) else 0
            return 0
            
        except Exception:
            return 0
    
    def validate_api_key(self, api_key: str, device_id: str) -> bool:
        """Valida API key del dispositivo"""
        try:
            if not self.url or not self.key:
                return False
                
            response = requests.get(
                f"{self.url}/rest/v1/devices?device_id=eq.{device_id}&api_key=eq.{api_key}&select=device_id",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data) > 0
            return False
            
        except Exception:
            return False
    
    def insert_sensor_reading(self, reading_data: dict) -> Optional[str]:
        """Inserta lectura de sensor"""
        try:
            if not self.url or not self.key:
                return None
                
            response = requests.post(
                f"{self.url}/rest/v1/sensor_readings",
                headers=self.headers,
                json=reading_data
            )
            
            if response.status_code == 201:
                data = response.json()
                return data[0].get("id") if data else None
            return None
            
        except Exception:
            return None
    
    def update_device_last_seen(self, device_id: str) -> bool:
        """Actualiza last_seen del dispositivo"""
        try:
            if not self.url or not self.key:
                return False
                
            response = requests.patch(
                f"{self.url}/rest/v1/devices?device_id=eq.{device_id}",
                headers=self.headers,
                json={"last_seen": "now()"}
            )
            
            return response.status_code == 204
            
        except Exception:
            return False
    
    def get_sensor_readings(self, device_id=None, start_date=None, end_date=None, limit=100, device_type=None):
        """Obtiene lecturas de sensores con filtros"""
        try:
            if not self.url or not self.key:
                return []
            
            query = f"{self.url}/rest/v1/sensor_readings?select=*,devices(name,location_lat,location_lng,municipality)"
            
            filters = []
            if device_id:
                filters.append(f"device_id=eq.{device_id}")
            if start_date:
                filters.append(f"timestamp=gte.{start_date}")
            if end_date:
                filters.append(f"timestamp=lte.{end_date}")
            
            if filters:
                query += "&" + "&".join(filters)
            
            query += f"&limit={min(limit, 1000)}&order=timestamp.desc"
            
            response = requests.get(query, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception:
            return []
    
    def register_device(self, device_data: dict) -> Optional[str]:
        """Registra nuevo dispositivo"""
        try:
            if not self.url or not self.key:
                return None
            
            import secrets
            api_key = secrets.token_urlsafe(32)
            device_data["api_key"] = api_key
            device_data["status"] = "active"
            
            response = requests.post(
                f"{self.url}/rest/v1/devices",
                headers=self.headers,
                json=device_data
            )
            
            if response.status_code == 201:
                return api_key
            return None
            
        except Exception:
            return None
    
    def get_devices(self, status=None, device_type=None):
        """Obtiene lista de dispositivos"""
        try:
            if not self.url or not self.key:
                return []
            
            query = f"{self.url}/rest/v1/devices?select=device_id,name,type,location_lat,location_lng,municipality,status,last_seen"
            
            filters = []
            if status:
                filters.append(f"status=eq.{status}")
            if device_type:
                filters.append(f"type=eq.{device_type}")
            
            if filters:
                query += "&" + "&".join(filters)
            
            response = requests.get(query, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception:
            return []