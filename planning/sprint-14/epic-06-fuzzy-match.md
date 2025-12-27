# E06 - Fuzzy Match de Entidades

## Objetivo

Implementar matching fuzzy para normalizar nomes de hospitais e especialidades extraídos para entidades do banco de dados.

## Contexto

Dados extraídos vêm como texto livre ("HSL ABC", "cardio", "CM"). Precisamos:
- Fazer match com tabelas `hospitais` e `especialidades`
- Usar aliases conhecidos
- Calcular score de similaridade
- Decidir se é match confiável ou precisa revisão

## Stories

### S06.1 - Implementar normalização de texto

**Descrição:** Funções para normalizar texto antes do match.

```python
# app/services/grupos/normalizador.py

import unicodedata
import re


def normalizar_para_busca(texto: str) -> str:
    """Normaliza texto para busca."""
    if not texto:
        return ""

    # Lowercase
    texto = texto.lower()

    # Remover acentos
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))

    # Remover caracteres especiais
    texto = re.sub(r'[^\w\s]', '', texto)

    # Remover espaços extras
    texto = ' '.join(texto.split())

    return texto


def extrair_tokens(texto: str) -> set:
    """Extrai tokens significativos."""
    texto = normalizar_para_busca(texto)
    tokens = set(texto.split())

    # Remover stopwords
    stopwords = {'de', 'do', 'da', 'dos', 'das', 'e', 'ou', 'o', 'a'}
    tokens = tokens - stopwords

    return tokens
```

**Estimativa:** 1h

---

### S06.2 - Implementar busca em alias

**Descrição:** Buscar primeiro nos aliases conhecidos.

```python
async def buscar_hospital_por_alias(texto: str) -> Optional[tuple]:
    """
    Busca hospital por alias.

    Returns:
        Tuple (hospital_id, nome, score) ou None
    """
    texto_norm = normalizar_para_busca(texto)

    # Match exato em alias
    result = supabase.table("hospitais_alias") \
        .select("hospital_id, hospitais(nome)") \
        .eq("alias_normalizado", texto_norm) \
        .limit(1) \
        .execute()

    if result.data:
        return (
            UUID(result.data[0]["hospital_id"]),
            result.data[0]["hospitais"]["nome"],
            1.0  # Match exato
        )

    return None
```

**Estimativa:** 1h

---

### S06.3 - Implementar similaridade com trigrams

**Descrição:** Usar pg_trgm para calcular similaridade.

```python
async def buscar_hospital_por_similaridade(texto: str, threshold: float = 0.3) -> Optional[tuple]:
    """
    Busca hospital por similaridade de texto.

    Uses PostgreSQL pg_trgm extension.
    """
    texto_norm = normalizar_para_busca(texto)

    # Usar função RPC do Supabase
    result = supabase.rpc(
        "buscar_hospital_por_alias",
        {"p_texto": texto_norm}
    ).execute()

    if result.data and result.data[0]["score"] >= threshold:
        return (
            UUID(result.data[0]["hospital_id"]),
            result.data[0]["nome"],
            result.data[0]["score"]
        )

    return None
```

**Estimativa:** 1.5h

---

### S06.4 - Implementar match de especialidade

**Descrição:** Mesma lógica para especialidades.

```python
async def normalizar_especialidade(texto: str) -> Optional[tuple]:
    """
    Normaliza especialidade para ID do banco.

    Returns:
        Tuple (especialidade_id, nome, score) ou None
    """
    # Primeiro tenta alias
    alias_match = await buscar_especialidade_por_alias(texto)
    if alias_match:
        return alias_match

    # Depois tenta similaridade
    return await buscar_especialidade_por_similaridade(texto)
```

**Estimativa:** 1h

---

### S06.5 - Implementar match de período/setor/tipo

**Descrição:** Match simples para enums conhecidos.

```python
MAPA_PERIODOS = {
    "noturno": "Noturno",
    "diurno": "Diurno",
    "manha": "Meio período (manhã)",
    "tarde": "Meio período (tarde)",
    "vespertino": "Vespertino",
    "cinderela": "Cinderela",
    "12h": "Diurno",
    "24h": "Diurno",  # Precisa lógica especial
}

async def normalizar_periodo(texto: str) -> Optional[UUID]:
    """Normaliza período para ID."""
    if not texto:
        return None

    texto_norm = normalizar_para_busca(texto)

    # Buscar no mapa
    nome_periodo = None
    for key, value in MAPA_PERIODOS.items():
        if key in texto_norm:
            nome_periodo = value
            break

    if not nome_periodo:
        return None

    # Buscar ID
    result = supabase.table("periodos") \
        .select("id") \
        .eq("nome", nome_periodo) \
        .limit(1) \
        .execute()

    return UUID(result.data[0]["id"]) if result.data else None
```

**Estimativa:** 1h

---

### S06.6 - Processador de normalização

**Descrição:** Orquestra normalização de vagas.

```python
async def normalizar_vaga(vaga_id: UUID) -> dict:
    """
    Normaliza uma vaga extraída.

    Atualiza vagas_grupo com IDs normalizados.
    """
    # Buscar vaga
    vaga = supabase.table("vagas_grupo") \
        .select("*") \
        .eq("id", str(vaga_id)) \
        .single() \
        .execute()

    if not vaga.data:
        return {"erro": "vaga_nao_encontrada"}

    dados = vaga.data
    updates = {}
    scores = {}

    # Normalizar hospital
    if dados.get("hospital_raw"):
        match = await normalizar_hospital(dados["hospital_raw"])
        if match:
            updates["hospital_id"] = str(match[0])
            updates["hospital_match_score"] = match[2]
            scores["hospital"] = match[2]

    # Normalizar especialidade
    if dados.get("especialidade_raw"):
        match = await normalizar_especialidade(dados["especialidade_raw"])
        if match:
            updates["especialidade_id"] = str(match[0])
            updates["especialidade_match_score"] = match[2]
            scores["especialidade"] = match[2]

    # Normalizar período
    if dados.get("periodo_raw"):
        periodo_id = await normalizar_periodo(dados["periodo_raw"])
        if periodo_id:
            updates["periodo_id"] = str(periodo_id)

    # Normalizar setor
    if dados.get("setor_raw"):
        setor_id = await normalizar_setor(dados["setor_raw"])
        if setor_id:
            updates["setor_id"] = str(setor_id)

    # Atualizar status
    if updates.get("hospital_id") and updates.get("especialidade_id"):
        updates["status"] = "normalizada"
        updates["dados_minimos_ok"] = True
    else:
        updates["status"] = "aguardando_revisao"
        updates["motivo_status"] = "match_incompleto"

    # Salvar
    supabase.table("vagas_grupo") \
        .update(updates) \
        .eq("id", str(vaga_id)) \
        .execute()

    return {"scores": scores, "status": updates.get("status")}
```

**Estimativa:** 2h

---

### S06.7 - Testes de normalização

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S06.1 | Normalização de texto | 1h |
| S06.2 | Busca em alias | 1h |
| S06.3 | Similaridade trigrams | 1.5h |
| S06.4 | Match especialidade | 1h |
| S06.5 | Match período/setor | 1h |
| S06.6 | Processador normalização | 2h |
| S06.7 | Testes | 2h |

**Total:** 9.5h (~1.25 dias)

## Dependências

- E01 (Modelo de Dados - tabelas de alias)
- E05 (Extração)

## Entregáveis

- Normalização de hospital com score
- Normalização de especialidade
- Normalização de campos secundários
- Testes com diversos casos
