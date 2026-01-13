"""
Group Entry Engine - Sistema seguro de entrada em grupos WhatsApp.

Sprint 25/26 - E12

Este módulo gerencia entrada segura em grupos WhatsApp para chips do tipo 'listener'.
Integra com Trust Score, respeita fases de warmup e distribui carga entre múltiplos chips.

Componentes:
- importer: Importa links de CSV/Excel
- validator: Valida links antes de tentar entrar
- scheduler: Agenda entradas respeitando limites por fase
- worker: Processa fila de entrada
- chip_selector: Seleciona chip ideal para cada entrada
- discovery: Descobre novas fontes de grupos (Sprint 26)
- crawler: Crawling de fontes conhecidas (Sprint 26)
"""

from app.services.group_entry.importer import (
    importar_csv,
    importar_excel,
    importar_diretorio,
    extrair_invite_code,
)
from app.services.group_entry.validator import (
    validar_link,
    validar_links_pendentes,
)
from app.services.group_entry.scheduler import (
    agendar_entrada,
    agendar_lote,
)
from app.services.group_entry.worker import (
    processar_fila,
    processar_entrada,
)
from app.services.group_entry.chip_selector import (
    selecionar_chip_para_grupo,
    listar_chips_disponiveis,
    buscar_config,
)
from app.services.group_entry.discovery import (
    source_discovery,
    SourceDiscovery,
)
from app.services.group_entry.crawler import (
    crawler_manager,
    CrawlerManager,
)

__all__ = [
    # Importer
    "importar_csv",
    "importar_excel",
    "importar_diretorio",
    "extrair_invite_code",
    # Validator
    "validar_link",
    "validar_links_pendentes",
    # Scheduler
    "agendar_entrada",
    "agendar_lote",
    # Worker
    "processar_fila",
    "processar_entrada",
    # Chip Selector
    "selecionar_chip_para_grupo",
    "listar_chips_disponiveis",
    "buscar_config",
    # Discovery (Sprint 26)
    "source_discovery",
    "SourceDiscovery",
    # Crawler (Sprint 26)
    "crawler_manager",
    "CrawlerManager",
]
