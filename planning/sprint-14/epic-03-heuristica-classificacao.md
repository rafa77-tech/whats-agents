# E03 - Heurística de Classificação

## Objetivo

Implementar filtro rápido baseado em regex e keywords para descartar mensagens que claramente não são ofertas de plantão, reduzindo o volume que vai para o LLM.

## Contexto

Com 500-2000 mensagens/dia, processar todas com LLM seria caro e lento. A heurística é o primeiro estágio de filtro:

- **Entrada:** Mensagens com status `pendente`
- **Saída:** Status `heuristica_passou` ou `heuristica_rejeitou`
- **Meta:** Rejeitar 60-70% das mensagens (conversas normais, cumprimentos, etc)

## Stories

### S03.1 - Definir patterns de keywords positivas

**Descrição:** Criar lista de keywords que indicam oferta de plantão.

**Critérios de Aceite:**
- [ ] Lista documentada
- [ ] Agrupadas por categoria
- [ ] Regex compilados

**Keywords Positivas:**

```python
# app/services/grupos/heuristica.py

KEYWORDS_PLANTAO = [
    # Termos de vaga
    r"\bplant[aã]o\b",
    r"\bvaga\b",
    r"\bescala\b",
    r"\bcobertura\b",
    r"\bsubstitui[çc][aã]o\b",

    # Termos financeiros
    r"R\$\s*\d",
    r"\d+\s*(mil|k)\b",
    r"\breais\b",
    r"\bvalor\b",
    r"\bpago\b",
    r"\bpagamento\b",
    r"\bPJ\b",
    r"\bPF\b",

    # Horários/Períodos
    r"\bnoturno\b",
    r"\bdiurno\b",
    r"\b12h\b",
    r"\b24h\b",
    r"\bcinderela\b",
    r"\d{1,2}h\s*[àa]\s*\d{1,2}h",  # "19h às 7h"
    r"\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}",  # "19:00 - 07:00"

    # Datas
    r"\bdia\s+\d{1,2}\b",
    r"\d{1,2}/\d{1,2}",  # "28/12"
    r"\bamanh[aã]\b",
    r"\bhoje\b",
    r"\bsegunda\b|\bter[çc]a\b|\bquarta\b|\bquinta\b|\bsexta\b",
    r"\bs[aá]bado\b|\bdomingo\b",

    # Termos médicos
    r"\bm[eé]dico\b",
    r"\bdr\.?\b",
    r"\bCRM\b",
    r"\bplantoni[sz]ta\b",

    # Urgência
    r"\burgente\b",
    r"\bpreciso\b",
    r"\bdispon[ií]vel\b",
    r"\baberto\b",
]

KEYWORDS_HOSPITAL = [
    r"\bhospital\b",
    r"\bUPA\b",
    r"\bPS\b",
    r"\bpronto.?socorro\b",
    r"\bcl[ií]nica\b",
    r"\bHU\b",
    r"\bSanta Casa\b",
]

KEYWORDS_ESPECIALIDADE = [
    r"\bcl[ií]nica\s*m[eé]dica\b",
    r"\bCM\b",
    r"\bcardio\b",
    r"\bpediatria\b",
    r"\bortopedia\b",
    r"\bgineco\b",
    r"\bGO\b",
    r"\bcirurgia\b",
    r"\banestesia\b",
    r"\bUTI\b",
    r"\bintensivista\b",
    r"\bemerg[eê]ncia\b",
]
```

**Estimativa:** 1h

---

### S03.2 - Definir patterns de keywords negativas

**Descrição:** Criar lista de keywords que indicam que NÃO é oferta.

**Critérios de Aceite:**
- [ ] Lista documentada
- [ ] Regex compilados

**Keywords Negativas:**

```python
KEYWORDS_DESCARTE = [
    # Cumprimentos
    r"^bom\s*dia\b",
    r"^boa\s*(tarde|noite)\b",
    r"^ol[aá]\b",
    r"^oi\b",

    # Agradecimentos
    r"\bobrigad[oa]\b",
    r"\bvaleu\b",
    r"\bagradec\b",
    r"\btmj\b",

    # Confirmações simples
    r"^ok\b",
    r"^beleza\b",
    r"^blz\b",
    r"^show\b",
    r"^top\b",
    r"^massa\b",

    # Perguntas genéricas
    r"^quem\s",
    r"^algu[eé]m\s",
    r"\?$",  # Termina com interrogação (provável pergunta)

    # Reações
    r"^(kk|haha|rs|kkk)",
    r"^\p{Emoji}+$",  # Só emojis
]

# Mensagens muito curtas geralmente não são ofertas
MIN_TAMANHO_MENSAGEM = 15

# Mensagens muito longas podem ser spam ou regras do grupo
MAX_TAMANHO_MENSAGEM = 2000
```

**Estimativa:** 0.5h

---

### S03.3 - Implementar função de score heurístico

**Descrição:** Função que calcula score baseado nas keywords encontradas.

**Critérios de Aceite:**
- [ ] Função implementada
- [ ] Retorna score 0-1
- [ ] Retorna keywords encontradas

**Código:**

```python
# app/services/grupos/heuristica.py

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ResultadoHeuristica:
    """Resultado da análise heurística."""
    passou: bool
    score: float
    keywords_encontradas: List[str]
    motivo_rejeicao: Optional[str] = None


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para análise."""
    if not texto:
        return ""

    # Lowercase
    texto = texto.lower()

    # Remover acentos (opcional, pode afetar patterns)
    # texto = unidecode(texto)

    # Remover espaços extras
    texto = " ".join(texto.split())

    return texto


def calcular_score_heuristica(texto: str) -> ResultadoHeuristica:
    """
    Calcula score heurístico da mensagem.

    Args:
        texto: Texto da mensagem

    Returns:
        ResultadoHeuristica com score e keywords
    """
    if not texto:
        return ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="texto_vazio"
        )

    texto_norm = normalizar_texto(texto)
    texto_len = len(texto_norm)

    # Verificar tamanho
    if texto_len < MIN_TAMANHO_MENSAGEM:
        return ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="muito_curta"
        )

    if texto_len > MAX_TAMANHO_MENSAGEM:
        return ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="muito_longa"
        )

    # Verificar keywords negativas (descarte imediato)
    for pattern in KEYWORDS_DESCARTE_COMPILED:
        if pattern.search(texto_norm):
            return ResultadoHeuristica(
                passou=False,
                score=0.0,
                keywords_encontradas=[],
                motivo_rejeicao="keyword_negativa"
            )

    # Calcular score positivo
    keywords_encontradas = []
    score = 0.0

    # Keywords de plantão (peso 0.3)
    for pattern in KEYWORDS_PLANTAO_COMPILED:
        match = pattern.search(texto_norm)
        if match:
            keywords_encontradas.append(f"plantao:{match.group()}")
            score += 0.3
            break  # Só conta uma vez por categoria

    # Keywords de hospital (peso 0.25)
    for pattern in KEYWORDS_HOSPITAL_COMPILED:
        match = pattern.search(texto_norm)
        if match:
            keywords_encontradas.append(f"hospital:{match.group()}")
            score += 0.25
            break

    # Keywords de especialidade (peso 0.25)
    for pattern in KEYWORDS_ESPECIALIDADE_COMPILED:
        match = pattern.search(texto_norm)
        if match:
            keywords_encontradas.append(f"especialidade:{match.group()}")
            score += 0.25
            break

    # Valor mencionado (peso 0.2)
    valor_pattern = re.compile(r"R\$\s*[\d.,]+|\d+\s*(mil|k)\b", re.IGNORECASE)
    if valor_pattern.search(texto_norm):
        keywords_encontradas.append("valor:mencionado")
        score += 0.2

    # Normalizar score para 0-1
    score = min(score, 1.0)

    # Threshold para passar
    THRESHOLD = 0.25  # Pelo menos 1 categoria forte

    passou = score >= THRESHOLD

    return ResultadoHeuristica(
        passou=passou,
        score=score,
        keywords_encontradas=keywords_encontradas,
        motivo_rejeicao=None if passou else "score_baixo"
    )


# Compilar patterns na inicialização
KEYWORDS_PLANTAO_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_PLANTAO]
KEYWORDS_HOSPITAL_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_HOSPITAL]
KEYWORDS_ESPECIALIDADE_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_ESPECIALIDADE]
KEYWORDS_DESCARTE_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_DESCARTE]
```

**Estimativa:** 2h

---

### S03.4 - Implementar classificador heurístico

**Descrição:** Função que processa mensagens pendentes com a heurística.

**Critérios de Aceite:**
- [ ] Busca mensagens pendentes
- [ ] Aplica heurística
- [ ] Atualiza status no banco

**Código:**

```python
# app/services/grupos/classificador.py

from typing import List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.heuristica import calcular_score_heuristica, ResultadoHeuristica

logger = get_logger(__name__)


async def buscar_mensagens_pendentes(limite: int = 100) -> List[dict]:
    """
    Busca mensagens com status pendente para classificação.

    Args:
        limite: Máximo de mensagens a buscar

    Returns:
        Lista de mensagens pendentes
    """
    result = supabase.table("mensagens_grupo") \
        .select("id, texto") \
        .eq("status", "pendente") \
        .order("created_at") \
        .limit(limite) \
        .execute()

    return result.data


async def atualizar_resultado_heuristica(
    mensagem_id: UUID,
    resultado: ResultadoHeuristica
) -> None:
    """
    Atualiza mensagem com resultado da heurística.

    Args:
        mensagem_id: ID da mensagem
        resultado: Resultado da análise
    """
    novo_status = "heuristica_passou" if resultado.passou else "heuristica_rejeitou"

    supabase.table("mensagens_grupo") \
        .update({
            "status": novo_status,
            "passou_heuristica": resultado.passou,
            "score_heuristica": resultado.score,
            "keywords_encontradas": resultado.keywords_encontradas,
            "motivo_descarte": resultado.motivo_rejeicao,
            "processado_em": "now()",
        }) \
        .eq("id", str(mensagem_id)) \
        .execute()


async def classificar_batch_heuristica(limite: int = 100) -> dict:
    """
    Processa um batch de mensagens com heurística.

    Args:
        limite: Tamanho do batch

    Returns:
        Estatísticas do processamento
    """
    mensagens = await buscar_mensagens_pendentes(limite)

    stats = {
        "total": len(mensagens),
        "passou": 0,
        "rejeitou": 0,
        "erros": 0,
    }

    for msg in mensagens:
        try:
            resultado = calcular_score_heuristica(msg.get("texto", ""))

            await atualizar_resultado_heuristica(
                mensagem_id=UUID(msg["id"]),
                resultado=resultado
            )

            if resultado.passou:
                stats["passou"] += 1
            else:
                stats["rejeitou"] += 1

        except Exception as e:
            logger.error(f"Erro ao classificar mensagem {msg['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Heurística processou {stats['total']} mensagens: "
        f"{stats['passou']} passaram, {stats['rejeitou']} rejeitadas"
    )

    return stats
```

**Estimativa:** 1.5h

---

### S03.5 - Testes da heurística

**Descrição:** Testes unitários para a heurística.

**Critérios de Aceite:**
- [ ] Testes de keywords positivas
- [ ] Testes de keywords negativas
- [ ] Testes de edge cases
- [ ] Cobertura > 90%

**Arquivo:** `tests/grupos/test_heuristica.py`

```python
import pytest
from app.services.grupos.heuristica import (
    calcular_score_heuristica,
    normalizar_texto,
    ResultadoHeuristica,
)


class TestNormalizarTexto:
    def test_lowercase(self):
        assert normalizar_texto("TESTE") == "teste"

    def test_espacos_extras(self):
        assert normalizar_texto("  muito   espaço  ") == "muito espaço"

    def test_vazio(self):
        assert normalizar_texto("") == ""
        assert normalizar_texto(None) == ""


class TestCalcularScoreHeuristica:
    """Testes do cálculo de score."""

    # Casos que devem PASSAR
    def test_oferta_completa(self):
        texto = """
        🚨 VAGA URGENTE 🚨
        Hospital São Luiz ABC
        Clínica Médica
        Dia 28/12 - Noturno (19h às 7h)
        Valor: R$ 1.800,00 PJ
        """
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou == True
        assert resultado.score >= 0.5
        assert len(resultado.keywords_encontradas) >= 3

    def test_oferta_simples(self):
        texto = "Plantão disponível amanhã no Hospital X, R$ 1500"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou == True
        assert "plantao:" in str(resultado.keywords_encontradas)
        assert "hospital:" in str(resultado.keywords_encontradas)

    def test_oferta_informal(self):
        texto = "Preciso de CM pro HU Santo André amanhã de manhã, pago 2k"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou == True

    def test_lista_escalas(self):
        texto = """
        Escalas disponíveis São Camilo:
        - 26/12 Diurno CM
        - 27/12 Noturno Pediatria
        Ligar 11 98765-4321
        """
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou == True

    # Casos que devem ser REJEITADOS
    def test_cumprimento(self):
        resultado = calcular_score_heuristica("Bom dia pessoal!")
        assert resultado.passou == False
        assert resultado.motivo_rejeicao == "keyword_negativa"

    def test_agradecimento(self):
        resultado = calcular_score_heuristica("Obrigado pela informação")
        assert resultado.passou == False

    def test_mensagem_curta(self):
        resultado = calcular_score_heuristica("Ok")
        assert resultado.passou == False
        assert resultado.motivo_rejeicao == "muito_curta"

    def test_pergunta(self):
        resultado = calcular_score_heuristica("Alguém sabe se tem vaga?")
        assert resultado.passou == False
        assert resultado.motivo_rejeicao == "keyword_negativa"

    def test_risadas(self):
        resultado = calcular_score_heuristica("kkkkkk muito bom")
        assert resultado.passou == False

    def test_texto_vazio(self):
        resultado = calcular_score_heuristica("")
        assert resultado.passou == False
        assert resultado.motivo_rejeicao == "texto_vazio"

    # Edge cases
    def test_so_valor_sem_contexto(self):
        """Só valor sem contexto médico não deve passar."""
        resultado = calcular_score_heuristica("R$ 1000 o produto")
        # Score baixo porque falta contexto médico
        assert resultado.score < 0.5

    def test_hospital_sem_vaga(self):
        """Menção a hospital sem ser oferta."""
        texto = "Fui no Hospital São Luiz ontem e o atendimento foi ótimo"
        resultado = calcular_score_heuristica(texto)
        # Pode passar pela heurística, LLM vai filtrar
        # O importante é não ter falso negativo (rejeitar ofertas reais)


class TestKeywordsEncontradas:
    """Testes das keywords retornadas."""

    def test_categorias_retornadas(self):
        texto = "Plantão Hospital XYZ Cardiologia R$ 2000"
        resultado = calcular_score_heuristica(texto)

        categorias = [k.split(":")[0] for k in resultado.keywords_encontradas]

        assert "plantao" in categorias or "hospital" in categorias

    def test_valor_detectado(self):
        texto = "Vaga disponível, valor R$ 1.500,00"
        resultado = calcular_score_heuristica(texto)

        assert "valor:mencionado" in resultado.keywords_encontradas
```

**Estimativa:** 2h

---

### S03.6 - Benchmark de performance da heurística

**Descrição:** Garantir que a heurística é rápida o suficiente.

**Critérios de Aceite:**
- [ ] Processar 1000 mensagens em < 1 segundo
- [ ] Sem memory leaks
- [ ] Benchmark documentado

**Código:**

```python
# tests/grupos/test_heuristica_benchmark.py

import pytest
import time
from app.services.grupos.heuristica import calcular_score_heuristica


MENSAGENS_TESTE = [
    "Bom dia pessoal",
    "Plantão disponível Hospital São Luiz amanhã R$ 1500",
    "Obrigado",
    "Vaga urgente CM noturno 28/12",
    "Alguém sabe de vaga?",
    "🚨 URGENTE - Preciso de pediatra pro PS Central, 19h-7h, R$ 2k PJ",
    "Ok",
    "Escalas disponíveis: 26/12, 27/12, 28/12 - Clínica Médica",
    "kkkkkk",
    "Hospital XYZ precisa de anestesista para cobertura amanhã",
] * 100  # 1000 mensagens


class TestHeuristicaBenchmark:
    def test_performance_1000_mensagens(self):
        """Deve processar 1000 mensagens em menos de 1 segundo."""
        inicio = time.time()

        for texto in MENSAGENS_TESTE:
            calcular_score_heuristica(texto)

        duracao = time.time() - inicio

        assert duracao < 1.0, f"Demorou {duracao:.2f}s para 1000 mensagens"
        print(f"\nBenchmark: 1000 mensagens em {duracao:.3f}s ({1000/duracao:.0f} msg/s)")

    def test_mensagem_longa(self):
        """Deve processar mensagem longa rapidamente."""
        texto_longo = "Plantão disponível " * 500

        inicio = time.time()
        resultado = calcular_score_heuristica(texto_longo)
        duracao = time.time() - inicio

        assert duracao < 0.01  # < 10ms
        assert resultado.passou == False  # Muito longa
```

**Estimativa:** 0.5h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S03.1 | Keywords positivas | 1h |
| S03.2 | Keywords negativas | 0.5h |
| S03.3 | Função score heurístico | 2h |
| S03.4 | Classificador batch | 1.5h |
| S03.5 | Testes heurística | 2h |
| S03.6 | Benchmark performance | 0.5h |

**Total:** 7.5h (~1 dia)

## Dependências

- E01 (Modelo de Dados)
- E02 (Ingestão)

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Taxa de rejeição | 60-70% |
| Falsos negativos | < 5% (ofertas reais rejeitadas) |
| Performance | > 1000 msg/segundo |
| Tempo por mensagem | < 1ms |

## Entregáveis

- Módulo `app/services/grupos/heuristica.py`
- Função `calcular_score_heuristica()`
- Testes com cobertura > 90%
- Benchmark documentado
