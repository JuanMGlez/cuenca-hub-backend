"""Módulo de análisis de datos con PandasAI"""

import pandas as pd
import io
import base64
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import os

try:
    import pandasai as pai

    PANDASAI_AVAILABLE = True
except ImportError:
    PANDASAI_AVAILABLE = False

from .config import GEMINI_API_KEY
from .storage_service import StorageService, AnalysisSession


class DataAnalyzer:
    """Analizador de datos usando PandasAI"""

    def __init__(self):
        if not PANDASAI_AVAILABLE:
            raise ImportError(
                "PandasAI no está instalado. Ejecuta: pip install pandasai"
            )

        # Configurar PandasAI v3 con Gemini via LiteLLM
        from pandasai_litellm.litellm import LiteLLM

        os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

        llm = LiteLLM(model="gemini/gemini-2.5-flash")
        
        # PandasAI guarda en exports/charts - usar ruta absoluta
        base_dir = Path(__file__).parent.parent.parent  # cuenca-hub-backend/
        self.charts_dir = base_dir / "exports" / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Charts directory: {self.charts_dir}")
        
        pai.config.set({
            "llm": llm,
            "save_charts": True,
            "save_charts_path": str(self.charts_dir),
            "enable_cache": False,
            "verbose": False  # Reducir logs
        })
        print(f"🤖 PandasAI configurado para guardar en: {self.charts_dir}")
        
        # Storage service para gráficos
        try:
            self.storage = StorageService()
        except (ImportError, ValueError):
            self.storage = None  # Fallback sin Supabase

    def analyze_csv_data(self, csv_content: str, question: str, analysis_id: str = None) -> Dict[str, Any]:
        """Analiza datos CSV con pregunta en lenguaje natural"""
        try:
            # Cargar datos con pandas y crear SmartDataframe
            pandas_df = pd.read_csv(io.StringIO(csv_content))
            df = pai.SmartDataframe(pandas_df)

            # Análisis directo con PandasAI v3 - forzar generación de gráficos
            enhanced_question = f"{question}. Please create appropriate visualizations and charts for this analysis."
            result = df.chat(enhanced_question)

            # Procesar gráfico con patrón Big Tech
            chart_info = self._process_chart_upload(analysis_id)

            # Usar DataFrame original para metadatos
            original_df = pandas_df

            return {
                "analysis": str(result),
                "chart_url": chart_info.get("url"),
                "chart_cdn_url": chart_info.get("cdn_url"),
                "chart_id": chart_info.get("chart_id"),
                "chart": chart_info.get("base64") if not chart_info.get("url") else None,  # Fallback
                "data_shape": [int(x) for x in original_df.shape],
                "columns": original_df.columns.tolist(),
                "summary": self._generate_data_summary(original_df),
            }

        except Exception as e:
            return {
                "error": f"Error en análisis: {str(e)}",
                "analysis": None,
                "chart": None,
            }

    def analyze_excel_data(
        self, excel_content: bytes, question: str, sheet_name: str = None, analysis_id: str = None
    ) -> Dict[str, Any]:
        """Analiza datos Excel"""
        try:
            # Crear archivo temporal para Excel
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_file.write(excel_content)
                tmp_path = tmp_file.name

            try:
                # Cargar Excel con PandasAI v3
                df = pai.read_excel(tmp_path, sheet_name=sheet_name)

                # Análisis directo
                result = df.chat(question)

                # Buscar gráficos generados
                chart_path = self._find_latest_chart()
                chart_base64 = None
                if chart_path:
                    chart_base64 = self._encode_chart(chart_path)

                # Obtener DataFrame original para metadatos
                original_df = df.to_pandas() if hasattr(df, "to_pandas") else df

                return {
                    "analysis": str(result),
                    "chart": chart_base64,
                    "data_shape": [int(x) for x in original_df.shape],
                    "columns": original_df.columns.tolist(),
                    "summary": self._generate_data_summary(original_df),
                }
            finally:
                # Limpiar archivo temporal
                os.unlink(tmp_path)

        except Exception as e:
            return {
                "error": f"Error procesando Excel: {str(e)}",
                "analysis": None,
                "chart": None,
            }

    def quick_analysis(
        self, data_content: str, file_type: str = "csv", analysis_id: str = None
    ) -> Dict[str, Any]:
        """Análisis rápido automático"""
        try:
            # Cargar datos según tipo
            if file_type == "csv":
                df = pd.read_csv(io.StringIO(data_content))
            else:
                df = pd.read_excel(io.BytesIO(data_content))

            # Cargar con PandasAI v3
            if file_type == "csv":
                df = pai.read_csv(io.StringIO(data_content))
            else:
                # Crear archivo temporal para Excel
                with tempfile.NamedTemporaryFile(
                    suffix=".xlsx", delete=False
                ) as tmp_file:
                    tmp_file.write(data_content)
                    tmp_path = tmp_file.name

                try:
                    df = pai.read_excel(tmp_path)
                finally:
                    os.unlink(tmp_path)

            # Análisis único más eficiente
            question = "Provide a comprehensive analysis of this dataset including summary statistics, key patterns, correlations, and create appropriate visualizations"
            result = df.chat(question)

            # Obtener DataFrame original para metadatos
            original_df = df.to_pandas() if hasattr(df, "to_pandas") else df

            chart_path = self._find_latest_chart()
            chart_base64 = None
            if chart_path:
                chart_base64 = self._encode_chart(chart_path)

            analysis_result = {
                "analysis": str(result),
                "chart": chart_base64,
                "data_shape": [int(x) for x in original_df.shape],
                "columns": original_df.columns.tolist(),
                "summary": self._generate_data_summary(original_df),
            }

            return {
                "quick_insights": [analysis_result],
                "tldr": str(result)[:300] + "..."
                if len(str(result)) > 300
                else str(result),
            }

        except Exception as e:
            return {
                "error": f"Error en análisis rápido: {str(e)}",
                "quick_insights": [],
                "tldr": "Error en análisis",
            }

    def _find_latest_chart(self) -> Optional[str]:
        """Encuentra el gráfico más reciente en exports/charts"""
        chart_files = list(self.charts_dir.glob("temp_chart_*.png"))
        if chart_files:
            latest = max(chart_files, key=lambda p: p.stat().st_ctime)
            return str(latest)
        return None

    def _encode_chart(self, chart_path: str) -> str:
        """Codifica gráfico a base64"""
        try:
            with open(chart_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return None
    
    def _process_chart_upload(self, analysis_id: str = None) -> Dict[str, str]:
        """Procesa y sube gráfico con patrón Big Tech"""
        import time
        
        # Esperar un poco para que PandasAI genere el gráfico
        time.sleep(2)
        
        chart_path = self._find_latest_chart()
        if not chart_path:
            print(f"⚠️  No se encontró gráfico en {self.charts_dir}")
            return {"error": "No chart generated"}
        
        try:
            # Leer imagen
            with open(chart_path, "rb") as f:
                image_data = f.read()
            
            print(f"📊 Gráfico encontrado: {chart_path} ({len(image_data)} bytes)")
            
            # Si hay storage service, subir a Supabase
            if self.storage and analysis_id:
                print(f"☁️  Subiendo a Supabase con analysis_id: {analysis_id}")
                upload_result = self.storage.upload_chart(
                    image_data=image_data,
                    analysis_id=analysis_id,
                    metadata={
                        "file_size": len(image_data),
                        "format": "png",
                        "generated_by": "pandasai"
                    }
                )
                
                if not upload_result.get("error"):
                    print(f"✅ Subida exitosa: {upload_result.get('url')}")
                    return upload_result
                else:
                    print(f"❌ Error subida: {upload_result.get('error')}")
            
            # Fallback: base64
            print("📦 Usando fallback base64")
            return {
                "base64": base64.b64encode(image_data).decode(),
                "fallback": True
            }
            
        except Exception as e:
            print(f"❌ Error procesando gráfico: {e}")
            return {"error": str(e)}

    def _generate_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Genera resumen básico de los datos"""
        return {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "numeric_columns": int(len(df.select_dtypes(include=["number"]).columns)),
            "categorical_columns": int(len(df.select_dtypes(include=["object"]).columns)),
            "missing_values": int(df.isnull().sum().sum()),
            "data_types": {k: str(v) for k, v in df.dtypes.to_dict().items()},
        }

    def _generate_tldr(self, results: list) -> str:
        """Genera TLDR de múltiples análisis"""
        if not results:
            return "No se pudieron generar insights automáticos"

        insights = []
        for result in results:
            if result.get("analysis"):
                insights.append(str(result["analysis"])[:200])

        return (
            " | ".join(insights)
            if insights
            else "Análisis completado sin insights específicos"
        )

    def cleanup(self):
        """Limpia archivos temporales"""
        try:
            # Limpiar gráficos generados
            for chart_file in self.charts_dir.glob("temp_chart_*.png"):
                chart_file.unlink()
        except Exception:
            pass
