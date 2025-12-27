"""
Módulo de processamento de mensagens de grupos WhatsApp.

Responsável por:
- Ingestão de mensagens
- Classificação de ofertas
- Extração de dados estruturados
- Normalização com entidades do banco
- Deduplicação de vagas
- Importação para tabela de vagas
"""

from app.services.grupos.ingestor import ingerir_mensagem_grupo

__all__ = [
    "ingerir_mensagem_grupo",
]
