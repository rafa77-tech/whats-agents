"""
Fragmentos do agente Julia.

NOTA: Renomeado de templates para fragmentos (Sprint 32).
"""
from .aberturas import (
    SAUDACOES,
    APRESENTACOES,
    CONTEXTOS,
    GANCHOS,
    montar_abertura_completa,
    gerar_abertura_texto_unico,
    FragmentoAbertura,
    contar_variacoes,
)
from .mensagens import (
    formatar_primeiro_contato,
    obter_saudacao_especialidade,
    MENSAGEM_PRIMEIRO_CONTATO,
)
