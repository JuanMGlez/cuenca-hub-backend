"""Módulo de ingesta y procesamiento de PDFs científicos"""

import re
import json
import fitz
import spacy
from typing import Dict, Tuple
from pathlib import Path

from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

# from llama_index.graph_stores.neo4j import Neo4jGraphStore
from neo4j import GraphDatabase
import chromadb

from .config import (
    DATA_DIR,
    CHROMA_DB_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    setup_global_settings,
    ensure_directories,
)


class DocumentIngester:
    def __init__(self):
        setup_global_settings()
        ensure_directories()
        self.load_papers_metadata()

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise OSError(
                "English spaCy model not found. Run: python -m spacy download en_core_web_sm"
            )

        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            "scientific_papers"
        )
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)

        self.node_parser = SentenceSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )

    def load_papers_metadata(self):
        """Carga metadata manual desde JSON (opcional)"""
        try:
            with open("papers_metadata.json", "r", encoding="utf-8") as f:
                self.papers_metadata = json.load(f)
        except FileNotFoundError:
            self.papers_metadata = {}

    def extract_pdf_text(self, pdf_path: str) -> Tuple[str, Dict]:
        """Extrae texto y metadatos de un PDF"""
        doc = fitz.open(pdf_path)
        text = ""
        filename = Path(pdf_path).name
        metadata = {"filename": filename}

        # 1. Usar metadatos PDF si son válidos
        pdf_metadata = doc.metadata or {}

        # Validar si el título PDF es válido (no archivos internos)
        pdf_title = pdf_metadata.get("title", "")
        if (
            pdf_title
            and len(pdf_title) > 15
            and not pdf_title.endswith(".indd")
            and "formados" not in pdf_title.lower()
            and not pdf_title.startswith("0")
        ):
            metadata["title"] = pdf_title
        else:
            # Extraer título del texto si PDF metadata es inválida
            title_from_text = self._extract_title_from_text(text)
            if title_from_text:
                metadata["title"] = title_from_text

        if pdf_metadata.get("author") and pdf_metadata["author"] != "Administrador":
            metadata["author"] = pdf_metadata["author"]
        if pdf_metadata.get("subject") and len(pdf_metadata["subject"]) > 20:
            metadata["journal"] = pdf_metadata["subject"]

        # 2. Extraer año del subject, filename o creationDate
        year_sources = [
            pdf_metadata.get("subject", ""),
            filename,
            pdf_metadata.get("creationDate", ""),
        ]
        for source in year_sources:
            year = self._extract_year_simple(source)
            if year:
                metadata["year"] = year
                break

        # 3. JSON manual como override final si existe
        if filename in self.papers_metadata:
            paper_meta = self.papers_metadata[filename]
            for key in ["title", "year", "journal"]:
                if paper_meta.get(key):
                    metadata[key] = paper_meta[key]
            if paper_meta.get("authors"):
                metadata["author"] = ", ".join(paper_meta["authors"])

        for page in doc:
            text += page.get_text()

        doc.close()

        return text, metadata

    def _extract_year_simple(self, text: str) -> str:
        """Extrae año de cualquier texto"""
        year_match = re.search(r"\b(19|20)\d{2}\b", text)
        return year_match.group() if year_match else ""

    def _extract_title_from_text(self, text: str) -> str:
        """Extrae título del texto - casos específicos conocidos"""
        lines = [line.strip() for line in text.split("\n")[:30] if line.strip()]

        # Casos específicos conocidos
        for line in lines:
            # Para v17s1a3.pdf
            if "multimétrico para evaluar contaminación" in line.lower():
                return line
            # Para annurev-ecolsys
            if "ecological restoration of streams and rivers" in line.lower():
                return line
            # Patrón general: línea larga con palabras clave
            if (
                30 < len(line) < 150
                and any(
                    keyword in line.lower()
                    for keyword in [
                        "restoration",
                        "river",
                        "water",
                        "ecological",
                        "contaminación",
                        "análisis",
                    ]
                )
                and line.count(" ") > 5
            ):
                return line

        return ""

        # Extraer conceptos clave
        doc = self.nlp(text[:2000])
        concepts = []
        for ent in doc.ents:
            if (
                ent.label_ in ["ORG", "PRODUCT", "EVENT", "WORK_OF_ART"]
                and len(ent.text) > 3
            ):
                concepts.append(ent.text.lower())

        concepts_str = [str(concept) for concept in concepts if concept]
        metadata["concepts"] = ", ".join(concepts_str[:5]) if concepts_str else ""

    def create_knowledge_graph(self, metadata: Dict, paper_id: str):
        """Crea nodos y relaciones en Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run(
                """
                MERGE (p:Paper {id: $paper_id})
                SET p.title = $title,
                    p.filename = $filename,
                    p.doi = $doi
            """,
                paper_id=paper_id,
                title=metadata.get("title", ""),
                filename=metadata.get("filename", ""),
                doi=metadata.get("doi", ""),
            )

            authors = metadata.get("author", "").split(",")
            for author in authors:
                author = author.strip()
                if author:
                    session.run(
                        """
                        MERGE (a:Author {name: $author})
                        MERGE (p:Paper {id: $paper_id})
                        MERGE (p)-[:WRITTEN_BY]->(a)
                    """,
                        author=author,
                        paper_id=paper_id,
                    )

            # Procesar conceptos desde string
            concepts_str = metadata.get("concepts", "")
            if concepts_str:
                concepts_list = [
                    c.strip() for c in concepts_str.split(",") if c.strip()
                ]
                for concept in concepts_list:
                    session.run(
                        """
                        MERGE (c:Concept {name: $concept})
                        MERGE (p:Paper {id: $paper_id})
                        MERGE (p)-[:ABOUT]->(c)
                    """,
                        concept=concept,
                        paper_id=paper_id,
                    )

    def process_pdf(self, pdf_path: str) -> str:
        """Procesa un PDF completo"""
        text, metadata = self.extract_pdf_text(pdf_path)
        paper_id = f"paper_{Path(pdf_path).stem}"

        document = Document(text=text, metadata={**metadata, "paper_id": paper_id})

        nodes = self.node_parser.get_nodes_from_documents([document])

        for node in nodes:
            node.metadata["paper_id"] = paper_id

        self.create_knowledge_graph(metadata, paper_id)

        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        VectorStoreIndex(nodes, storage_context=storage_context)

        return paper_id

    def ingest_all_pdfs(self):
        """Ingesta todos los PDFs en el directorio de datos"""
        pdf_files = list(Path(DATA_DIR).glob("*.pdf"))

        if not pdf_files:
            return

        processed_papers = []
        for pdf_path in pdf_files:
            try:
                paper_id = self.process_pdf(str(pdf_path))
                processed_papers.append(paper_id)
            except Exception:
                pass

        return processed_papers

    def close(self):
        """Cierra conexiones"""
        self.neo4j_driver.close()
