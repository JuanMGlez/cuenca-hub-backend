#!/usr/bin/env python3
"""Script de ejecución principal del sistema KG-RAG"""

import sys
from src.cuenca_hub_ba.rag_system import main
from src.cuenca_hub_ba.utils import system_health_check, clear_databases, get_system_stats
from src.cuenca_hub_ba.document_processor import DocumentIngester

def run_ingestion():
    """Solo ejecuta la ingesta"""
    processor = DocumentIngester()
    try:
        processor.ingest_all_pdfs()
    finally:
        processor.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "check":
            system_health_check()
        elif command == "clear":
            clear_databases()
        elif command == "stats":
            stats = get_system_stats()
            for key, value in stats.items():
                print(f"{key}: {value}")
        elif command == "ingest":
            run_ingestion()
        else:
            print("Comandos disponibles: check, clear, stats, ingest")
    else:
        main()