"""
Servico de extracao de dados de conversas.

Sprint 53: Discovery Intelligence Pipeline.

Este modulo fornece extracao automatica de dados estruturados
de cada turno de conversa, incluindo:
- Classificacao de interesse
- Deteccao de objecoes
- Extracao de preferencias e restricoes
- Sugestao de proximo passo

Uso basico:
    from app.services.extraction import extrair_dados_conversa, ExtractionContext

    context = ExtractionContext(
        mensagem_medico="Oi, tenho interesse em vagas no RJ",
        resposta_julia="Otimo! Temos varias opcoes la",
        nome_medico="Dr. Carlos",
        especialidade_cadastrada="Cardiologia",
    )

    result = await extrair_dados_conversa(context)
    print(f"Interesse: {result.interesse.value}")
    print(f"Score: {result.interesse_score}")
"""

# Schemas
from .schemas import (
    ExtractionContext,
    ExtractionResult,
    Interesse,
    ProximoPasso,
    TipoObjecao,
    SeveridadeObjecao,
    Objecao,
)

# Extrator principal
from .extractor import extrair_dados_conversa

# Persistencia
from .persistence import (
    salvar_insight,
    salvar_memorias_extraidas,
    atualizar_dados_cliente,
    buscar_insights_conversa,
    buscar_insights_cliente,
    buscar_insights_campanha,
)

__all__ = [
    # Schemas
    "ExtractionContext",
    "ExtractionResult",
    "Interesse",
    "ProximoPasso",
    "TipoObjecao",
    "SeveridadeObjecao",
    "Objecao",
    # Extrator
    "extrair_dados_conversa",
    # Persistencia
    "salvar_insight",
    "salvar_memorias_extraidas",
    "atualizar_dados_cliente",
    "buscar_insights_conversa",
    "buscar_insights_cliente",
    "buscar_insights_campanha",
]
