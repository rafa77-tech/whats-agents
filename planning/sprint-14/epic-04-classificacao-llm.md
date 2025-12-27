# E04 - Classificação LLM

## Objetivo

Implementar classificação via LLM para mensagens que passaram pela heurística, determinando com precisão se são ofertas de plantão.

## Contexto

Mensagens que passaram pela heurística (status `heuristica_passou`) precisam de validação mais precisa. O LLM classifica:

- **É oferta de plantão?** (sim/não)
- **Confiança** da classificação (0-1)

## Stories

### S04.1 - Criar prompt de classificação

**Descrição:** Criar prompt otimizado para classificar ofertas.

**Critérios de Aceite:**
- [ ] Prompt claro e conciso
- [ ] Exemplos few-shot incluídos
- [ ] Retorno em JSON estruturado

**Prompt:**

```python
# app/services/grupos/prompts.py

PROMPT_CLASSIFICACAO = """
Você é um classificador de mensagens de grupos de WhatsApp de staffing médico.

Sua tarefa: Determinar se a mensagem é uma OFERTA DE PLANTÃO/VAGA MÉDICA.

CONSIDERA OFERTA DE PLANTÃO:
- Anúncio de vaga/plantão disponível
- Lista de escalas disponíveis
- Cobertura urgente sendo oferecida
- Hospital/clínica buscando médico para data específica

NÃO CONSIDERA OFERTA:
- Perguntas sobre vagas ("alguém tem vaga?")
- Cumprimentos e conversas sociais
- Médicos se oferecendo para trabalhar
- Discussões sobre valores de mercado
- Regras do grupo

MENSAGEM:
{texto}

CONTEXTO:
- Grupo: {nome_grupo}
- Enviado por: {nome_contato}

Responda APENAS com JSON:
{
  "eh_oferta": true/false,
  "confianca": 0.0-1.0,
  "motivo": "explicação breve"
}
"""


EXEMPLOS_CLASSIFICACAO = [
    {
        "texto": "Bom dia pessoal!",
        "resposta": {"eh_oferta": False, "confianca": 0.99, "motivo": "Cumprimento"}
    },
    {
        "texto": "🚨 URGENTE - Plantão disponível Hospital São Luiz, CM, 28/12 noturno, R$ 1800 PJ",
        "resposta": {"eh_oferta": True, "confianca": 0.98, "motivo": "Oferta completa com hospital, especialidade, data e valor"}
    },
    {
        "texto": "Alguém sabe se tem vaga de cardio essa semana?",
        "resposta": {"eh_oferta": False, "confianca": 0.95, "motivo": "Pergunta sobre vaga, não oferta"}
    },
    {
        "texto": "Preciso de CM pro PS Central amanhã, pago 2k",
        "resposta": {"eh_oferta": True, "confianca": 0.92, "motivo": "Oferta informal mas com dados de vaga"}
    },
    {
        "texto": "Sou pediatra com disponibilidade, alguém contrata?",
        "resposta": {"eh_oferta": False, "confianca": 0.90, "motivo": "Médico se oferecendo, não oferta de vaga"}
    },
]
```

**Estimativa:** 1h

---

### S04.2 - Implementar cliente LLM para classificação

**Descrição:** Função que chama o LLM para classificar mensagens.

**Critérios de Aceite:**
- [ ] Usar Claude Haiku (custo baixo)
- [ ] Retry com backoff
- [ ] Timeout configurável
- [ ] Parsing robusto do JSON

**Código:**

```python
# app/services/grupos/classificador_llm.py

import json
from typing import Optional
from dataclasses import dataclass

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.grupos.prompts import PROMPT_CLASSIFICACAO

logger = get_logger(__name__)


@dataclass
class ResultadoClassificacaoLLM:
    """Resultado da classificação LLM."""
    eh_oferta: bool
    confianca: float
    motivo: str
    tokens_usados: int = 0
    erro: Optional[str] = None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def classificar_com_llm(
    texto: str,
    nome_grupo: str = "",
    nome_contato: str = ""
) -> ResultadoClassificacaoLLM:
    """
    Classifica mensagem usando LLM.

    Args:
        texto: Texto da mensagem
        nome_grupo: Nome do grupo (contexto)
        nome_contato: Nome de quem enviou (contexto)

    Returns:
        ResultadoClassificacaoLLM
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = PROMPT_CLASSIFICACAO.format(
        texto=texto,
        nome_grupo=nome_grupo or "Desconhecido",
        nome_contato=nome_contato or "Desconhecido"
    )

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extrair texto da resposta
        resposta_texto = response.content[0].text.strip()

        # Tentar parsear JSON
        resultado = _parsear_resposta_llm(resposta_texto)

        resultado.tokens_usados = response.usage.input_tokens + response.usage.output_tokens

        return resultado

    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear JSON do LLM: {e}")
        return ResultadoClassificacaoLLM(
            eh_oferta=False,
            confianca=0.0,
            motivo="erro_parse",
            erro=str(e)
        )
    except anthropic.APIError as e:
        logger.error(f"Erro API Anthropic: {e}")
        raise  # Será tratado pelo retry


def _parsear_resposta_llm(texto: str) -> ResultadoClassificacaoLLM:
    """
    Parseia resposta do LLM para estrutura.

    Tenta extrair JSON mesmo se vier com texto adicional.
    """
    # Tentar encontrar JSON na resposta
    texto = texto.strip()

    # Se começa com {, tentar parsear direto
    if texto.startswith("{"):
        dados = json.loads(texto)
    else:
        # Tentar extrair JSON do meio do texto
        import re
        match = re.search(r'\{[^{}]+\}', texto)
        if match:
            dados = json.loads(match.group())
        else:
            raise json.JSONDecodeError("JSON não encontrado", texto, 0)

    return ResultadoClassificacaoLLM(
        eh_oferta=dados.get("eh_oferta", False),
        confianca=float(dados.get("confianca", 0.0)),
        motivo=dados.get("motivo", "")
    )
```

**Estimativa:** 2h

---

### S04.3 - Implementar processador batch de classificação LLM

**Descrição:** Função que processa mensagens em batch com rate limiting.

**Critérios de Aceite:**
- [ ] Processar mensagens com status `heuristica_passou`
- [ ] Rate limiting para não sobrecarregar API
- [ ] Atualizar status no banco
- [ ] Métricas de processamento

**Código:**

```python
# app/services/grupos/classificador.py (adicionar)

import asyncio
from typing import List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.classificador_llm import classificar_com_llm, ResultadoClassificacaoLLM

logger = get_logger(__name__)

# Rate limiting
MAX_REQUESTS_POR_MINUTO = 60
DELAY_ENTRE_REQUESTS = 1.0  # segundos


async def buscar_mensagens_para_classificacao_llm(limite: int = 50) -> List[dict]:
    """
    Busca mensagens que passaram na heurística para classificação LLM.
    """
    result = supabase.table("mensagens_grupo") \
        .select("id, texto, grupo_id, contato_id") \
        .eq("status", "heuristica_passou") \
        .order("created_at") \
        .limit(limite) \
        .execute()

    return result.data


async def buscar_contexto_mensagem(grupo_id: str, contato_id: str) -> tuple:
    """Busca nome do grupo e contato para contexto."""
    nome_grupo = ""
    nome_contato = ""

    try:
        if grupo_id:
            grupo = supabase.table("grupos_whatsapp") \
                .select("nome") \
                .eq("id", grupo_id) \
                .single() \
                .execute()
            nome_grupo = grupo.data.get("nome", "") if grupo.data else ""

        if contato_id:
            contato = supabase.table("contatos_grupo") \
                .select("nome") \
                .eq("id", contato_id) \
                .single() \
                .execute()
            nome_contato = contato.data.get("nome", "") if contato.data else ""
    except Exception:
        pass

    return nome_grupo, nome_contato


async def atualizar_resultado_classificacao_llm(
    mensagem_id: UUID,
    resultado: ResultadoClassificacaoLLM
) -> None:
    """Atualiza mensagem com resultado da classificação LLM."""
    novo_status = "classificada_oferta" if resultado.eh_oferta else "classificada_nao_oferta"

    if resultado.erro:
        novo_status = "erro"

    supabase.table("mensagens_grupo") \
        .update({
            "status": novo_status,
            "eh_oferta": resultado.eh_oferta,
            "confianca_classificacao": resultado.confianca,
            "processado_em": "now()",
            "erro": resultado.erro,
        }) \
        .eq("id", str(mensagem_id)) \
        .execute()


async def classificar_batch_llm(limite: int = 50) -> dict:
    """
    Processa batch de mensagens com LLM.

    Args:
        limite: Tamanho do batch

    Returns:
        Estatísticas do processamento
    """
    mensagens = await buscar_mensagens_para_classificacao_llm(limite)

    stats = {
        "total": len(mensagens),
        "ofertas": 0,
        "nao_ofertas": 0,
        "erros": 0,
        "tokens_total": 0,
    }

    for msg in mensagens:
        try:
            # Buscar contexto
            nome_grupo, nome_contato = await buscar_contexto_mensagem(
                msg.get("grupo_id"),
                msg.get("contato_id")
            )

            # Classificar
            resultado = await classificar_com_llm(
                texto=msg.get("texto", ""),
                nome_grupo=nome_grupo,
                nome_contato=nome_contato
            )

            # Atualizar banco
            await atualizar_resultado_classificacao_llm(
                mensagem_id=UUID(msg["id"]),
                resultado=resultado
            )

            if resultado.eh_oferta:
                stats["ofertas"] += 1
            else:
                stats["nao_ofertas"] += 1

            stats["tokens_total"] += resultado.tokens_usados

            # Rate limiting
            await asyncio.sleep(DELAY_ENTRE_REQUESTS)

        except Exception as e:
            logger.error(f"Erro ao classificar mensagem {msg['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Classificação LLM processou {stats['total']} mensagens: "
        f"{stats['ofertas']} ofertas, {stats['nao_ofertas']} não-ofertas, "
        f"{stats['tokens_total']} tokens usados"
    )

    return stats
```

**Estimativa:** 2h

---

### S04.4 - Testes do classificador LLM

**Descrição:** Testes unitários e de integração.

**Critérios de Aceite:**
- [ ] Mock do cliente Anthropic
- [ ] Testes de parsing de resposta
- [ ] Testes de retry
- [ ] Testes de edge cases

**Arquivo:** `tests/grupos/test_classificador_llm.py`

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.services.grupos.classificador_llm import (
    classificar_com_llm,
    _parsear_resposta_llm,
    ResultadoClassificacaoLLM,
)


class TestParsearRespostaLLM:
    """Testes do parser de resposta."""

    def test_json_simples(self):
        texto = '{"eh_oferta": true, "confianca": 0.95, "motivo": "Oferta clara"}'
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta == True
        assert resultado.confianca == 0.95
        assert resultado.motivo == "Oferta clara"

    def test_json_com_texto_antes(self):
        texto = 'Analisando a mensagem:\n{"eh_oferta": false, "confianca": 0.8, "motivo": "Pergunta"}'
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta == False

    def test_json_com_espacos(self):
        texto = '''
        {
            "eh_oferta": true,
            "confianca": 0.9,
            "motivo": "teste"
        }
        '''
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta == True

    def test_json_invalido(self):
        with pytest.raises(json.JSONDecodeError):
            _parsear_resposta_llm("isso não é json")


class TestClassificarComLLM:
    """Testes da função de classificação."""

    @pytest.mark.asyncio
    async def test_classificacao_sucesso(self, mock_anthropic):
        """Deve classificar corretamente."""
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"eh_oferta": true, "confianca": 0.95, "motivo": "Oferta"}')],
            usage=MagicMock(input_tokens=100, output_tokens=50)
        )

        resultado = await classificar_com_llm(
            texto="Plantão disponível Hospital X",
            nome_grupo="Vagas ABC"
        )

        assert resultado.eh_oferta == True
        assert resultado.confianca == 0.95
        assert resultado.tokens_usados == 150

    @pytest.mark.asyncio
    async def test_classificacao_nao_oferta(self, mock_anthropic):
        """Deve identificar não-ofertas."""
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"eh_oferta": false, "confianca": 0.9, "motivo": "Cumprimento"}')],
            usage=MagicMock(input_tokens=50, output_tokens=30)
        )

        resultado = await classificar_com_llm("Bom dia pessoal!")

        assert resultado.eh_oferta == False

    @pytest.mark.asyncio
    async def test_erro_api_retry(self, mock_anthropic):
        """Deve fazer retry em caso de erro."""
        import anthropic

        mock_anthropic.messages.create.side_effect = [
            anthropic.APIError("Erro temporário"),
            MagicMock(
                content=[MagicMock(text='{"eh_oferta": true, "confianca": 0.8, "motivo": "ok"}')],
                usage=MagicMock(input_tokens=50, output_tokens=30)
            )
        ]

        resultado = await classificar_com_llm("Teste")

        assert resultado.eh_oferta == True
        assert mock_anthropic.messages.create.call_count == 2


@pytest.fixture
def mock_anthropic():
    with patch("app.services.grupos.classificador_llm.anthropic.Anthropic") as mock:
        yield mock.return_value
```

**Estimativa:** 2h

---

### S04.5 - Cache de classificações

**Descrição:** Implementar cache para evitar reclassificar mensagens similares.

**Critérios de Aceite:**
- [ ] Cache em Redis
- [ ] Hash do texto como chave
- [ ] TTL de 24h
- [ ] Bypass opcional

**Código:**

```python
# app/services/grupos/cache.py

import hashlib
import json
from typing import Optional

from app.core.redis import get_redis
from app.services.grupos.classificador_llm import ResultadoClassificacaoLLM

CACHE_TTL = 86400  # 24 horas
CACHE_PREFIX = "grupo:classificacao:"


def _hash_texto(texto: str) -> str:
    """Gera hash do texto para cache."""
    return hashlib.md5(texto.encode()).hexdigest()


async def buscar_classificacao_cache(texto: str) -> Optional[ResultadoClassificacaoLLM]:
    """
    Busca classificação no cache.

    Args:
        texto: Texto da mensagem

    Returns:
        ResultadoClassificacaoLLM se encontrado, None caso contrário
    """
    redis = get_redis()
    chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"

    dados = await redis.get(chave)
    if dados:
        dados = json.loads(dados)
        return ResultadoClassificacaoLLM(
            eh_oferta=dados["eh_oferta"],
            confianca=dados["confianca"],
            motivo=dados["motivo"],
            tokens_usados=0  # Do cache
        )

    return None


async def salvar_classificacao_cache(
    texto: str,
    resultado: ResultadoClassificacaoLLM
) -> None:
    """Salva classificação no cache."""
    redis = get_redis()
    chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"

    dados = json.dumps({
        "eh_oferta": resultado.eh_oferta,
        "confianca": resultado.confianca,
        "motivo": resultado.motivo,
    })

    await redis.setex(chave, CACHE_TTL, dados)
```

**Estimativa:** 1h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S04.1 | Prompt de classificação | 1h |
| S04.2 | Cliente LLM | 2h |
| S04.3 | Processador batch | 2h |
| S04.4 | Testes | 2h |
| S04.5 | Cache Redis | 1h |

**Total:** 8h (~1 dia)

## Dependências

- E01 (Modelo de Dados)
- E02 (Ingestão)
- E03 (Heurística)

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Precisão | > 90% |
| Recall | > 95% (não perder ofertas reais) |
| Custo por mensagem | < $0.001 |
| Latência | < 2s por mensagem |

## Entregáveis

- Prompt otimizado
- Cliente LLM com retry
- Processador batch
- Cache Redis
- Testes com > 90% cobertura
