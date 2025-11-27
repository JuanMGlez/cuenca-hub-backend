"""Configuración global del sistema KG-RAG"""

import os
from dotenv import load_dotenv  # Importar dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.gemini import Gemini

# 1. Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de directorios
DATA_DIR = "./data"
CHROMA_DB_DIR = "./chroma_db"

# Configuración Neo4j (Obtenida del .env)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")  # Ya no está hardcodeada

# API Key de Gemini (Obtenida del .env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# Configuración de modelos (multilingüe)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"
# Nota: Verifica si tienes acceso a 'gemini-2.5-flash', el estándar actual suele ser 'gemini-1.5-flash'
LLM_MODEL_NAME = "models/gemini-2.5-flash"

# Configuración de chunking
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

# Configuración balanceada: calidad + profundidad
HIGH_QUALITY_THRESHOLD = 0.3
EXCELLENT_THRESHOLD = 0.7
MIN_SOURCES = 3
MAX_SOURCES = 8
OPTIMAL_SOURCES = 5


def setup_global_settings():
    """Configura los settings globales de LlamaIndex"""
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL, trust_remote_code=True
    )

    # Configurar Gemini LLM
    if GEMINI_API_KEY:
        Settings.llm = Gemini(
            model=LLM_MODEL_NAME,
            api_key=GEMINI_API_KEY,
            temperature=0.1,
            max_tokens=2000,
            system_instruction="Eres un consultor senior especializado en soluciones prácticas para restauración fluvial. ENFOQUE: Proporciona soluciones ESPECÍFICAS, CONCRETAS y ACCIONABLES. REGLAS: 1) SOLO usa referencias [1], [2], [3] que existan en los documentos, 2) Para cada problema, da soluciones técnicas detalladas con pasos específicos, 3) Incluye tecnologías, métodos y parámetros cuantitativos cuando estén disponibles, 4) Sé BREVE pero ÚTIL - evita generalidades. ESTRUCTURA: Problema identificado → Solución técnica específica → Pasos de implementación.",
        )
    else:
        print(
            "⚠️  ADVERTENCIA: GEMINI_API_KEY no configurada en el archivo .env. Solo retrieval disponible."
        )

    Settings.chunk_size = CHUNK_SIZE
    Settings.chunk_overlap = CHUNK_OVERLAP


def get_llm():
    """Obtiene instancia del LLM configurado"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no encontrada. Revisa tu archivo .env")

    return Gemini(
        model=LLM_MODEL_NAME,
        api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_tokens=2000,
    )


def ensure_directories():
    """Crea directorios necesarios si no existen"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
