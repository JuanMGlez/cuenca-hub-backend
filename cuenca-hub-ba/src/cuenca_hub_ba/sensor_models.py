"""Modelos para API de sensores IoT"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SensorReading(BaseModel):
    device_id: str
    timestamp: Optional[str] = None
    ph: Optional[float] = None
    temperature: Optional[float] = None
    dissolved_oxygen: Optional[float] = None
    turbidity: Optional[float] = None
    conductivity: Optional[float] = None
    water_level: Optional[float] = None
    flow_rate: Optional[float] = None

class DeviceRegistration(BaseModel):
    device_id: str
    name: str
    type: str
    location_lat: float
    location_lng: float
    municipality: str