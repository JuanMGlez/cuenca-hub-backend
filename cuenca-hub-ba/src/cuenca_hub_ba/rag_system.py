"""Sistema KG-RAG simple y eficiente"""

from pathlib import Path
from typing import Dict, Any

from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.prompts import PromptTemplate


from .config import DATA_DIR, CHROMA_DB_DIR, setup_global_settings
from .document_processor import DocumentIngester
from .retriever import HybridRetriever
from .prompts import TRACEABLE_PROMPT
from .response_processor import ResponseHandler
from .data_analyzer import DataAnalyzer


class RAGSystem:
    def __init__(self):
        setup_global_settings()
        self.retriever = None
        self.query_engine = None
        self.response_handler = ResponseHandler()
        self.data_analyzer = DataAnalyzer()

    def check_ingestion_status(self) -> bool:
        """Verifica si ya se realizó la ingesta"""
        chroma_exists = Path(CHROMA_DB_DIR).exists()
        pdf_files = list(Path(DATA_DIR).glob("*.pdf"))

        if not pdf_files:
            return False

        if not chroma_exists:
            return False

        return True

    def run_ingestion(self):
        """Ejecuta el proceso de ingesta"""
        processor = DocumentIngester()
        try:
            processed_papers = processor.ingest_all_pdfs()
        except Exception:
            raise
        finally:
            processor.close()

    def initialize_query_engine(self):
        """Inicializa el motor de consultas"""
        self.retriever = HybridRetriever()

        # Crear prompt con trazabilidad de fuentes
        traceable_prompt = PromptTemplate(TRACEABLE_PROMPT)

        response_synthesizer = get_response_synthesizer(
            response_mode="compact", text_qa_template=traceable_prompt, use_async=False
        )

        # Crear retriever personalizado que implementa la interfaz correcta
        class CustomRetriever:
            def __init__(self, scientific_retriever):
                self.scientific_retriever = scientific_retriever

            def retrieve(self, query_str):
                return self.scientific_retriever.hybrid_retrieve(query_str)

        custom_retriever = CustomRetriever(self.retriever)

        self.query_engine = RetrieverQueryEngine(
            retriever=custom_retriever, response_synthesizer=response_synthesizer
        )
        


    def query(self, question: str) -> dict:
        """Query simple como la industria"""
        if not self.query_engine:
            raise ValueError("Sistema no inicializado")

        # Detectar si es consulta de análisis de datos
        data_keywords = ['analyze', 'chart', 'graph', 'correlation', 'statistics', 'data']
        if any(keyword in question.lower() for keyword in data_keywords):
            # Respuesta simple para consultas de datos sin archivo
            return {
                "question": question,
                "answer": "Para análisis de datos, por favor sube un archivo CSV o Excel junto con tu consulta.",
                "sources": [],
                "citations": [],
                "num_sources": 0,
                "analysis_mode": True,
                "traceability_report": {}
            }

        # Query normal de documentos
        # 1. Retrieval simple (ya incluye diversidad)
        nodes = self.retriever.hybrid_retrieve(question)

        # 2. LLM response
        response = self.query_engine.query(question)

        # 3. Post-process simple
        result = self.response_handler.process_query_response(nodes, str(response))

        return {
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
            "citations": result.get("citations", []),
            "num_sources": result["num_sources"],
            "analysis_mode": False,
            "traceability_report": result.get("traceability_report", {}),
        }

    def interactive_mode(self):
        """Modo interactivo para hacer consultas"""
        print("\n🎯 Modo interactivo activado")
        print("Escribe 'salir' para terminar\n")

        while True:
            try:
                question = input("❓ Tu pregunta: ").strip()

                if question.lower() in ["salir", "exit", "quit"]:
                    break

                if not question:
                    continue

                result = self.query(question)

                print("\n💡 Respuesta:")
                print(result["answer"])

                print(f"\n📚 Fuentes ({result['num_sources']}):")
                for source in result["sources"]:
                    print(f"[{source['number']}] {source['title']}")

                print("\n" + "=" * 80)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

        print("\n👋 ¡Hasta luego!")

    def run_test_query(self):
        """Ejecuta una consulta de prueba"""
        test_questions = [
            "What are the main river restoration techniques?",
            "What water treatment methods are mentioned?",
            "How can water quality be improved in contaminated rivers?",
        ]

        for question in test_questions:
            try:
                result = self.query(question)
            except Exception:
                pass

    def analyze_data(self, data_content: str, question: str, file_type: str = "csv", analysis_id: str = None) -> Dict[str, Any]:
        """Analiza datos con PandasAI"""
        if file_type == "csv":
            return self.data_analyzer.analyze_csv_data(data_content, question, analysis_id)
        else:
            return self.data_analyzer.analyze_excel_data(data_content.encode(), question, analysis_id=analysis_id)
    
    def quick_data_analysis(self, data_content: str, file_type: str = "csv", analysis_id: str = None) -> Dict[str, Any]:
        """Análisis rápido automático"""
        return self.data_analyzer.quick_analysis(data_content, file_type, analysis_id)
    

    
    def close(self):
        """Cierra el sistema"""
        if self.retriever:
            self.retriever.close()
        if hasattr(self, 'data_analyzer'):
            self.data_analyzer.cleanup()


def main():
    """Función principal"""
    system = RAGSystem()

    try:
        if not system.check_ingestion_status():
            system.run_ingestion()

        system.initialize_query_engine()
        system.run_test_query()
        system.interactive_mode()

    except Exception as e:
        print(f"❌ Error crítico: {e}")
    finally:
        system.close()


if __name__ == "__main__":
    main()
