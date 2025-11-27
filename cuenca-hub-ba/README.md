# 🌊 Sistema KG-RAG para Restauración de Ríos

Sistema avanzado de Knowledge Graph RAG optimizado para consultas sobre investigación científica en restauración de ríos y tratamiento de aguas.

## 🎯 Características

- **Recuperación Híbrida**: Combina grafo de conocimiento + búsqueda vectorial + reranking
- **IA Conversacional**: Respuestas inteligentes con Gemini 2.0 Flash
- **Procesamiento Automático**: Ingesta PDFs científicos automáticamente
- **Fuentes Verificables**: Cada respuesta incluye documentos fuente específicos

## 🚀 Instalación

### Prerrequisitos
- Python 3.11+
- Poetry
- Docker (para Neo4j)
- API Key de Google Gemini

### Setup
```bash
# Instalar dependencias
poetry install

# Instalar modelo spaCy
poetry run python -m spacy download en_core_web_sm

# Configurar Neo4j (Docker)
docker run -d --name neo4j-scientific \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/hackathon \
  neo4j:latest
```

### Configuración
1. Edita `src/cuenca_hub_ba/config.py`
2. Reemplaza `GEMINI_API_KEY` con tu API key real
3. Coloca PDFs científicos en `data/`

## 🎮 Uso

```bash
# Sistema completo
poetry run python run_system.py

# Comandos específicos
poetry run python run_system.py check    # Verificar estado
poetry run python run_system.py ingest   # Solo ingesta
poetry run python run_system.py stats    # Estadísticas
```

## 💡 Ejemplos de Consultas

- "What are the main river restoration techniques?"
- "How can water quality be improved in contaminated rivers?"
- "What factors determine restoration success?"
- "What did Palmer conclude about ecological restoration?"

## 🏗️ Arquitectura

### Flujo de Datos
1. **Ingesta**: PDFs → Chunks → Neo4j (grafo) + ChromaDB (vectores)
2. **Consulta**: Query → Búsqueda híbrida → Reranking → Gemini → Respuesta

### Componentes
- **Neo4j**: Grafo de conocimiento (papers, autores, conceptos)
- **ChromaDB**: Base vectorial para similitud semántica
- **Gemini**: Generación de respuestas inteligentes
- **Cross-encoder**: Reranking de resultados

## 📊 Métricas del Sistema

- **Precisión**: Reducción de alucinaciones via grafo estructurado
- **Velocidad**: Modelos ligeros optimizados para M4 Pro
- **Escalabilidad**: Arquitectura modular para cientos de papers
- **Memoria**: <4GB RAM para 100+ documentos

## 📚 Documentación

- [Guía de Uso Detallada](GUIA_USO.md)
- [Arquitectura Técnica](src/cuenca_hub_ba/)

## 🤝 Contribuir

Este sistema fue desarrollado para el hackathon de TlamatIA, enfocado en soluciones de saneamiento de ríos y tratamiento de aguas.

---

**Desarrollado con ❤️ para la restauración de ecosistemas fluviales**