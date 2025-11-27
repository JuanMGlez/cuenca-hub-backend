"""Servicio de almacenamiento tipo Big Tech con Supabase"""
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

class StorageService:
    """Servicio de almacenamiento estilo Vercel/Notion/Linear"""
    
    def __init__(self):
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase no disponible. Ejecuta: pip install supabase")
        
        # Configuración Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY requeridas")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.bucket_name = "analysis-charts"
    
    def upload_chart(self, image_data: bytes, analysis_id: str, metadata: Dict[str, Any] = None) -> Dict[str, str]:
        """Sube gráfico con patrón Big Tech: hash-based deduplication + CDN"""
        try:
            # 1. Hash-based deduplication (como GitHub/Vercel)
            content_hash = hashlib.sha256(image_data).hexdigest()[:16]
            
            # 2. Structured path (como AWS S3 best practices)
            timestamp = datetime.now().strftime("%Y/%m/%d")
            file_path = f"charts/{timestamp}/{analysis_id}_{content_hash}.png"
            
            # 3. Upload con metadata (como Notion)
            upload_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=image_data,
                file_options={
                    "content-type": "image/png",
                    "cache-control": "3600"
                }
            )
            
            # 4. Generate signed URL (como Vercel Edge)
            signed_url = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=86400 * 7  # 7 days
            )
            
            # 5. Store metadata in database (como Linear)
            chart_record = {
                "id": str(uuid.uuid4()),
                "analysis_id": analysis_id,
                "file_path": file_path,
                "content_hash": content_hash,
                "url": signed_url["signedURL"],
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            # Insert record
            self.supabase.table("analysis_charts").insert(chart_record).execute()
            
            return {
                "chart_id": chart_record["id"],
                "url": signed_url["signedURL"],
                "cdn_url": self._get_cdn_url(file_path),
                "content_hash": content_hash,
                "expires_at": chart_record["expires_at"]
            }
            
        except Exception as e:
            return {"error": f"Upload failed: {str(e)}"}
    
    def get_chart_url(self, chart_id: str) -> Optional[str]:
        """Obtiene URL del gráfico con refresh automático"""
        try:
            # Get chart record
            result = self.supabase.table("analysis_charts").select("*").eq("id", chart_id).execute()
            
            if not result.data:
                return None
            
            chart = result.data[0]
            
            # Check if URL expired (como Cloudflare)
            expires_at = datetime.fromisoformat(chart["expires_at"])
            if datetime.now() > expires_at:
                # Refresh signed URL
                new_signed_url = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                    path=chart["file_path"],
                    expires_in=86400 * 7
                )
                
                # Update record
                self.supabase.table("analysis_charts").update({
                    "url": new_signed_url["signedURL"],
                    "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
                }).eq("id", chart_id).execute()
                
                return new_signed_url["signedURL"]
            
            return chart["url"]
            
        except Exception:
            return None
    
    def _get_cdn_url(self, file_path: str) -> str:
        """Genera URL de CDN público (como Vercel Edge)"""
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
    
    def cleanup_expired_charts(self):
        """Limpia gráficos expirados (cron job como Vercel)"""
        try:
            # Get expired charts
            expired_charts = self.supabase.table("analysis_charts").select("*").lt(
                "expires_at", datetime.now().isoformat()
            ).execute()
            
            for chart in expired_charts.data:
                # Delete from storage
                self.supabase.storage.from_(self.bucket_name).remove([chart["file_path"]])
                
                # Delete record
                self.supabase.table("analysis_charts").delete().eq("id", chart["id"]).execute()
                
        except Exception as e:
            print(f"Cleanup error: {e}")

class AnalysisSession:
    """Sesión de análisis estilo Big Tech con tracking"""
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
    
    def create_analysis_record(self, question: str, file_info: Dict, result: Dict) -> str:
        """Crea registro de análisis con tracking completo"""
        try:
            analysis_record = {
                "id": str(uuid.uuid4()),
                "session_id": self.session_id,
                "question": question,
                "file_info": file_info,
                "result_summary": {
                    "type": result.get("type"),
                    "num_sources": result.get("num_sources", 0),
                    "processing_time": result.get("processing_time", 0),
                    "has_chart": bool(result.get("chart"))
                },
                "created_at": datetime.now().isoformat(),
                "status": "completed" if not result.get("error") else "failed"
            }
            
            # Insert analysis record
            insert_result = self.storage.supabase.table("analysis_sessions").insert(analysis_record).execute()
            
            return analysis_record["id"]
            
        except Exception as e:
            print(f"Analysis record error: {e}")
            return str(uuid.uuid4())  # Fallback ID
    
    def get_session_history(self) -> list:
        """Obtiene historial de la sesión"""
        try:
            result = self.storage.supabase.table("analysis_sessions").select("*").eq(
                "session_id", self.session_id
            ).order("created_at", desc=True).execute()
            
            return result.data
            
        except Exception:
            return []