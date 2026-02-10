"""
Gerador de vagas atômicas.

Combina hospitais, datas, valores e contato para gerar vagas.

Sprint 40 - E07: Gerador de Vagas
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import (
    VagaAtomica,
    HospitalExtraido,
    DataPeriodoExtraido,
    ValoresExtraidos,
    ContatoExtraido,
    EspecialidadeExtraida,
)
from app.services.grupos.extrator_v2.extrator_valores import obter_valor_para_dia

logger = get_logger(__name__)


def _calcular_confianca_geral(
    hospital: HospitalExtraido,
    data_periodo: DataPeriodoExtraido,
    valor: Optional[int],
    contato: Optional[ContatoExtraido],
) -> float:
    """
    Calcula confiança geral da vaga.

    Média ponderada das confianças dos componentes.
    """
    pesos = {
        "hospital": 3,
        "data": 3,
        "valor": 2,
        "contato": 1,
    }

    scores = {
        "hospital": hospital.confianca,
        "data": data_periodo.confianca,
        "valor": 1.0 if valor else 0.5,  # Sem valor = menos confiável
        "contato": contato.confianca if contato else 0.5,
    }

    total_peso = sum(pesos.values())
    soma = sum(scores[k] * pesos[k] for k in pesos)

    return round(soma / total_peso, 2)


def gerar_vagas_para_hospital(
    hospital: HospitalExtraido,
    datas_periodos: List[DataPeriodoExtraido],
    valores: ValoresExtraidos,
    contato: Optional[ContatoExtraido] = None,
    especialidades: Optional[List[EspecialidadeExtraida]] = None,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
) -> List[VagaAtomica]:
    """
    Gera vagas atômicas para um hospital.

    Args:
        hospital: Hospital extraído
        datas_periodos: Lista de datas e períodos
        valores: Valores e regras
        contato: Contato extraído (opcional)
        especialidades: Especialidades (opcional)
        mensagem_id: ID da mensagem origem
        grupo_id: ID do grupo origem

    Returns:
        Lista de VagaAtomica
    """
    vagas = []

    # Usar primeira especialidade se disponível
    especialidade = especialidades[0] if especialidades else None

    for dp in datas_periodos:
        # Obter valor para este dia/período
        valor = obter_valor_para_dia(valores, dp.dia_semana, dp.periodo)

        if valor is None:
            logger.warning(
                f"Sem valor para {dp.dia_semana.value}/{dp.periodo.value}, "
                f"usando valor_unico ou ignorando"
            )
            valor = valores.valor_unico
            if valor is None:
                # Sem valor conhecido - gerar vaga mesmo assim mas com observação
                pass

        # Calcular confiança
        confianca = _calcular_confianca_geral(hospital, dp, valor, contato)

        # Criar vaga atômica
        vaga = VagaAtomica(
            # Dados da data/período
            data=dp.data,
            dia_semana=dp.dia_semana,
            periodo=dp.periodo,
            hora_inicio=dp.hora_inicio,
            hora_fim=dp.hora_fim,
            # Valor
            valor=valor or 0,  # 0 indica valor não informado
            # Hospital
            hospital_raw=hospital.nome,
            endereco_raw=hospital.endereco,
            cidade=hospital.cidade,
            estado=hospital.estado,
            # Especialidade
            especialidade_raw=especialidade.nome if especialidade else None,
            # Contato
            contato_nome=contato.nome if contato else None,
            contato_whatsapp=contato.whatsapp if contato else None,
            # Metadados
            confianca_geral=confianca,
            observacoes="Valor não informado" if valor is None else None,
            # Rastreabilidade
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
        )

        vagas.append(vaga)

    return vagas


def gerar_vagas(
    hospitais: List[HospitalExtraido],
    datas_periodos: List[DataPeriodoExtraido],
    valores: ValoresExtraidos,
    contato: Optional[ContatoExtraido] = None,
    especialidades: Optional[List[EspecialidadeExtraida]] = None,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
) -> List[VagaAtomica]:
    """
    Gera todas as vagas atômicas a partir dos dados extraídos.

    Esta é a função principal do gerador.

    Lógica:
    - Para cada hospital
      - Para cada data/período
        - Cria uma vaga com valor associado ao dia da semana

    Args:
        hospitais: Lista de hospitais extraídos
        datas_periodos: Lista de datas e períodos
        valores: Valores e regras
        contato: Contato extraído
        especialidades: Especialidades extraídas
        mensagem_id: ID da mensagem origem
        grupo_id: ID do grupo origem

    Returns:
        Lista de VagaAtomica

    Example:
        >>> hospitais = [HospitalExtraido(nome="Hospital ABC")]
        >>> datas = [
        ...     DataPeriodoExtraido(data=date(2026,1,26), dia_semana=DiaSemana.SEGUNDA, periodo=Periodo.MANHA),
        ...     DataPeriodoExtraido(data=date(2026,1,27), dia_semana=DiaSemana.TERCA, periodo=Periodo.NOITE),
        ... ]
        >>> valores = ValoresExtraidos(valor_unico=1700)
        >>> vagas = gerar_vagas(hospitais, datas, valores)
        >>> len(vagas)
        2
    """
    if not hospitais:
        logger.warning("Nenhum hospital fornecido")
        return []

    if not datas_periodos:
        logger.warning("Nenhuma data/período fornecido")
        return []

    todas_vagas = []

    for hospital in hospitais:
        vagas_hospital = gerar_vagas_para_hospital(
            hospital=hospital,
            datas_periodos=datas_periodos,
            valores=valores,
            contato=contato,
            especialidades=especialidades,
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
        )
        todas_vagas.extend(vagas_hospital)

    logger.info(
        f"Geradas {len(todas_vagas)} vagas "
        f"({len(hospitais)} hospitais × {len(datas_periodos)} datas)"
    )

    return todas_vagas


def validar_vagas(vagas: List[VagaAtomica]) -> List[VagaAtomica]:
    """
    Valida e filtra vagas.

    Remove vagas com dados insuficientes ou inválidos.

    Args:
        vagas: Lista de vagas geradas

    Returns:
        Lista de vagas válidas
    """
    validas = []
    hoje = date.today()

    for vaga in vagas:
        # Verificar campos obrigatórios
        if not vaga.hospital_raw:
            logger.debug("Vaga sem hospital, ignorando")
            continue

        if not vaga.data:
            logger.debug("Vaga sem data, ignorando")
            continue

        # Verificar data futura
        if vaga.data < hoje:
            logger.debug(f"Vaga com data passada {vaga.data}, ignorando")
            continue

        # Verificar valor (0 é permitido - significa "a combinar")
        # Não filtrar por valor

        validas.append(vaga)

    logger.info(f"Validação: {len(validas)}/{len(vagas)} vagas válidas")
    return validas


def deduplicar_vagas(vagas: List[VagaAtomica]) -> List[VagaAtomica]:
    """
    Remove vagas duplicadas.

    Duas vagas são consideradas duplicadas se têm mesmo:
    - Hospital
    - Data
    - Período
    - Valor

    Args:
        vagas: Lista de vagas

    Returns:
        Lista sem duplicatas
    """
    vistas: set = set()
    unicas = []

    for vaga in vagas:
        chave = (
            vaga.hospital_raw.lower().strip(),
            vaga.data.isoformat(),
            vaga.periodo.value,
            vaga.valor,
        )

        if chave not in vistas:
            vistas.add(chave)
            unicas.append(vaga)
        else:
            logger.debug(f"Vaga duplicada removida: {chave}")

    if len(vagas) != len(unicas):
        logger.info(f"Deduplicação: {len(vagas)} -> {len(unicas)} vagas")

    return unicas
