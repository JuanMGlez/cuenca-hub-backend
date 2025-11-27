"""API REST para el sistema KG-RAG"""

from dotenv import load_dotenv
load_dotenv()  # Cargar variables de entorno

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import shutil
from pathlib import Path

from .rag_system import RAGSystem
from .utils import get_system_stats, system_health_check
from .unified_agent import UnifiedAgent
from .storage_service import AnalysisSession, StorageService

app = FastAPI(
    title="🌊 River Restoration KG-RAG API",
    description="Sistema avanzado de Knowledge Graph RAG para investigación en restauración de ríos",
    version="1.0.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sistema global
rag_system = None
unified_agent = None
storage_service = None


class QueryRequest(BaseModel):
    question: str
    include_citations: bool = True


class TraceabilityReport(BaseModel):
    total_references: int
    valid_references: List[int]
    reliability_score: float
    has_traceability: bool


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict]
    citations: List[str]
    num_sources: int
    processing_time: float
    traceability: Optional[TraceabilityReport] = None


class SystemStats(BaseModel):
    pdf_count: int
    papers_in_graph: int
    authors_in_graph: int
    concepts_in_graph: int
    chunks_in_vector_db: int
    system_healthy: bool



class UnifiedResponse(BaseModel):
    type: str  # "document_search", "data_analysis", "hybrid"
    question: str
    answer: str
    
    # Chart info (Big Tech style)
    chart_url: Optional[str] = None
    chart_cdn_url: Optional[str] = None
    chart_id: Optional[str] = None
    chart: Optional[str] = None  # Fallback base64
    
    # Analysis metadata
    analysis_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Data insights
    data_summary: Optional[Dict] = None
    document_insights: Optional[Dict] = None
    data_insights: Optional[Dict] = None
    
    # Sources
    sources: List[Dict] = []
    citations: List[str] = []
    num_sources: int = 0
    
    # Performance
    processing_time: float = 0.0
    error: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Inicializar sistema al arrancar"""
    global rag_system, unified_agent, storage_service
    try:
        rag_system = RAGSystem()
        if not rag_system.check_ingestion_status():
            rag_system.run_ingestion()
        rag_system.initialize_query_engine()
        unified_agent = UnifiedAgent(rag_system)
        
        # Inicializar storage service
        try:
            storage_service = StorageService()
        except (ImportError, ValueError) as e:
            print(f"⚠️  Storage service no disponible: {e}")
            storage_service = None
            
    except Exception as e:
        print(f"❌ Error inicializando sistema: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al cerrar"""
    global rag_system
    if rag_system:
        rag_system.close()


@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "message": "🌊 River Restoration KG-RAG API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "query": "/query",
            "upload": "/upload",
            "capabilities": "/capabilities",
            "chart": "/chart/{chart_id}",
            "session": "/session/{session_id}",
            "stats": "/stats",
            "health": "/health",
        },
    }





@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Subir PDF para ingesta"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    try:
        # Guardar archivo
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)

        file_path = data_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ejecutar ingesta
        if rag_system:
            rag_system.run_ingestion()

        return {
            "message": f"PDF '{file.filename}' subido y procesado exitosamente",
            "filename": file.filename,
            "status": "processed",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")


@app.get("/stats", response_model=SystemStats)
async def get_stats():
    """Obtener estadísticas del sistema"""
    try:
        stats = get_system_stats()
        health = system_health_check()

        return SystemStats(
            pdf_count=stats["pdf_count"],
            papers_in_graph=stats["papers_in_graph"],
            authors_in_graph=stats["authors_in_graph"],
            concepts_in_graph=stats["concepts_in_graph"],
            chunks_in_vector_db=stats["chunks_in_vector_db"],
            system_healthy=health,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Verificar salud del sistema"""
    try:
        health = system_health_check()
        stats = get_system_stats()

        return {
            "status": "healthy" if health else "unhealthy",
            "system_initialized": rag_system is not None,
            "papers_available": stats["papers_in_graph"] > 0,
            "vector_db_ready": stats["chunks_in_vector_db"] > 0,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/query", response_model=UnifiedResponse)
async def query_system_unified(
    question: str = Form(...),
    include_citations: bool = Form(True),
    session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Endpoint unificado estilo Big Tech con session tracking"""
    if not unified_agent:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")
    
    try:
        import time
        import uuid
        start_time = time.time()
        
        # Crear sesión de análisis (patrón Big Tech)
        if storage_service:
            analysis_session = AnalysisSession(storage_service)
            if session_id:
                analysis_session.session_id = session_id
        else:
            analysis_session = None
        
        # Generar ID único para este análisis
        analysis_id = str(uuid.uuid4())
        
        # Procesar archivo si existe
        file_content = None
        file_type = None
        file_info = {}
        
        if file:
            if file.filename.endswith('.csv'):
                content = await file.read()
                file_content = content.decode('utf-8')
                file_type = "csv"
            elif file.filename.endswith(('.xlsx', '.xls')):
                content = await file.read()
                file_content = content
                file_type = "excel"
            else:
                raise HTTPException(status_code=400, detail="Solo se permiten archivos CSV o Excel")
            
            file_info = {
                "filename": file.filename,
                "size": len(content),
                "type": file_type
            }
        
        # Procesar con agente unificado (con analysis_id)
        result = unified_agent.process_unified_query(
            query=question,
            file_content=file_content,
            file_type=file_type,
            analysis_id=analysis_id
        )
        
        processing_time = time.time() - start_time
        
        # Crear registro de análisis
        if analysis_session:
            analysis_session.create_analysis_record(question, file_info, result)
        
        # Formatear respuesta estilo Big Tech
        return UnifiedResponse(
            type=result.get("type", "unknown"),
            question=result.get("query", question) or question,
            answer=result.get("answer", "No se pudo generar respuesta") or "No se pudo generar respuesta",
            
            # Chart URLs (Big Tech style)
            chart_url=result.get("chart_url"),
            chart_cdn_url=result.get("chart_cdn_url"),
            chart_id=result.get("chart_id"),
            chart=result.get("chart"),  # Fallback base64
            
            # Session tracking
            analysis_id=analysis_id,
            session_id=analysis_session.session_id if analysis_session else None,
            
            # Data insights
            data_summary=result.get("data_summary"),
            document_insights=result.get("document_insights"),
            data_insights=result.get("data_insights"),
            
            # Sources
            sources=result.get("sources", []) or [],
            citations=result.get("citations", []) if include_citations else [],
            num_sources=result.get("num_sources", 0) or 0,
            
            # Performance
            processing_time=round(processing_time, 2),
            error=result.get("error")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@app.get("/capabilities")
async def get_capabilities():
    """Obtiene capacidades del agente unificado"""
    if not unified_agent:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")
    
    return unified_agent.get_capabilities()

@app.get("/chart/{chart_id}")
async def get_chart(chart_id: str):
    """Obtiene URL de gráfico (patrón Big Tech)"""
    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service no disponible")
    
    chart_url = storage_service.get_chart_url(chart_id)
    if not chart_url:
        raise HTTPException(status_code=404, detail="Gráfico no encontrado")
    
    return {"url": chart_url, "chart_id": chart_id}

@app.get("/session/{session_id}")
async def get_session_history(session_id: str):
    """Obtiene historial de sesión (patrón Big Tech)"""
    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service no disponible")
    
    try:
        session = AnalysisSession(storage_service)
        session.session_id = session_id
        history = session.get_session_history()
        
        return {
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {str(e)}")

@app.post("/ingest")
async def trigger_ingestion():
    """Forzar re-ingesta de todos los PDFs"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="Sistema no inicializado")

    try:
        rag_system.run_ingestion()
        stats = get_system_stats()

        return {
            "message": "Ingesta completada exitosamente",
            "papers_processed": stats["papers_in_graph"],
            "chunks_created": stats["chunks_in_vector_db"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en ingesta: {str(e)}")

@app.post("/cleanup")
async def cleanup_expired_charts():
    """Limpia gráficos expirados (cron endpoint)"""
    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service no disponible")
    
    try:
        storage_service.cleanup_expired_charts()
        return {"message": "Cleanup completado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cleanup: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
