"""
Extrator de dados estruturados de mensagens de grupos.

Sprint 14 - E05 - Extração de Dados
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, UTC
from typing import List, Optional
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.prompts import PROMPT_EXTRACAO

logger = get_logger(__name__)


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class DadosVagaExtraida:
    """Dados extraídos de uma vaga."""
    hospital: Optional[str] = None
    especialidade: Optional[str] = None
    data: Optional[date] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    # Campos de valor flexível (Sprint 19)
    valor: Optional[int] = None           # Valor exato (quando fixo)
    valor_minimo: Optional[int] = None    # Faixa mínima
    valor_maximo: Optional[int] = None    # Faixa máxima
    valor_tipo: str = "a_combinar"        # 'fixo', 'a_combinar', 'faixa'
    periodo: Optional[str] = None
    setor: Optional[str] = None
    tipo_vaga: Optional[str] = None
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None


@dataclass
class ConfiancaExtracao:
    """Scores de confiança por campo."""
    hospital: float = 0.0
    especialidade: float = 0.0
    data: float = 0.0
    hora_inicio: float = 0.0
    hora_fim: float = 0.0
    valor: float = 0.0

    def media_ponderada(self) -> float:
        """Calcula média ponderada (hospital e especialidade têm peso maior)."""
        pesos = {
            "hospital": 3,
            "especialidade": 3,
            "data": 2,
            "hora_inicio": 1,
            "hora_fim": 1,
            "valor": 2,
        }
        total_peso = sum(pesos.values())
        soma = (
            self.hospital * pesos["hospital"] +
            self.especialidade * pesos["especialidade"] +
            self.data * pesos["data"] +
            self.hora_inicio * pesos["hora_inicio"] +
            self.hora_fim * pesos["hora_fim"] +
            self.valor * pesos["valor"]
        )
        return soma / total_peso


@dataclass
class VagaExtraida:
    """Uma vaga extraída da mensagem."""
    dados: DadosVagaExtraida
    confianca: ConfiancaExtracao
    data_valida: bool = True
    campos_faltando: List[str] = field(default_factory=list)


@dataclass
class ResultadoExtracao:
    """Resultado da extração de uma mensagem."""
    vagas: List[VagaExtraida]
    total_vagas: int
    tokens_usados: int = 0
    erro: Optional[str] = None


# =============================================================================
# S05.2 - Cliente LLM para Extração
# =============================================================================

def _parsear_valor_seguro(valor_raw) -> Optional[int]:
    """
    Parseia valor de forma segura, tratando strings.

    Args:
        valor_raw: Valor bruto do JSON (pode ser int, str, None)

    Returns:
        int ou None
    """
    if valor_raw is None:
        return None

    if isinstance(valor_raw, int):
        return valor_raw if valor_raw > 0 else None

    if isinstance(valor_raw, float):
        return int(valor_raw) if valor_raw > 0 else None

    if isinstance(valor_raw, str):
        # Tentar extrair número da string
        # Ex: "1.800", "1800", "R$ 1.800", "1800 reais"
        numeros = re.sub(r'[^\d]', '', valor_raw)
        if numeros:
            try:
                valor_int = int(numeros)
                # Validar range razoável (100 a 50000)
                if 100 <= valor_int <= 50000:
                    return valor_int
            except ValueError:
                pass

    return None


def _validar_valor(
    valor_tipo: str,
    valor: Optional[int],
    valor_minimo: Optional[int],
    valor_maximo: Optional[int]
) -> tuple:
    """
    Valida e corrige consistência dos campos de valor.

    Returns:
        Tupla (valor_tipo, valor, valor_minimo, valor_maximo) validados
    """
    # Normalizar valor_tipo
    valor_tipo = valor_tipo.lower().strip() if valor_tipo else "a_combinar"

    # Mapear variações comuns
    if valor_tipo in ("a combinar", "a_combinar", "negociavel", "a tratar", "negociável"):
        valor_tipo = "a_combinar"
    elif valor_tipo in ("faixa", "range", "entre"):
        valor_tipo = "faixa"
    elif valor_tipo in ("fixo", "exato", "definido"):
        valor_tipo = "fixo"
    else:
        # Tipo desconhecido - inferir do contexto
        if valor and valor > 0:
            valor_tipo = "fixo"
        elif valor_minimo or valor_maximo:
            valor_tipo = "faixa"
        else:
            valor_tipo = "a_combinar"

    # Validar consistência
    if valor_tipo == "fixo":
        if not valor or valor <= 0:
            # Sem valor válido - mudar para a_combinar
            valor_tipo = "a_combinar"
            valor = None
        valor_minimo = None
        valor_maximo = None

    elif valor_tipo == "a_combinar":
        # Se tem valor, inferir como fixo (compatibilidade com JSONs antigos)
        if valor and valor > 0:
            valor_tipo = "fixo"
            valor_minimo = None
            valor_maximo = None
        else:
            valor = None
            valor_minimo = None
            valor_maximo = None

    elif valor_tipo == "faixa":
        valor = None  # Faixa não tem valor exato
        # Validar que pelo menos um limite existe
        if not valor_minimo and not valor_maximo:
            valor_tipo = "a_combinar"
        # Validar ordem
        if valor_minimo and valor_maximo and valor_minimo > valor_maximo:
            valor_minimo, valor_maximo = valor_maximo, valor_minimo

    return valor_tipo, valor, valor_minimo, valor_maximo


def _parsear_resposta_extracao(texto: str) -> ResultadoExtracao:
    """Parseia resposta do LLM."""
    texto = texto.strip()

    # Extrair JSON
    if not texto.startswith("{"):
        match = re.search(r'\{[\s\S]+\}', texto)
        if match:
            texto = match.group()
        else:
            raise json.JSONDecodeError("JSON não encontrado", texto, 0)

    dados = json.loads(texto)

    vagas = []
    for vaga_json in dados.get("vagas", []):
        dados_vaga = vaga_json.get("dados", {})
        confianca_json = vaga_json.get("confianca", {})

        # Converter data string para date
        data_str = dados_vaga.get("data")
        data_obj = None
        if data_str:
            try:
                data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Parsear valor com validação (Sprint 19)
        valor_tipo = dados_vaga.get("valor_tipo", "a_combinar")
        valor = _parsear_valor_seguro(dados_vaga.get("valor"))
        valor_minimo = _parsear_valor_seguro(dados_vaga.get("valor_minimo"))
        valor_maximo = _parsear_valor_seguro(dados_vaga.get("valor_maximo"))

        # Validar consistência
        valor_tipo, valor, valor_minimo, valor_maximo = _validar_valor(
            valor_tipo, valor, valor_minimo, valor_maximo
        )

        vaga = VagaExtraida(
            dados=DadosVagaExtraida(
                hospital=dados_vaga.get("hospital"),
                especialidade=dados_vaga.get("especialidade"),
                data=data_obj,
                hora_inicio=dados_vaga.get("hora_inicio"),
                hora_fim=dados_vaga.get("hora_fim"),
                valor=valor,
                valor_minimo=valor_minimo,
                valor_maximo=valor_maximo,
                valor_tipo=valor_tipo,
                periodo=dados_vaga.get("periodo"),
                setor=dados_vaga.get("setor"),
                tipo_vaga=dados_vaga.get("tipo_vaga"),
                forma_pagamento=dados_vaga.get("forma_pagamento"),
                observacoes=dados_vaga.get("observacoes"),
            ),
            confianca=ConfiancaExtracao(
                hospital=confianca_json.get("hospital", 0.0),
                especialidade=confianca_json.get("especialidade", 0.0),
                data=confianca_json.get("data", 0.0),
                hora_inicio=confianca_json.get("hora_inicio", 0.0),
                hora_fim=confianca_json.get("hora_fim", 0.0),
                valor=confianca_json.get("valor", 0.0),
            ),
            data_valida=vaga_json.get("data_valida", True),
        )

        # Identificar campos faltando (valor não é obrigatório - a_combinar é válido)
        if not vaga.dados.hospital:
            vaga.campos_faltando.append("hospital")
        if not vaga.dados.especialidade:
            vaga.campos_faltando.append("especialidade")
        if not vaga.dados.data:
            vaga.campos_faltando.append("data")

        vagas.append(vaga)

    return ResultadoExtracao(
        vagas=vagas,
        total_vagas=len(vagas)
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def extrair_dados_mensagem(
    texto: str,
    nome_grupo: str = "",
    regiao_grupo: str = "",
    nome_contato: str = ""
) -> ResultadoExtracao:
    """
    Extrai dados estruturados de uma mensagem (async).

    Args:
        texto: Texto da mensagem
        nome_grupo: Nome do grupo
        regiao_grupo: Região do grupo
        nome_contato: Nome de quem enviou

    Returns:
        ResultadoExtracao com lista de vagas
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    hoje = date.today()
    amanha = hoje + timedelta(days=1)

    prompt = PROMPT_EXTRACAO.format(
        texto=texto,
        nome_grupo=nome_grupo or "Desconhecido",
        regiao_grupo=regiao_grupo or "Não informada",
        nome_contato=nome_contato or "Desconhecido",
        data_hoje=hoje.isoformat(),
        data_amanha=amanha.isoformat(),
    )

    try:
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2000,  # Maior para múltiplas vagas
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        resposta_texto = response.content[0].text.strip()
        resultado = _parsear_resposta_extracao(resposta_texto)
        resultado.tokens_usados = response.usage.input_tokens + response.usage.output_tokens

        return resultado

    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear JSON de extração: {e}")
        return ResultadoExtracao(
            vagas=[],
            total_vagas=0,
            erro=f"erro_parse: {str(e)}"
        )
    except anthropic.APIError as e:
        logger.error(f"Erro API Anthropic: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na extração: {e}")
        return ResultadoExtracao(
            vagas=[],
            total_vagas=0,
            erro=f"erro_desconhecido: {str(e)}"
        )


# =============================================================================
# S05.3 - Processador Batch
# =============================================================================

async def buscar_mensagens_para_extracao(limite: int = 50) -> List[dict]:
    """Busca mensagens classificadas como oferta."""
    result = supabase.table("mensagens_grupo") \
        .select("id, texto, grupo_id, contato_id") \
        .eq("status", "classificada_oferta") \
        .order("created_at") \
        .limit(limite) \
        .execute()

    return result.data


async def buscar_contexto_grupo(grupo_id: str) -> tuple:
    """Busca contexto do grupo."""
    nome = ""
    regiao = ""

    try:
        grupo = supabase.table("grupos_whatsapp") \
            .select("nome, regiao") \
            .eq("id", grupo_id) \
            .single() \
            .execute()

        if grupo.data:
            nome = grupo.data.get("nome", "")
            regiao = grupo.data.get("regiao", "")
    except Exception:
        pass

    return nome, regiao


async def salvar_vaga_extraida(
    mensagem_id: UUID,
    grupo_id: UUID,
    contato_id: Optional[UUID],
    vaga: VagaExtraida
) -> Optional[UUID]:
    """
    Salva uma vaga extraída no banco.

    Returns:
        UUID da vaga criada, ou None se dados insuficientes
    """
    # Verificar dados mínimos
    if not vaga.dados.hospital or not vaga.dados.especialidade:
        logger.debug("Vaga sem hospital ou especialidade, ignorando")
        return None

    # Verificar data válida
    if not vaga.data_valida:
        logger.debug("Vaga com data passada, ignorando")
        return None

    dados = {
        "mensagem_id": str(mensagem_id),
        "grupo_origem_id": str(grupo_id),
        "contato_responsavel_id": str(contato_id) if contato_id else None,

        # Dados raw
        "hospital_raw": vaga.dados.hospital,
        "especialidade_raw": vaga.dados.especialidade,
        "periodo_raw": vaga.dados.periodo,
        "setor_raw": vaga.dados.setor,
        "tipo_vaga_raw": vaga.dados.tipo_vaga,
        "forma_pagamento_raw": vaga.dados.forma_pagamento,

        # Dados estruturados
        "data": vaga.dados.data.isoformat() if vaga.dados.data else None,
        "hora_inicio": vaga.dados.hora_inicio,
        "hora_fim": vaga.dados.hora_fim,
        # Campos de valor flexível (Sprint 19)
        "valor": vaga.dados.valor,
        "valor_minimo": vaga.dados.valor_minimo,
        "valor_maximo": vaga.dados.valor_maximo,
        "valor_tipo": vaga.dados.valor_tipo,
        "observacoes": vaga.dados.observacoes,

        # Confiança
        "confianca_geral": vaga.confianca.media_ponderada(),
        "confianca_hospital": vaga.confianca.hospital,
        "confianca_especialidade": vaga.confianca.especialidade,
        "confianca_data": vaga.confianca.data,
        "confianca_valor": vaga.confianca.valor,
        "campos_faltando": vaga.campos_faltando,

        # Status inicial
        "status": "nova",
        "data_valida": vaga.data_valida,
        "dados_minimos_ok": True,
    }

    result = supabase.table("vagas_grupo").insert(dados).execute()
    return UUID(result.data[0]["id"])


async def extrair_batch(limite: int = 50) -> dict:
    """
    Processa batch de mensagens para extração.

    Returns:
        Estatísticas do processamento
    """
    mensagens = await buscar_mensagens_para_extracao(limite)

    stats = {
        "mensagens_processadas": 0,
        "vagas_extraidas": 0,
        "vagas_invalidas": 0,
        "erros": 0,
        "tokens_total": 0,
    }

    for msg in mensagens:
        try:
            # Buscar contexto
            nome_grupo, regiao_grupo = await buscar_contexto_grupo(msg["grupo_id"])
            nome_contato = ""

            if msg.get("contato_id"):
                try:
                    contato = supabase.table("contatos_grupo") \
                        .select("nome") \
                        .eq("id", msg["contato_id"]) \
                        .single() \
                        .execute()
                    nome_contato = contato.data.get("nome", "") if contato.data else ""
                except Exception:
                    pass

            # Extrair
            resultado = await extrair_dados_mensagem(
                texto=msg["texto"],
                nome_grupo=nome_grupo,
                regiao_grupo=regiao_grupo,
                nome_contato=nome_contato
            )

            stats["tokens_total"] += resultado.tokens_usados

            # Salvar cada vaga
            vagas_salvas = 0
            for vaga in resultado.vagas:
                vaga_id = await salvar_vaga_extraida(
                    mensagem_id=UUID(msg["id"]),
                    grupo_id=UUID(msg["grupo_id"]),
                    contato_id=UUID(msg["contato_id"]) if msg.get("contato_id") else None,
                    vaga=vaga
                )

                if vaga_id:
                    vagas_salvas += 1
                else:
                    stats["vagas_invalidas"] += 1

            # Atualizar mensagem
            novo_status = "extraida" if vagas_salvas > 0 else "extracao_falhou"
            supabase.table("mensagens_grupo") \
                .update({
                    "status": novo_status,
                    "qtd_vagas_extraidas": vagas_salvas,
                    "processado_em": datetime.now(UTC).isoformat(),
                }) \
                .eq("id", msg["id"]) \
                .execute()

            stats["mensagens_processadas"] += 1
            stats["vagas_extraidas"] += vagas_salvas

            # Rate limiting
            await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"Erro ao extrair mensagem {msg['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Extração processou {stats['mensagens_processadas']} mensagens, "
        f"{stats['vagas_extraidas']} vagas extraídas"
    )

    return stats
