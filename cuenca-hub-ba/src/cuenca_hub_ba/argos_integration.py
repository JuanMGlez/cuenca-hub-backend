"""
Integración Argos - Sistema de Visualización Avanzada para Análisis Satelital
Estándares UX/UI 2025/2026 para Ingeniería de Datos
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime

class ArgosVisualizationEngine:
    """Motor de visualización para datos satelitales con estándares UX/UI avanzados"""
    
    def __init__(self):
        self.color_palette = {
            "primary": "#0066CC",
            "success": "#00C851", 
            "warning": "#FF8800",
            "danger": "#FF4444",
            "info": "#33B5E5",
            "clean_water": "#4FC3F7",
            "moderate_water": "#FFB74D",
            "polluted_water": "#E57373",
            "critical_water": "#F44336"
        }
    
    def generate_dashboard_config(self, sentinel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera configuración de dashboard para Argos con métricas satelitales"""
        
        if "error" in sentinel_data:
            return self._error_dashboard(sentinel_data["error"])
        
        indicators = sentinel_data.get("indicators", {})
        metadata = sentinel_data.get("metadata", {})
        
        return {
            "dashboard_id": f"sentinel2_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": "Análisis Satelital Cuenca - Sentinel-2",
            "subtitle": f"Área: {metadata.get('aoi_water_area_ha', 0)} ha | {metadata.get('acquisition_date', 'N/A')}",
            "layout": "grid_4x3",
            "components": [
                self._create_health_score_card(indicators),
                self._create_eutrophication_chart(indicators.get("eutrophication_ndci", {})),
                self._create_vegetation_alert(indicators.get("macrophytes_fai", {})),
                self._create_turbidity_gauge(indicators.get("turbidity_ndti", {})),
                self._create_cyanobacteria_risk(indicators.get("cyanobacteria_risk", {})),
                self._create_spatial_overview(metadata),
                self._create_quality_metrics(sentinel_data.get("quality_control", {})),
                self._create_trend_analysis(),
                self._create_recommendations(indicators)
            ],
            "theme": "satellite_analysis",
            "refresh_interval": 300000  # 5 minutos
        }
    
    def _create_health_score_card(self, indicators: Dict) -> Dict:
        """Tarjeta principal con score de salud general"""
        ndci = indicators.get("eutrophication_ndci", {})
        fai = indicators.get("macrophytes_fai", {})
        
        # Algoritmo de score simplificado
        score = 100
        if ndci.get("classification_breakdown_ha"):
            critical_ha = ndci["classification_breakdown_ha"].get("critical_hypertrophic", 0)
            high_ha = ndci["classification_breakdown_ha"].get("high_eutrophic", 0)
            score -= (critical_ha * 2.0 + high_ha * 1.0)
        
        if fai.get("percentage_coverage", 0) > 10:
            score -= fai["percentage_coverage"] * 1.5
            
        score = max(0, min(100, score))
        
        return {
            "type": "metric_card",
            "position": {"row": 1, "col": 1, "span": 2},
            "config": {
                "title": "Índice de Salud Hídrica",
                "value": round(score, 1),
                "unit": "/100",
                "trend": self._calculate_trend(score),
                "color": self._get_health_color(score),
                "icon": "water_drop",
                "subtitle": self._get_health_status(score)
            }
        }
    
    def _create_eutrophication_chart(self, ndci_data: Dict) -> Dict:
        """Gráfico de barras apiladas para eutrofización"""
        breakdown = ndci_data.get("classification_breakdown_ha", {})
        
        return {
            "type": "stacked_bar_chart",
            "position": {"row": 1, "col": 3, "span": 2},
            "config": {
                "title": "Clasificación Trófica (ha)",
                "data": [
                    {"label": "Oligotrófico", "value": breakdown.get("clean_oligotrophic", 0), "color": self.color_palette["clean_water"]},
                    {"label": "Mesotrófico", "value": breakdown.get("moderate_mesotrophic", 0), "color": self.color_palette["moderate_water"]},
                    {"label": "Eutrófico", "value": breakdown.get("high_eutrophic", 0), "color": self.color_palette["polluted_water"]},
                    {"label": "Hipertrófico", "value": breakdown.get("critical_hypertrophic", 0), "color": self.color_palette["critical_water"]}
                ],
                "orientation": "horizontal",
                "show_values": True
            }
        }
    
    def _create_vegetation_alert(self, fai_data: Dict) -> Dict:
        """Alerta de vegetación flotante"""
        coverage = fai_data.get("percentage_coverage", 0)
        status = fai_data.get("invasion_status", "MONITOR")
        
        return {
            "type": "alert_card",
            "position": {"row": 2, "col": 1, "span": 1},
            "config": {
                "title": "Lirio Acuático",
                "value": f"{coverage:.1f}%",
                "status": status,
                "color": self.color_palette["danger"] if status == "CRITICAL" else self.color_palette["warning"],
                "icon": "eco",
                "area_ha": fai_data.get("floating_vegetation_area_ha", 0)
            }
        }
    
    def _create_turbidity_gauge(self, ndti_data: Dict) -> Dict:
        """Medidor circular de turbidez"""
        mean_value = ndti_data.get("mean_value", 0)
        status = ndti_data.get("sediment_load_status", "NORMAL")
        
        return {
            "type": "circular_gauge",
            "position": {"row": 2, "col": 2, "span": 1},
            "config": {
                "title": "Turbidez (NDTI)",
                "value": mean_value,
                "min": -0.1,
                "max": 0.3,
                "thresholds": [
                    {"value": 0.0, "color": self.color_palette["clean_water"]},
                    {"value": 0.1, "color": self.color_palette["moderate_water"]},
                    {"value": 0.15, "color": self.color_palette["polluted_water"]}
                ],
                "status": status
            }
        }
    
    def _create_cyanobacteria_risk(self, cyano_data: Dict) -> Dict:
        """Indicador de riesgo de cianobacterias"""
        ratio = cyano_data.get("mean_ratio_2bda", 0)
        risk_area = cyano_data.get("high_risk_area_ha", 0)
        
        risk_level = "ALTO" if ratio > 1.1 else "MEDIO" if ratio > 1.0 else "BAJO"
        
        return {
            "type": "risk_indicator",
            "position": {"row": 2, "col": 3, "span": 1},
            "config": {
                "title": "Riesgo Cianobacterias",
                "ratio": ratio,
                "risk_level": risk_level,
                "affected_area_ha": risk_area,
                "color": self._get_risk_color(risk_level),
                "icon": "warning"
            }
        }
    
    def _create_spatial_overview(self, metadata: Dict) -> Dict:
        """Vista espacial del área analizada"""
        return {
            "type": "spatial_map",
            "position": {"row": 2, "col": 4, "span": 1},
            "config": {
                "title": "Área de Estudio",
                "area_ha": metadata.get("aoi_water_area_ha", 0),
                "resolution_m": metadata.get("spatial_resolution_m", 10),
                "satellite": "Sentinel-2",
                "processing_level": metadata.get("processing_level", "L2A")
            }
        }
    
    def _create_quality_metrics(self, qc_data: Dict) -> Dict:
        """Métricas de control de calidad"""
        return {
            "type": "quality_panel",
            "position": {"row": 3, "col": 1, "span": 2},
            "config": {
                "title": "Control de Calidad",
                "metrics": [
                    {"label": "Píxeles Válidos", "value": qc_data.get("valid_water_pixels", 0)},
                    {"label": "Cobertura Nubes", "value": f"{qc_data.get('cloud_probability_percent', 0)}%"},
                    {"label": "Confiabilidad", "value": self._calculate_reliability(qc_data)}
                ]
            }
        }
    
    def _create_trend_analysis(self) -> Dict:
        """Análisis de tendencias temporales"""
        return {
            "type": "trend_chart",
            "position": {"row": 3, "col": 3, "span": 1},
            "config": {
                "title": "Tendencia Temporal",
                "placeholder": "Datos históricos requeridos",
                "chart_type": "line"
            }
        }
    
    def _create_recommendations(self, indicators: Dict) -> Dict:
        """Panel de recomendaciones automáticas"""
        recommendations = []
        
        # Análisis automático de recomendaciones
        ndci = indicators.get("eutrophication_ndci", {})
        fai = indicators.get("macrophytes_fai", {})
        
        if ndci.get("classification_breakdown_ha", {}).get("critical_hypertrophic", 0) > 5:
            recommendations.append("🚨 Implementar control de nutrientes urgente")
        
        if fai.get("invasion_status") == "CRITICAL":
            recommendations.append("🌿 Programa de remoción de lirio acuático")
        
        if not recommendations:
            recommendations.append("✅ Condiciones dentro de parámetros normales")
        
        return {
            "type": "recommendations_panel",
            "position": {"row": 3, "col": 4, "span": 1},
            "config": {
                "title": "Recomendaciones",
                "items": recommendations
            }
        }
    
    def _error_dashboard(self, error_msg: str) -> Dict:
        """Dashboard de error"""
        return {
            "dashboard_id": "error_dashboard",
            "title": "Error en Análisis",
            "components": [{
                "type": "error_card",
                "config": {"message": error_msg, "color": self.color_palette["danger"]}
            }]
        }
    
    def _get_health_color(self, score: float) -> str:
        if score >= 80: return self.color_palette["success"]
        elif score >= 60: return self.color_palette["warning"] 
        else: return self.color_palette["danger"]
    
    def _get_health_status(self, score: float) -> str:
        if score >= 80: return "Excelente"
        elif score >= 60: return "Bueno"
        elif score >= 40: return "Regular"
        else: return "Crítico"
    
    def _get_risk_color(self, risk_level: str) -> str:
        colors = {"BAJO": self.color_palette["success"], "MEDIO": self.color_palette["warning"], "ALTO": self.color_palette["danger"]}
        return colors.get(risk_level, self.color_palette["info"])
    
    def _calculate_trend(self, current_score: float) -> str:
        # Placeholder para cálculo de tendencia
        return "stable"
    
    def _calculate_reliability(self, qc_data: Dict) -> str:
        cloud_cover = qc_data.get("cloud_probability_percent", 0)
        valid_pixels = qc_data.get("valid_water_pixels", 0)
        
        if cloud_cover < 10 and valid_pixels > 1000:
            return "Alta"
        elif cloud_cover < 20 and valid_pixels > 500:
            return "Media"
        else:
            return "Baja"