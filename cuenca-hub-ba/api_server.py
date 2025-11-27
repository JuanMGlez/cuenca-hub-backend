#!/usr/bin/env python3
"""Servidor API para el sistema KG-RAG"""

import uvicorn

if __name__ == "__main__":
    print("🌊 Iniciando River Restoration KG-RAG API...")
    print("📡 Servidor disponible en: http://localhost:8000")
    print("📚 Documentación en: http://localhost:8000/docs")
    
    uvicorn.run(
        "src.cuenca_hub_ba.api:app", 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info"
    )