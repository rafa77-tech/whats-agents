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
from app.services.grupos.heuristica import calcular_score_heuristica, ResultadoHeuristica
from app.services.grupos.classificador import (
    classificar_batch_heuristica,
    classificar_mensagem_individual,
    classificar_batch_llm,
)
from app.services.grupos.classificador_llm import (
    classificar_com_llm,
    ResultadoClassificacaoLLM,
)
from app.services.grupos.extrator import (
    extrair_dados_mensagem,
    extrair_batch,
    VagaExtraida,
    DadosVagaExtraida,
    ConfiancaExtracao,
    ResultadoExtracao,
)
from app.services.grupos.validacoes import (
    validar_vaga_completa,
    validar_valor,
    validar_data,
    validar_horario,
    AlertaVaga,
)
from app.services.grupos.normalizador import (
    normalizar_para_busca,
    normalizar_hospital,
    normalizar_especialidade,
    normalizar_periodo,
    normalizar_setor,
    normalizar_vaga,
    normalizar_batch,
    ResultadoMatch,
    ResultadoNormalizacao,
)
from app.services.grupos.hospital_web import (
    buscar_hospital_web,
    criar_hospital,
    criar_hospital_minimo,
    normalizar_ou_criar_hospital,
    InfoHospitalWeb,
    ResultadoHospitalAuto,
)
from app.services.grupos.deduplicador import (
    calcular_hash_dedup,
    processar_deduplicacao,
    processar_batch_deduplicacao,
    listar_fontes_vaga,
    ResultadoDedup,
)

__all__ = [
    # Ingestão
    "ingerir_mensagem_grupo",
    # Heurística
    "calcular_score_heuristica",
    "ResultadoHeuristica",
    # Classificador heurística
    "classificar_batch_heuristica",
    "classificar_mensagem_individual",
    # Classificador LLM
    "classificar_batch_llm",
    "classificar_com_llm",
    "ResultadoClassificacaoLLM",
    # Extrator
    "extrair_dados_mensagem",
    "extrair_batch",
    "VagaExtraida",
    "DadosVagaExtraida",
    "ConfiancaExtracao",
    "ResultadoExtracao",
    # Validações
    "validar_vaga_completa",
    "validar_valor",
    "validar_data",
    "validar_horario",
    "AlertaVaga",
    # Normalizador
    "normalizar_para_busca",
    "normalizar_hospital",
    "normalizar_especialidade",
    "normalizar_periodo",
    "normalizar_setor",
    "normalizar_vaga",
    "normalizar_batch",
    "ResultadoMatch",
    "ResultadoNormalizacao",
    # Hospital Web
    "buscar_hospital_web",
    "criar_hospital",
    "criar_hospital_minimo",
    "normalizar_ou_criar_hospital",
    "InfoHospitalWeb",
    "ResultadoHospitalAuto",
    # Deduplicador
    "calcular_hash_dedup",
    "processar_deduplicacao",
    "processar_batch_deduplicacao",
    "listar_fontes_vaga",
    "ResultadoDedup",
]
