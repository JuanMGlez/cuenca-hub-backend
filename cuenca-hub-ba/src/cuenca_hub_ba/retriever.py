"""Módulo de recuperación híbrida y reranking"""

from typing import List, Dict, Optional, Set
import re
from sentence_transformers import CrossEncoder

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from neo4j import GraphDatabase
import chromadb

from .config import (
    CHROMA_DB_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    RERANKER_MODEL,
    setup_global_settings,
)


class HybridRetriever:
    def __init__(self):
        setup_global_settings()

        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            "scientific_papers"
        )
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)

        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.vector_index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store, storage_context=storage_context
        )

        self.reranker = CrossEncoder(RERANKER_MODEL)

    def extract_entities_from_query(self, query: str) -> Dict[str, List[str]]:
        """Extrae entidades de la consulta"""
        entities = {"authors": [], "concepts": [], "keywords": []}

        author_patterns = [
            r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
            r"\b[A-Z]\. [A-Z][a-z]+\b",
        ]

        for pattern in author_patterns:
            matches = re.findall(pattern, query)
            entities["authors"].extend(matches)

        technical_words = re.findall(r"\b[A-Z][a-z]{3,}\b|\b[a-z]{5,}\b", query)
        entities["keywords"].extend(technical_words)

        return entities

    def search_knowledge_graph(self, entities: Dict[str, List[str]]) -> Set[str]:
        """Busca paper IDs relevantes en el grafo"""
        paper_ids = set()

        with self.neo4j_driver.session() as session:
            # Búsqueda por autores
            for author in entities["authors"]:
                result = session.run(
                    """
                    MATCH (p:Paper)-[:WRITTEN_BY]->(a:Author)
                    WHERE toLower(a.name) CONTAINS toLower($author)
                    RETURN p.id as paper_id
                """,
                    author=author,
                )

                for record in result:
                    paper_ids.add(record["paper_id"])

            # Búsqueda por palabras clave en títulos y conceptos
            all_keywords = entities["concepts"] + entities["keywords"]
            for keyword in all_keywords:
                if len(keyword) > 2:  # Reducir umbral
                    result = session.run(
                        """
                        MATCH (p:Paper)-[:ABOUT]->(c:Concept)
                        WHERE toLower(c.name) CONTAINS toLower($keyword)
                        RETURN p.id as paper_id
                        UNION
                        MATCH (p:Paper)
                        WHERE toLower(p.title) CONTAINS toLower($keyword)
                        RETURN p.id as paper_id
                    """,
                        keyword=keyword,
                    )

                    for record in result:
                        paper_ids.add(record["paper_id"])

        return paper_ids

    def vector_search_with_filter(
        self, query: str, paper_ids: Optional[Set[str]] = None, top_k: int = 20
    ) -> List:
        """Búsqueda vectorial con filtro opcional"""
        retriever = VectorIndexRetriever(
            index=self.vector_index, similarity_top_k=top_k
        )

        # ChromaDB no soporta filtros complejos, usar búsqueda simple
        # if paper_ids:
        #     filter_dict = {"paper_id": {"$in": list(paper_ids)}}
        #     retriever = VectorIndexRetriever(
        #         index=self.vector_index,
        #         similarity_top_k=top_k,
        #         filters=filter_dict
        #     )

        nodes = retriever.retrieve(query)
        return nodes

    def rerank_results(self, query: str, nodes: List, top_k: int = 5) -> List:
        """Aplica reranking usando cross-encoder"""
        if not nodes:
            return []

        # Extraer string de query si es QueryBundle
        query_str = query.query_str if hasattr(query, "query_str") else str(query)

        query_doc_pairs = []
        for node in nodes:
            query_doc_pairs.append([query_str, node.text])

        scores = self.reranker.predict(query_doc_pairs)
        node_score_pairs = list(zip(nodes, scores))
        node_score_pairs.sort(key=lambda x: x[1], reverse=True)

        return [pair[0] for pair in node_score_pairs[:top_k]]

    def hybrid_retrieve(self, query: str, top_k: int = 8) -> List:
        """Retrieval simple como la industria - sin overengineering"""
        query_str = query.query_str if hasattr(query, "query_str") else str(query)

        # 1. Vector search simple (como Google/OpenAI)
        retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=top_k * 2,  # Recuperar más para diversidad
        )
        nodes = retriever.retrieve(query_str)

        # 2. Diversidad simple: una fuente por documento
        seen_files = set()
        diverse_nodes = []
        for node in nodes:
            filename = node.node.metadata.get("filename", "unknown")
            if filename not in seen_files and len(diverse_nodes) < top_k:
                seen_files.add(filename)
                diverse_nodes.append(node)

        # 3. Rerank solo los diversos
        return self.rerank_results(query_str, diverse_nodes, top_k)

    def get_paper_metadata(self, paper_id: str) -> Dict:
        """Obtiene metadatos de un paper"""
        with self.neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (p:Paper {id: $paper_id})
                OPTIONAL MATCH (p)-[:WRITTEN_BY]->(a:Author)
                OPTIONAL MATCH (p)-[:ABOUT]->(c:Concept)
                RETURN p.title as title, p.filename as filename, p.doi as doi,
                       collect(DISTINCT a.name) as authors,
                       collect(DISTINCT c.name) as concepts
            """,
                paper_id=paper_id,
            )

            record = result.single()
            if record:
                return {
                    "title": record["title"],
                    "filename": record["filename"],
                    "doi": record["doi"],
                    "authors": record["authors"],
                    "concepts": record["concepts"],
                }
        return {}

    def close(self):
        """Cierra conexiones"""
        self.neo4j_driver.close()
