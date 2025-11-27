"""Response processor - Handles LLM output and source management"""

import re
from typing import Dict, List


class ResponseHandler:
    """Handles LLM responses and source references"""

    def process_query_response(self, retrieved_nodes, response_text: str) -> Dict:
        """Procesamiento simple como la industria"""

        # 1. Fuentes únicas (una por documento)
        sources = self._get_unique_sources(retrieved_nodes)

        # 2. Limpiar referencias inválidas
        clean_text = self._fix_references(response_text, len(sources))

        # 3. Generar citas
        citations = self._generate_citations(sources)

        # 4. Analizar referencias para traceability
        refs = re.findall(r"\[(\d+)\]", clean_text)
        valid_refs = [int(r) for r in refs if 1 <= int(r) <= len(sources)]

        return {
            "answer": clean_text,
            "sources": sources,
            "citations": citations,
            "num_sources": len(sources),
            "traceability_report": {
                "total_references": len(refs),
                "valid_references": list(set(valid_refs)),
                "reliability_score": min(60 + len(set(valid_refs)) * 20, 100)
                if valid_refs
                else 20,
                "has_traceability": len(refs) > 0,
            },
        }

    def _get_unique_sources(self, nodes) -> List[Dict]:
        """Una fuente por documento - simple con corrección de títulos"""
        seen = set()
        sources = []

        for node in nodes:
            filename = node.node.metadata.get("filename", "unknown")
            if filename not in seen:
                seen.add(filename)

                # Corregir títulos conocidos problemáticos
                title = node.node.metadata.get("title", "Sin título")
                title = self._fix_known_bad_titles(filename, title)

                sources.append(
                    {
                        "number": len(sources) + 1,
                        "filename": filename,
                        "title": title,
                        "preview": node.node.text[:150] + "...",
                    }
                )

        return sources

    def _fix_known_bad_titles(self, filename: str, title: str) -> str:
        """Corrige títulos conocidos problemáticos"""
        fixes = {
            "v17s1a3.pdf": "Análisis multimétrico para evaluar contaminación en el río Lerma y lago de Chapala, México",
            "v70n1a3.pdf": "Gestión integrada del agua en la cuenca Lerma-Chapala-Santiago",
            "annurev-ecolsys-120213-091935.pdf": "Ecological Restoration of Streams and Rivers: Shifting Strategies and Shifting Goals",
        }

        if filename in fixes:
            return fixes[filename]

        # Si el título parece inválido, usar filename como fallback
        if (
            title in ["Sin título", ""]
            or title.endswith(".indd")
            or "formados" in title.lower()
        ):
            return filename.replace(".pdf", "").replace("_", " ").title()

        return title

    def _fix_references(self, text: str, max_refs: int) -> str:
        """Fix referencias y generar citas"""
        # Limpiar referencias inválidas
        cleaned = re.sub(
            r"\[(\d+)\]",
            lambda m: m.group(0) if int(m.group(1)) <= max_refs else "",
            text,
        )
        return cleaned

    def _generate_citations(self, sources: List[Dict]) -> List[str]:
        """Genera citas académicas"""
        citations = []
        for source in sources:
            title = source.get("title", "Sin título")
            filename = source.get("filename", "")
            citation = f"[{source['number']}] {title} ({filename})"
            citations.append(citation)
        return citations
