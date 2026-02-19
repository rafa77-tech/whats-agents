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
    mergear_hospitais,
    normalizar_ou_criar_hospital,
    hospital_tem_endereco_completo,
    InfoHospitalWeb,
    ResultadoHospitalAuto,
)
from app.services.grupos.deduplicador import (
    calcular_hash_dedup,
    processar_deduplicacao,
    listar_fontes_vaga,
    ResultadoDedup,
)
from app.services.grupos.importador import (
    calcular_confianca_geral,
    validar_para_importacao,
    decidir_acao,
    criar_vaga_principal,
    processar_importacao,
    listar_vagas_para_revisao,
    aprovar_vaga_revisao,
    rejeitar_vaga_revisao,
    obter_estatisticas_importacao,
    ScoreConfianca,
    ResultadoValidacao,
    AcaoImportacao,
    ResultadoImportacao,
    THRESHOLD_IMPORTAR,
    THRESHOLD_REVISAR,
)
from app.services.grupos.fila import (
    EstagioPipeline,
    ItemFila,
    enfileirar_mensagem,
    enfileirar_batch,
    buscar_proximos_pendentes,
    buscar_item_por_mensagem,
    atualizar_estagio,
    marcar_como_finalizado,
    marcar_como_descartado,
    obter_estatisticas_fila,
    obter_itens_travados,
    reprocessar_erros,
    limpar_finalizados,
)
from app.services.grupos.pipeline_worker import (
    PipelineGrupos,
    ResultadoPipeline,
    mapear_acao_para_estagio,
    THRESHOLD_HEURISTICA,
    THRESHOLD_HEURISTICA_ALTO,
    THRESHOLD_LLM,
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
    "mergear_hospitais",
    "hospital_tem_endereco_completo",
    "normalizar_ou_criar_hospital",
    "InfoHospitalWeb",
    "ResultadoHospitalAuto",
    # Deduplicador
    "calcular_hash_dedup",
    "processar_deduplicacao",
    "listar_fontes_vaga",
    "ResultadoDedup",
    # Importador
    "calcular_confianca_geral",
    "validar_para_importacao",
    "decidir_acao",
    "criar_vaga_principal",
    "processar_importacao",
    "listar_vagas_para_revisao",
    "aprovar_vaga_revisao",
    "rejeitar_vaga_revisao",
    "obter_estatisticas_importacao",
    "ScoreConfianca",
    "ResultadoValidacao",
    "AcaoImportacao",
    "ResultadoImportacao",
    "THRESHOLD_IMPORTAR",
    "THRESHOLD_REVISAR",
    # Fila de processamento
    "EstagioPipeline",
    "ItemFila",
    "enfileirar_mensagem",
    "enfileirar_batch",
    "buscar_proximos_pendentes",
    "buscar_item_por_mensagem",
    "atualizar_estagio",
    "marcar_como_finalizado",
    "marcar_como_descartado",
    "obter_estatisticas_fila",
    "obter_itens_travados",
    "reprocessar_erros",
    "limpar_finalizados",
    # Pipeline Worker
    "PipelineGrupos",
    "ResultadoPipeline",
    "mapear_acao_para_estagio",
    "THRESHOLD_HEURISTICA",
    "THRESHOLD_HEURISTICA_ALTO",
    "THRESHOLD_LLM",
]
