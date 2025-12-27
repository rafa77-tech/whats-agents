# E07 - Criação de Hospital via Web

## Objetivo

Quando não encontrar match para um hospital, buscar informações na web e criar automaticamente.

## Contexto

- Se fuzzy match < 70%, hospital é desconhecido
- Buscar na web: nome oficial, endereço, cidade
- Criar registro em `hospitais`
- Criar alias automaticamente

## Stories

### S07.1 - Implementar busca web de hospital

**Descrição:** Usar WebSearch para encontrar informações do hospital.

```python
# app/services/grupos/hospital_web.py

from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InfoHospitalWeb:
    """Informações do hospital encontradas na web."""
    nome_oficial: str
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    confianca: float = 0.0
    fonte: Optional[str] = None


async def buscar_hospital_web(
    nome_hospital: str,
    regiao_hint: str = ""
) -> Optional[InfoHospitalWeb]:
    """
    Busca informações do hospital na web.

    Args:
        nome_hospital: Nome extraído da mensagem
        regiao_hint: Dica de região (do grupo)

    Returns:
        InfoHospitalWeb ou None
    """
    import anthropic
    from app.core.config import settings

    # Construir query de busca
    query = f"{nome_hospital} hospital endereço"
    if regiao_hint:
        query += f" {regiao_hint}"

    # Usar Claude com tool de web search (se disponível)
    # Ou usar API de busca direta

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""
    Busque informações sobre o hospital/clínica: "{nome_hospital}"
    Região provável: {regiao_hint or "Brasil"}

    Encontre e retorne em JSON:
    - nome_oficial: Nome completo oficial
    - logradouro: Rua/Avenida
    - numero: Número
    - bairro: Bairro
    - cidade: Cidade
    - estado: Sigla do estado (SP, RJ, etc)
    - cep: CEP
    - confianca: 0-1 (quão confiante está nos dados)
    - fonte: URL de onde veio a informação

    Se não encontrar, retorne: {{"encontrado": false}}
    """

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parsear resposta
        import json
        dados = json.loads(response.content[0].text)

        if not dados.get("encontrado", True):
            return None

        return InfoHospitalWeb(
            nome_oficial=dados.get("nome_oficial", nome_hospital),
            logradouro=dados.get("logradouro"),
            numero=dados.get("numero"),
            bairro=dados.get("bairro"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            cep=dados.get("cep"),
            confianca=dados.get("confianca", 0.5),
            fonte=dados.get("fonte")
        )

    except Exception as e:
        logger.error(f"Erro ao buscar hospital na web: {e}")
        return None
```

**Estimativa:** 2h

---

### S07.2 - Criar hospital no banco

**Descrição:** Inserir novo hospital com dados da web.

```python
async def criar_hospital(
    info: InfoHospitalWeb,
    alias_original: str
) -> UUID:
    """
    Cria hospital no banco de dados.

    Args:
        info: Informações da web
        alias_original: Nome original da mensagem (para criar alias)

    Returns:
        UUID do hospital criado
    """
    from app.services.supabase import supabase

    # Criar hospital
    dados_hospital = {
        "nome": info.nome_oficial,
        "logradouro": info.logradouro,
        "numero": info.numero,
        "bairro": info.bairro,
        "cidade": info.cidade,
        "estado": info.estado,
        "cep": info.cep,
    }

    result = supabase.table("hospitais").insert(dados_hospital).execute()
    hospital_id = UUID(result.data[0]["id"])

    logger.info(f"Hospital criado: {hospital_id} - {info.nome_oficial}")

    # Criar alias com nome original
    alias_norm = normalizar_para_busca(alias_original)

    supabase.table("hospitais_alias").insert({
        "hospital_id": str(hospital_id),
        "alias": alias_original,
        "alias_normalizado": alias_norm,
        "origem": "sistema_auto",
        "confianca": info.confianca,
    }).execute()

    # Criar alias com nome oficial também
    if info.nome_oficial != alias_original:
        nome_norm = normalizar_para_busca(info.nome_oficial)
        supabase.table("hospitais_alias").insert({
            "hospital_id": str(hospital_id),
            "alias": info.nome_oficial,
            "alias_normalizado": nome_norm,
            "origem": "sistema_auto",
            "confianca": 1.0,
        }).execute()

    return hospital_id
```

**Estimativa:** 1.5h

---

### S07.3 - Fallback sem dados web

**Descrição:** Criar hospital mínimo se busca web falhar.

```python
async def criar_hospital_minimo(
    nome: str,
    regiao_grupo: str = ""
) -> UUID:
    """
    Cria hospital com dados mínimos.

    Usado quando busca web falha.
    """
    # Tentar inferir cidade/estado da região do grupo
    cidade = None
    estado = None

    if regiao_grupo:
        # Mapa simples de regiões conhecidas
        REGIOES = {
            "abc": ("Santo André", "SP"),
            "sp capital": ("São Paulo", "SP"),
            "campinas": ("Campinas", "SP"),
            "rj": ("Rio de Janeiro", "RJ"),
        }

        regiao_norm = regiao_grupo.lower()
        for key, (c, e) in REGIOES.items():
            if key in regiao_norm:
                cidade = c
                estado = e
                break

    dados = {
        "nome": nome,
        "cidade": cidade,
        "estado": estado,
    }

    result = supabase.table("hospitais").insert(dados).execute()
    hospital_id = UUID(result.data[0]["id"])

    # Criar alias
    supabase.table("hospitais_alias").insert({
        "hospital_id": str(hospital_id),
        "alias": nome,
        "alias_normalizado": normalizar_para_busca(nome),
        "origem": "sistema_auto",
        "confianca": 0.5,  # Baixa confiança
    }).execute()

    logger.info(f"Hospital mínimo criado: {hospital_id} - {nome}")

    return hospital_id
```

**Estimativa:** 1h

---

### S07.4 - Integrar com normalizador

**Descrição:** Chamar criação de hospital quando match falha.

```python
async def normalizar_hospital(texto: str, regiao_grupo: str = "") -> tuple:
    """
    Normaliza hospital, criando se necessário.

    Returns:
        Tuple (hospital_id, nome, score, foi_criado)
    """
    # Primeiro tenta alias
    match = await buscar_hospital_por_alias(texto)
    if match:
        return (*match, False)

    # Tenta similaridade
    match = await buscar_hospital_por_similaridade(texto, threshold=0.7)
    if match:
        return (*match, False)

    # Não encontrou - criar novo
    logger.info(f"Hospital não encontrado, buscando na web: {texto}")

    info = await buscar_hospital_web(texto, regiao_grupo)

    if info and info.confianca >= 0.6:
        hospital_id = await criar_hospital(info, texto)
        return (hospital_id, info.nome_oficial, info.confianca, True)

    # Fallback - criar mínimo
    hospital_id = await criar_hospital_minimo(texto, regiao_grupo)
    return (hospital_id, texto, 0.3, True)
```

**Estimativa:** 1h

---

### S07.5 - Marcar hospitais criados automaticamente

**Descrição:** Flag para identificar hospitais que precisam revisão.

```sql
-- Adicionar coluna na tabela hospitais
ALTER TABLE hospitais
ADD COLUMN criado_automaticamente BOOLEAN DEFAULT false,
ADD COLUMN precisa_revisao BOOLEAN DEFAULT false,
ADD COLUMN revisado_em TIMESTAMPTZ,
ADD COLUMN revisado_por TEXT;
```

**Estimativa:** 0.5h

---

### S07.6 - Testes

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S07.1 | Busca web | 2h |
| S07.2 | Criar hospital | 1.5h |
| S07.3 | Fallback mínimo | 1h |
| S07.4 | Integrar normalizador | 1h |
| S07.5 | Flags de revisão | 0.5h |
| S07.6 | Testes | 2h |

**Total:** 8h (~1 dia)

## Dependências

- E06 (Fuzzy Match)

## Entregáveis

- Busca web de hospitais
- Criação automática com dados enriquecidos
- Fallback para dados mínimos
- Flags de revisão
