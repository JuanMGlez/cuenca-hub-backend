"""Agente unificado tipo LangGraph para manejo inteligente de consultas"""
from typing import Dict, Any, Optional, List
from enum import Enum
import re

class QueryType(Enum):
    DOCUMENT_SEARCH = "document_search"
    DATA_ANALYSIS = "data_analysis"
    HYBRID = "hybrid"

class UnifiedAgent:
    """Agente unificado que decide automáticamente el tipo de procesamiento"""
    
    def __init__(self, rag_system):
        self.rag_system = rag_system
        self.uploaded_data = None
        self.data_context = {}
    
    def classify_query(self, query: str, has_file: bool = False) -> QueryType:
        """Clasifica automáticamente el tipo de consulta"""
        
        # Palabras clave para análisis de datos
        data_keywords = [
            'analyze', 'chart', 'graph', 'plot', 'correlation', 'statistics', 
            'dataset', 'csv', 'excel', 'data', 'trend', 'distribution',
            'mean', 'median', 'variance', 'outlier', 'regression'
        ]
        
        # Palabras clave para búsqueda documental
        doc_keywords = [
            'research', 'paper', 'study', 'restoration', 'river', 'water',
            'treatment', 'technique', 'method', 'approach', 'literature'
        ]
        
        query_lower = query.lower()
        
        # Si hay archivo subido, priorizar análisis de datos
        if has_file:
            return QueryType.DATA_ANALYSIS
        
        # Contar coincidencias
        data_matches = sum(1 for keyword in data_keywords if keyword in query_lower)
        doc_matches = sum(1 for keyword in doc_keywords if keyword in query_lower)
        
        # Decisión basada en coincidencias
        if data_matches > doc_matches and data_matches >= 2:
            return QueryType.DATA_ANALYSIS
        elif doc_matches > data_matches:
            return QueryType.DOCUMENT_SEARCH
        elif data_matches > 0 and doc_matches > 0:
            return QueryType.HYBRID
        else:
            return QueryType.DOCUMENT_SEARCH  # Default
    
    def process_unified_query(self, query: str, file_content: Optional[str] = None, 
                            file_type: Optional[str] = None, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """Procesa consulta unificada con routing automático"""
        
        # 1. Clasificar consulta
        query_type = self.classify_query(query, has_file=bool(file_content))
        
        # 2. Procesar según tipo
        if query_type == QueryType.DATA_ANALYSIS and file_content:
            return self._handle_data_analysis(query, file_content, file_type, analysis_id)
        
        elif query_type == QueryType.HYBRID:
            return self._handle_hybrid_query(query, file_content, file_type, analysis_id)
        
        else:  # DOCUMENT_SEARCH
            return self._handle_document_search(query)
    
    def _handle_data_analysis(self, query: str, file_content: str, file_type: str, analysis_id: str = None) -> Dict[str, Any]:
        """Maneja análisis puro de datos"""
        try:
            # Análisis con PandasAI
            result = self.rag_system.analyze_data(file_content, query, file_type, analysis_id)
            
            return {
                "type": "data_analysis",
                "query": query,
                "answer": result.get('analysis', 'No analysis available'),
                "chart_url": result.get('chart_url'),
                "chart_cdn_url": result.get('chart_cdn_url'),
                "chart_id": result.get('chart_id'),
                "chart": result.get('chart'),
                "data_summary": result.get('summary', {}),
                "sources": [],
                "citations": [],
                "num_sources": 0,
                "error": result.get('error')
            }
        except Exception as e:
            return {
                "type": "data_analysis",
                "query": query,
                "answer": f"Error en análisis: {str(e)}",
                "error": str(e)
            }
    
    def _handle_document_search(self, query: str) -> Dict[str, Any]:
        """Maneja búsqueda pura en documentos"""
        try:
            result = self.rag_system.query(query)
            result["type"] = "document_search"
            return result
        except Exception as e:
            return {
                "type": "document_search",
                "query": query,
                "answer": f"Error en búsqueda: {str(e)}",
                "error": str(e)
            }
    
    def _handle_hybrid_query(self, query: str, file_content: Optional[str] = None, 
                           file_type: Optional[str] = None, analysis_id: str = None) -> Dict[str, Any]:
        """Maneja consulta híbrida: datos + documentos"""
        try:
            results = {}
            
            # 1. Búsqueda en documentos
            doc_result = self.rag_system.query(query)
            results["document_insights"] = {
                "answer": doc_result["answer"],
                "sources": doc_result["sources"][:3],  # Limitar fuentes
                "num_sources": len(doc_result["sources"][:3])
            }
            
            # 2. Análisis de datos si hay archivo
            if file_content:
                data_result = self.rag_system.analyze_data(file_content, query, file_type, analysis_id)
                results["data_insights"] = {
                    "analysis": data_result.get('analysis', ''),
                    "chart_url": data_result.get('chart_url'),
                    "chart_cdn_url": data_result.get('chart_cdn_url'),
                    "chart_id": data_result.get('chart_id'),
                    "chart": data_result.get('chart'),
                    "summary": data_result.get('summary', {})
                }
            
            # 3. Síntesis híbrida
            hybrid_answer = self._synthesize_hybrid_response(results, query)
            
            return {
                "type": "hybrid",
                "query": query,
                "answer": hybrid_answer,
                "document_insights": results.get("document_insights", {}),
                "data_insights": results.get("data_insights", {}),
                "chart_url": results.get("data_insights", {}).get("chart_url"),
                "chart_cdn_url": results.get("data_insights", {}).get("chart_cdn_url"),
                "chart_id": results.get("data_insights", {}).get("chart_id"),
                "chart": results.get("data_insights", {}).get("chart"),
                "sources": results.get("document_insights", {}).get("sources", []),
                "citations": doc_result.get("citations", [])[:3],
                "num_sources": results.get("document_insights", {}).get("num_sources", 0)
            }
            
        except Exception as e:
            return {
                "type": "hybrid",
                "query": query,
                "answer": f"Error en análisis híbrido: {str(e)}",
                "error": str(e)
            }
    
    def _synthesize_hybrid_response(self, results: Dict, query: str) -> str:
        """Sintetiza respuesta híbrida combinando documentos y datos"""
        
        doc_answer = results.get("document_insights", {}).get("answer", "")
        data_analysis = results.get("data_insights", {}).get("analysis", "")
        
        if doc_answer and data_analysis:
            return f"""**Insights de Literatura Científica:**
{doc_answer}

**Análisis de Datos Proporcionados:**
{data_analysis}

**Síntesis:** Los datos analizados complementan los hallazgos de la literatura científica, proporcionando evidencia específica para las técnicas mencionadas."""
        
        elif doc_answer:
            return doc_answer
        elif data_analysis:
            return data_analysis
        else:
            return "No se pudieron generar insights para esta consulta."
    
    def get_capabilities(self) -> Dict[str, List[str]]:
        """Retorna capacidades del agente unificado"""
        return {
            "document_search": [
                "Búsqueda en literatura científica",
                "Técnicas de restauración fluvial",
                "Métodos de tratamiento de agua",
                "Referencias académicas con trazabilidad"
            ],
            "data_analysis": [
                "Análisis estadístico automático",
                "Generación de gráficos contextuales",
                "Detección de correlaciones",
                "Insights con PandasAI"
            ],
            "hybrid_mode": [
                "Combinación de literatura + datos",
                "Validación de teoría con evidencia",
                "Síntesis automática de insights",
                "Respuestas multidimensionales"
            ]
        }