"""
Pipeline principal de extração de vagas v2.

Orquestra todos os extratores para processar uma mensagem completa.

Sprint 40 - E08: Integração e Pipeline
"""

import time
from datetime import date
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import (
    ResultadoExtracaoV2,
)
from app.services.grupos.extrator_v2.parser_mensagem import (
    parsear_mensagem,
)
from app.services.grupos.extrator_v2.extrator_hospitais import extrair_hospitais
from app.services.grupos.extrator_v2.extrator_datas import extrair_datas_periodos
from app.services.grupos.extrator_v2.extrator_valores import extrair_valores
from app.services.grupos.extrator_v2.extrator_contato import extrair_contato
from app.services.grupos.extrator_v2.gerador_vagas import (
    gerar_vagas,
    validar_vagas,
    deduplicar_vagas,
)
from app.services.grupos.extrator_v2.exceptions import (
    ExtracaoError,
)

logger = get_logger(__name__)


async def extrair_vagas_v2(
    texto: str,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
    data_referencia: Optional[date] = None,
) -> ResultadoExtracaoV2:
    """
    Extrai vagas atômicas de uma mensagem de grupo.

    Pipeline:
    1. Parser de mensagem (separa seções)
    2. Extrator de hospitais
    3. Extrator de datas/períodos
    4. Extrator de valores
    5. Extrator de contato
    6. Gerador de vagas (combina tudo)
    7. Validação e deduplicação

    Args:
        texto: Texto bruto da mensagem
        mensagem_id: ID da mensagem (para rastreabilidade)
        grupo_id: ID do grupo (para rastreabilidade)
        data_referencia: Data de referência para "hoje" e "amanhã"

    Returns:
        ResultadoExtracaoV2 com vagas e metadados

    Example:
        >>> resultado = await extrair_vagas_v2(
        ...     texto="📍 Hospital ABC\\n🗓 26/01 Manhã\\n💰 R$ 1.700",
        ...     mensagem_id=uuid4(),
        ...     grupo_id=uuid4()
        ... )
        >>> len(resultado.vagas)
        1
    """
    inicio = time.time()
    warnings: list[str] = []

    # Validação inicial
    if not texto or not texto.strip():
        return ResultadoExtracaoV2(
            erro="mensagem_vazia",
            tempo_processamento_ms=0
        )

    try:
        # 1. Parser de mensagem
        msg_parsed = parsear_mensagem(texto)

        # 2. Extração de hospitais
        hospitais = extrair_hospitais(msg_parsed.secoes_local)
        if not hospitais:
            # Tentar extrair do texto completo
            hospitais = extrair_hospitais([texto])
            if hospitais:
                warnings.append("hospital_extraido_texto_completo")

        if not hospitais:
            return ResultadoExtracaoV2(
                erro="sem_hospital",
                tempo_processamento_ms=int((time.time() - inicio) * 1000),
                warnings=warnings
            )

        # 3. Extração de datas/períodos
        datas_periodos = extrair_datas_periodos(
            msg_parsed.secoes_data,
            data_referencia=data_referencia or date.today()
        )
        if not datas_periodos:
            # Tentar extrair do texto completo
            datas_periodos = extrair_datas_periodos(
                [texto],
                data_referencia=data_referencia or date.today()
            )
            if datas_periodos:
                warnings.append("datas_extraidas_texto_completo")

        if not datas_periodos:
            return ResultadoExtracaoV2(
                hospitais=hospitais,
                erro="sem_data",
                tempo_processamento_ms=int((time.time() - inicio) * 1000),
                warnings=warnings
            )

        # 4. Extração de valores
        valores = extrair_valores(msg_parsed.secoes_valor)
        if not valores.regras and not valores.valor_unico:
            # Tentar extrair do texto completo
            valores = extrair_valores([texto])
            if valores.regras or valores.valor_unico:
                warnings.append("valores_extraidos_texto_completo")
            else:
                warnings.append("sem_valor_extraido")

        # 5. Extração de contato
        contato = extrair_contato(msg_parsed.secoes_contato)
        if not contato:
            # Tentar extrair do texto completo
            contato = extrair_contato([texto])
            if contato:
                warnings.append("contato_extraido_texto_completo")

        # 6. Geração de vagas
        vagas = gerar_vagas(
            hospitais=hospitais,
            datas_periodos=datas_periodos,
            valores=valores,
            contato=contato,
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
        )

        # 7. Validação e deduplicação
        vagas = validar_vagas(vagas)
        vagas = deduplicar_vagas(vagas)

        tempo_ms = int((time.time() - inicio) * 1000)

        return ResultadoExtracaoV2(
            vagas=vagas,
            hospitais=hospitais,
            datas_periodos=datas_periodos,
            valores=valores,
            contato=contato,
            total_vagas=len(vagas),
            tempo_processamento_ms=tempo_ms,
            warnings=warnings
        )

    except ExtracaoError as e:
        logger.error(f"Erro de extração: {e}")
        return ResultadoExtracaoV2(
            erro=str(e),
            tempo_processamento_ms=int((time.time() - inicio) * 1000),
            warnings=warnings
        )
    except Exception as e:
        logger.exception(f"Erro inesperado na extração: {e}")
        return ResultadoExtracaoV2(
            erro=f"erro_inesperado: {str(e)}",
            tempo_processamento_ms=int((time.time() - inicio) * 1000),
            warnings=warnings
        )
