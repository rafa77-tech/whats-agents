"""
Entry point para executar workers.
"""
import asyncio
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Executa worker baseado no argumento."""
    if len(sys.argv) < 2:
        print("Uso: python -m app.workers <worker_name>")
        print("Workers disponíveis: fila, scheduler")
        sys.exit(1)
    
    worker_name = sys.argv[1]
    
    if worker_name == "fila":
        from app.workers.fila_worker import processar_fila
        logger.info("Iniciando worker de fila...")
        asyncio.run(processar_fila())
    elif worker_name == "scheduler":
        from app.workers.scheduler import scheduler_loop
        logger.info("Iniciando scheduler...")
        asyncio.run(scheduler_loop())
    else:
        logger.error(f"Worker desconhecido: {worker_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()

