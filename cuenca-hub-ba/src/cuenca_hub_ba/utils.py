"""Utilidades para el sistema KG-RAG"""

from pathlib import Path
from neo4j import GraphDatabase
import chromadb

from .config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, CHROMA_DB_DIR, DATA_DIR


def check_neo4j_connection():
    """Verifica la conexión con Neo4j"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                return True
    except Exception:
        return False
    finally:
        if "driver" in locals():
            driver.close()


def check_chromadb():
    """Verifica ChromaDB"""
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        collections = client.list_collections()
        return True
    except Exception:
        return False


def get_system_stats():
    """Obtiene estadísticas del sistema"""
    stats = {}

    pdf_files = list(Path(DATA_DIR).glob("*.pdf"))
    stats["pdf_count"] = len(pdf_files)

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("MATCH (p:Paper) RETURN count(p) as count")
            stats["papers_in_graph"] = result.single()["count"]

            result = session.run("MATCH (a:Author) RETURN count(a) as count")
            stats["authors_in_graph"] = result.single()["count"]

            result = session.run("MATCH (c:Concept) RETURN count(c) as count")
            stats["concepts_in_graph"] = result.single()["count"]

        driver.close()
    except Exception:
        stats.update(
            {"papers_in_graph": 0, "authors_in_graph": 0, "concepts_in_graph": 0}
        )

    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        collection = client.get_collection("scientific_papers")
        stats["chunks_in_vector_db"] = collection.count()
    except Exception:
        stats["chunks_in_vector_db"] = 0

    return stats


def clear_databases():
    """Limpia las bases de datos"""
    response = input(
        "⚠️  ¿Estás seguro de que quieres limpiar todas las bases de datos? (sí/no): "
    )
    if response.lower() not in ["sí", "si", "yes", "y"]:
        return

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
    except Exception:
        pass

    try:
        if Path(CHROMA_DB_DIR).exists():
            import shutil

            shutil.rmtree(CHROMA_DB_DIR)
    except Exception:
        pass


def system_health_check():
    """Verifica el estado completo del sistema"""
    neo4j_ok = check_neo4j_connection()
    chroma_ok = check_chromadb()

    stats = get_system_stats()

    if neo4j_ok and chroma_ok and stats["papers_in_graph"] > 0:
        return True
    else:
        return False
