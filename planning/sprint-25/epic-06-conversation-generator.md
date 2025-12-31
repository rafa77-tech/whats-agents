# Epic 03: Conversation Generator

## Objetivo

Gerar dialogos naturais usando Claude com typos intencionais, linguagem informal brasileira e trending topics.

## Contexto

Conversas de warm-up precisam parecer REAIS. Isso significa:
- Linguagem informal brasileira (vc, pra, blz, tb)
- Typos ocasionais com correcao (ex: "voc*" -> "vc*")
- Temas variados (cotidiano, futebol, series)
- Trending topics para contexto atual
- Variacao no tamanho das mensagens
- Emojis com moderacao

---

## Story 3.1: Temas de Conversa

### Objetivo
Definir banco de temas para geracao de dialogos.

### Implementacao

**Arquivo:** `app/services/warmer/conversation_generator.py`

```python
"""
Conversation Generator - Gera dialogos naturais para warm-up.

Usa Claude para criar conversas com:
- Linguagem informal brasileira
- Typos intencionais com correcao
- Trending topics para contexto atual
"""
import random
import json
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


# Temas base para conversas
TEMAS_WARMUP = [
    "cotidiano",
    "clima e tempo",
    "futebol brasileiro",
    "filmes e series",
    "viagens",
    "comida e restaurantes",
    "tecnologia",
    "noticias leves",
    "fim de semana",
    "trabalho generico",
    "familia",
    "musica",
    "series netflix",
    "compras online",
    "pets",
    "academia e saude",
    "trânsito",
    "delivery",
    "feriados",
    "eventos locais",
]


# Temas sazonais por mes
TEMAS_SAZONAIS = {
    1: ["ano novo", "ferias", "praia", "calor"],
    2: ["carnaval", "volta as aulas"],
    3: ["outono chegando", "chuvas"],
    4: ["pascoa", "outono"],
    5: ["dia das maes", "frio chegando"],
    6: ["festa junina", "frio", "dia dos namorados"],
    7: ["ferias de inverno", "frio"],
    8: ["dia dos pais", "primavera chegando"],
    9: ["primavera", "flores"],
    10: ["dia das criancas", "halloween"],
    11: ["black friday", "calor chegando"],
    12: ["natal", "ferias", "ano novo", "calor"],
}


def escolher_tema(usar_sazonal: bool = True) -> str:
    """
    Escolhe tema para conversa.

    Args:
        usar_sazonal: Se deve priorizar temas sazonais

    Returns:
        Tema escolhido
    """
    if usar_sazonal and random.random() < 0.3:
        from datetime import datetime
        mes = datetime.now().month
        temas_mes = TEMAS_SAZONAIS.get(mes, [])
        if temas_mes:
            return random.choice(temas_mes)

    return random.choice(TEMAS_WARMUP)
```

### DoD

- [ ] Lista de temas definida
- [ ] Temas sazonais por mes
- [ ] Funcao `escolher_tema` implementada
- [ ] 30% chance de tema sazonal

---

## Story 3.2: Trending Topics

### Objetivo
Buscar trending topics brasileiros para conversas mais atuais.

### Implementacao

```python
import feedparser
from app.services.redis import redis_client


async def buscar_trending_brasil() -> str:
    """
    Busca trending topic brasileiro.
    Usa cache Redis (1 hora) para evitar requests excessivos.

    Fontes:
    - RSS G1 (mais estavel)
    - Fallback para temas pre-definidos

    Returns:
        String com topico trending ou tema generico
    """
    # Checar cache
    cached = await redis_client.get("warmer:trending_brasil")
    if cached:
        return cached.decode() if isinstance(cached, bytes) else cached

    try:
        # RSS G1 (mais estavel que Google Trends)
        feed = feedparser.parse('https://g1.globo.com/rss/g1/')
        if feed.entries:
            # Pegar manchetes (excluir tragédias, politica pesada)
            manchetes = []
            termos_excluir = ["morte", "morre", "assassin", "traged", "acident"]

            for entry in feed.entries[:15]:
                titulo = entry.title.lower()
                if not any(termo in titulo for termo in termos_excluir):
                    manchetes.append(entry.title)

            if manchetes:
                trending = random.choice(manchetes[:10])

                # Cache por 1 hora
                await redis_client.setex("warmer:trending_brasil", 3600, trending)
                return trending

    except Exception as e:
        logger.warning(f"Erro ao buscar trending: {e}")

    # Fallback
    return random.choice(TEMAS_WARMUP)


async def buscar_trending_esportes() -> Optional[str]:
    """
    Busca trending de esportes (especialmente futebol).

    Returns:
        Noticia esportiva ou None
    """
    cached = await redis_client.get("warmer:trending_esportes")
    if cached:
        return cached.decode() if isinstance(cached, bytes) else cached

    try:
        feed = feedparser.parse('https://ge.globo.com/rss/feed')
        if feed.entries:
            manchetes = [entry.title for entry in feed.entries[:10]]
            trending = random.choice(manchetes)

            await redis_client.setex("warmer:trending_esportes", 3600, trending)
            return trending

    except Exception as e:
        logger.warning(f"Erro ao buscar trending esportes: {e}")

    return None
```

### DoD

- [ ] Busca RSS G1 funcionando
- [ ] Cache Redis de 1 hora
- [ ] Filtro de conteudo negativo
- [ ] Fallback para temas base
- [ ] Busca de esportes separada

---

## Story 3.3: Geracao de Dialogo via Claude

### Objetivo
Gerar dialogos naturais usando Claude com prompt especializado.

### Implementacao

```python
from app.services.claude import claude_client


PROMPT_DIALOGO = """Gere um dialogo casual de WhatsApp entre duas pessoas (A e B) sobre: {tema}

REGRAS OBRIGATORIAS:
- Exatamente {turnos} mensagens no total (alternando A e B)
- Mensagens CURTAS (1-3 linhas maximo cada)
- Linguagem informal brasileira: vc, pra, ta, blz, tb, msg, tmb, nd, oq, ne
- Emojis ocasionais (3-5 no dialogo todo, NAO em toda msg)
- IMPORTANTE: Inclua 1-2 typos com correcao, exemplos:
  * "voc" seguido de "vc*" na proxima msg
  * "trbalhando" seguido de "trabalhando*"
  * "aond" seguido de "onde*"
- Termine naturalmente (despedida ou combinado)
- Varie tamanho das msgs (algumas bem curtas "blz", outras medias)
- Pareca conversa REAL entre amigos
- NAO use: palavrao, politica, religiao, assuntos sensiveis

FORMATO JSON (array de objetos):
[
  {{"from": "A", "text": "mensagem aqui"}},
  {{"from": "B", "text": "resposta aqui"}},
  ...
]

APENAS O JSON, sem explicacoes."""


async def gerar_dialogo(
    tema: Optional[str] = None,
    usar_trending: bool = True,
    turnos: Optional[int] = None,
) -> List[Dict[str, str]]:
    """
    Gera dialogo natural entre duas pessoas.

    Args:
        tema: Tema especifico (opcional)
        usar_trending: Se deve usar trending topics
        turnos: Numero de turnos (4-12 se nao especificado)

    Returns:
        Lista de mensagens: [{from: 'A', text: '...'}, ...]
    """
    # Escolher tema
    if not tema:
        if usar_trending and random.random() < 0.3:  # 30% chance trending
            tema = await buscar_trending_brasil()
        else:
            tema = escolher_tema()

    # Numero de turnos variavel (4-12)
    if not turnos:
        turnos = random.randint(4, 12)

    prompt = PROMPT_DIALOGO.format(tema=tema, turnos=turnos)

    try:
        response = await claude_client.generate(
            prompt=prompt,
            model="haiku",
            max_tokens=1000,
            temperature=0.9,  # Alta para variedade
        )

        # Parse JSON
        # Limpar resposta (remover markdown se houver)
        response_clean = response.strip()
        if response_clean.startswith("```"):
            response_clean = response_clean.split("```")[1]
            if response_clean.startswith("json"):
                response_clean = response_clean[4:]
            response_clean = response_clean.strip()

        mensagens = json.loads(response_clean)

        if not isinstance(mensagens, list) or len(mensagens) < 4:
            raise ValueError("Formato invalido")

        # Validar estrutura
        for msg in mensagens:
            if "from" not in msg or "text" not in msg:
                raise ValueError("Mensagem sem from ou text")

        logger.info(f"[ConvGen] Dialogo gerado: {tema}, {len(mensagens)} msgs")
        return mensagens

    except json.JSONDecodeError as e:
        logger.error(f"[ConvGen] Erro JSON: {e}")
        return gerar_dialogo_fallback()
    except Exception as e:
        logger.error(f"[ConvGen] Erro ao gerar dialogo: {e}")
        return gerar_dialogo_fallback()
```

### DoD

- [ ] Prompt especializado para dialogo BR
- [ ] Geracao via Claude Haiku
- [ ] Parse de JSON robusto
- [ ] Temperatura alta para variedade
- [ ] Validacao de estrutura
- [ ] Testes com diferentes temas

---

## Story 3.4: Dialogos Fallback

### Objetivo
Criar banco de dialogos pre-definidos para fallback.

### Implementacao

```python
def gerar_dialogo_fallback() -> List[Dict[str, str]]:
    """
    Dialogo fallback caso Claude falhe.
    Retorna dialogo aleatorio do banco pre-definido.
    """
    dialogos = [
        # Dialogo 1: Generico
        [
            {"from": "A", "text": "e ai, blz?"},
            {"from": "B", "text": "tudo bem e vc?"},
            {"from": "A", "text": "de boa, so trabalhando"},
            {"from": "B", "text": "sei como e kkk"},
            {"from": "A", "text": "fds ta chegando pelo menos"},
            {"from": "B", "text": "ne, ja ta precisando"},
        ],
        # Dialogo 2: Futebol
        [
            {"from": "A", "text": "viu o jogo ontem?"},
            {"from": "B", "text": "vi, que jogo hein"},
            {"from": "A", "text": "demais, nao esperava"},
            {"from": "B", "text": "tb nao, achei q ia perder"},
            {"from": "A", "text": "sorte q deu certo no final"},
            {"from": "B", "text": "agr e torcer pro proximo"},
        ],
        # Dialogo 3: Comida
        [
            {"from": "A", "text": "ja almocou?"},
            {"from": "B", "text": "to indo agr"},
            {"from": "A", "text": "oq vai comer"},
            {"from": "B", "text": "acho q prato feito msm"},
            {"from": "A", "text": "boa, eu pedi um delivery"},
            {"from": "B", "text": "tb queria mas to sem tempo"},
            {"from": "A", "text": "entendo, bom almoco"},
            {"from": "B", "text": "vlw, vc tb"},
        ],
        # Dialogo 4: Fim de semana
        [
            {"from": "A", "text": "vai fazer oq no fds?"},
            {"from": "B", "text": "nd ainda, talvez ficar em casa"},
            {"from": "A", "text": "entendo, eu vou visitar minha mae"},
            {"from": "B", "text": "q bom, faz tempo q vc foi?"},
            {"from": "A", "text": "faz umas 2 semanas"},
            {"from": "B", "text": "aproveita entao"},
        ],
        # Dialogo 5: Trabalho
        [
            {"from": "A", "text": "cara to cansado"},
            {"from": "B", "text": "muito trabalho?"},
            {"from": "A", "text": "demais, essa semana foi pesada"},
            {"from": "B", "text": "imagino, aqui tb ta corrido"},
            {"from": "A", "text": "pelo menos ta acabando"},
            {"from": "B", "text": "verdade, depois melhora"},
        ],
        # Dialogo 6: Series
        [
            {"from": "A", "text": "comecei aquela serie q vc falou"},
            {"from": "B", "text": "qual? a da netflix?"},
            {"from": "A", "text": "isso, to gostando"},
            {"from": "B", "text": "ne, muito boa"},
            {"from": "A", "text": "to no ep 3 ainda"},
            {"from": "B", "text": "depois so piora de tao boa"},
            {"from": "A", "text": "vou maratonar no fds"},
        ],
        # Dialogo 7: Com typo
        [
            {"from": "A", "text": "oi, td bem?"},
            {"from": "B", "text": "tudo, e voc?"},
            {"from": "B", "text": "vc*"},
            {"from": "A", "text": "kkk td certo"},
            {"from": "A", "text": "vou sair daqui a poco"},
            {"from": "B", "text": "pra onde?"},
            {"from": "A", "text": "mercado, preciso comprar umas coisas"},
            {"from": "B", "text": "blz, boas compras"},
        ],
        # Dialogo 8: Clima
        [
            {"from": "A", "text": "ta muito calor ai?"},
            {"from": "B", "text": "demais, insuportavel"},
            {"from": "A", "text": "aqui tb, nem da pra sair"},
            {"from": "B", "text": "to no ar condicionado o dia todo"},
            {"from": "A", "text": "sorte sua ter"},
            {"from": "B", "text": "poise, senao nao dava"},
        ],
    ]
    return random.choice(dialogos)
```

### DoD

- [ ] Minimo 8 dialogos pre-definidos
- [ ] Variedade de temas
- [ ] Pelo menos 1 com typo
- [ ] Dialogos parecem naturais
- [ ] Funcao retorna aleatorio

---

## Story 3.5: Injecao de Typos

### Objetivo
Adicionar typos intencionais em dialogos gerados.

### Implementacao

```python
import re


# Padroes de typos comuns
TYPOS_COMUNS = [
    ("voce", "voc"),
    ("você", "voc"),
    ("vc", "vx"),
    ("trabalho", "trbaalho"),
    ("trabalhando", "trbalhando"),
    ("onde", "aond"),
    ("quando", "qunado"),
    ("porque", "proque"),
    ("tambem", "tanbem"),
    ("também", "tanbem"),
    ("entao", "entaoo"),
    ("então", "entaoo"),
    ("legal", "leagal"),
    ("bom", "bpm"),
    ("bem", "bem"),
    ("dia", "dua"),
    ("que", "qeu"),
]


def injetar_typo(texto: str) -> tuple[str, str]:
    """
    Injeta um typo no texto e retorna a correcao.

    Args:
        texto: Texto original

    Returns:
        Tupla (texto_com_typo, correcao)
    """
    texto_lower = texto.lower()

    for palavra_certa, typo in TYPOS_COMUNS:
        if palavra_certa in texto_lower:
            # Substituir apenas primeira ocorrencia
            pattern = re.compile(re.escape(palavra_certa), re.IGNORECASE)
            texto_com_typo = pattern.sub(typo, texto, count=1)

            # Correcao e so a palavra certa com asterisco
            correcao = f"{palavra_certa}*"

            return texto_com_typo, correcao

    return texto, ""


def adicionar_typos_dialogo(
    mensagens: List[Dict[str, str]],
    probabilidade: float = 0.15
) -> List[Dict[str, str]]:
    """
    Adiciona typos naturais a um dialogo existente.

    Args:
        mensagens: Lista de mensagens
        probabilidade: Chance de adicionar typo (0-1)

    Returns:
        Dialogo com typos adicionados
    """
    resultado = []
    typos_adicionados = 0
    max_typos = 2  # Maximo de typos por dialogo

    for i, msg in enumerate(mensagens):
        resultado.append(msg)

        # Chance de adicionar typo
        if typos_adicionados < max_typos and random.random() < probabilidade:
            texto_com_typo, correcao = injetar_typo(msg["text"])

            if correcao:
                # Substituir mensagem original pelo typo
                resultado[-1] = {"from": msg["from"], "text": texto_com_typo}

                # Adicionar correcao como proxima mensagem (mesmo remetente)
                resultado.append({"from": msg["from"], "text": correcao})
                typos_adicionados += 1

    return resultado
```

### DoD

- [ ] Lista de typos comuns
- [ ] Funcao `injetar_typo` funcionando
- [ ] `adicionar_typos_dialogo` com probabilidade
- [ ] Maximo 2 typos por dialogo
- [ ] Correcao com asterisco

---

## Checklist do Epico

- [ ] **S25.E03.1** - Temas de conversa definidos
- [ ] **S25.E03.2** - Trending topics com cache
- [ ] **S25.E03.3** - Geracao via Claude
- [ ] **S25.E03.4** - Dialogos fallback
- [ ] **S25.E03.5** - Injecao de typos
- [ ] Conversas parecem naturais
- [ ] Linguagem informal brasileira
- [ ] Testes completos

---

## Validacao

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.services.warmer.conversation_generator import (
    escolher_tema,
    gerar_dialogo,
    gerar_dialogo_fallback,
    adicionar_typos_dialogo,
    injetar_typo,
)


def test_escolher_tema():
    """Testa escolha de temas."""
    temas = set()
    for _ in range(50):
        tema = escolher_tema(usar_sazonal=False)
        temas.add(tema)

    assert len(temas) > 5  # Deve ter variedade


def test_gerar_dialogo_fallback():
    """Testa geracao de dialogo fallback."""
    dialogo = gerar_dialogo_fallback()

    assert isinstance(dialogo, list)
    assert len(dialogo) >= 4

    for msg in dialogo:
        assert "from" in msg
        assert "text" in msg
        assert msg["from"] in ["A", "B"]


def test_injetar_typo():
    """Testa injecao de typo."""
    # Texto com palavra conhecida
    texto, correcao = injetar_typo("voce esta bem?")
    assert texto == "voc esta bem?"
    assert correcao == "voce*"

    # Texto sem palavra conhecida
    texto, correcao = injetar_typo("oi")
    assert texto == "oi"
    assert correcao == ""


def test_adicionar_typos_dialogo():
    """Testa adicao de typos em dialogo."""
    dialogo = [
        {"from": "A", "text": "voce vai sair?"},
        {"from": "B", "text": "sim, vou trabalhar"},
    ]

    # Com probabilidade 1 (sempre adiciona)
    resultado = adicionar_typos_dialogo(dialogo, probabilidade=1.0)

    # Deve ter mais mensagens (correcoes)
    assert len(resultado) >= len(dialogo)


@pytest.mark.asyncio
async def test_gerar_dialogo_com_claude():
    """Testa geracao com Claude (mockado)."""
    resposta_mock = json.dumps([
        {"from": "A", "text": "e ai blz"},
        {"from": "B", "text": "tudo e vc"},
        {"from": "A", "text": "de boa"},
        {"from": "B", "text": "q bom"},
    ])

    with patch("app.services.warmer.conversation_generator.claude_client") as mock:
        mock.generate = AsyncMock(return_value=resposta_mock)

        dialogo = await gerar_dialogo(tema="teste")

        assert len(dialogo) == 4
        assert dialogo[0]["from"] == "A"
```

---

## Exemplo de Dialogo Gerado

```json
[
  {"from": "A", "text": "e ai, viu o jogo do fla ontem?"},
  {"from": "B", "text": "vi, que jogo hein"},
  {"from": "A", "text": "demais, achei que ia perder"},
  {"from": "B", "text": "tb, mas viro no final"},
  {"from": "A", "text": "o gol do gabigol foi incrivel"},
  {"from": "B", "text": "poise, jogador diferenciado"},
  {"from": "A", "text": "agr e torcer pro campeoanto"},
  {"from": "A", "text": "campeonato*"},
  {"from": "B", "text": "kkkk ta dificil digitar ne"},
  {"from": "A", "text": "demais, celular ruim"},
  {"from": "B", "text": "entendo, o meu tb trava"},
  {"from": "A", "text": "bom, vou la, flw"},
  {"from": "B", "text": "flw, ate"}
]
```

