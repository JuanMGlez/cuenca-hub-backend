"""Modelos de request para Sentinel-2"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class Sentinel2Request(BaseModel):
    coordinates: List[List[float]]
    date_start: Optional[str] = "2020-01-01"
    date_end: Optional[str] = "2025-12-31"
    include_dashboard: bool = True