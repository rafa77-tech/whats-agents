# E08 - Deduplicação

## Objetivo

Identificar e agrupar vagas duplicadas que aparecem em múltiplos grupos.

## Contexto

A mesma vaga pode ser postada em vários grupos. Precisamos:
- Identificar duplicatas por hash (hospital + data + período + especialidade)
- Agrupar fontes da mesma vaga
- Manter apenas uma vaga principal
- Rastrear todas as fontes

## Stories

### S08.1 - Implementar cálculo de hash de deduplicação

**Descrição:** Função para calcular hash único da vaga.

```python
# app/services/grupos/deduplicador.py

import hashlib
from typing import Optional
from uuid import UUID


def calcular_hash_dedup(
    hospital_id: UUID,
    data: str,  # YYYY-MM-DD
    periodo_id: Optional[UUID],
    especialidade_id: UUID
) -> str:
    """
    Calcula hash para deduplicação.

    A chave é: hospital + data + período + especialidade
    """
    componentes = [
        str(hospital_id),
        data,
        str(periodo_id) if periodo_id else "null",
        str(especialidade_id),
    ]

    texto = "|".join(componentes)
    return hashlib.md5(texto.encode()).hexdigest()
```

**Estimativa:** 0.5h

---

### S08.2 - Verificar duplicatas existentes

**Descrição:** Buscar vagas com mesmo hash na janela temporal.

```python
from datetime import datetime, timedelta

JANELA_DEDUP_HORAS = 48


async def buscar_vaga_duplicada(
    hash_dedup: str,
    excluir_id: Optional[UUID] = None
) -> Optional[dict]:
    """
    Busca vaga existente com mesmo hash.

    Args:
        hash_dedup: Hash calculado
        excluir_id: ID para excluir da busca (a própria vaga)

    Returns:
        Vaga existente ou None
    """
    limite_tempo = datetime.utcnow() - timedelta(hours=JANELA_DEDUP_HORAS)

    query = supabase.table("vagas_grupo") \
        .select("id, qtd_fontes") \
        .eq("hash_dedup", hash_dedup) \
        .eq("eh_duplicada", False) \
        .gte("created_at", limite_tempo.isoformat())

    if excluir_id:
        query = query.neq("id", str(excluir_id))

    result = query.limit(1).execute()

    return result.data[0] if result.data else None
```

**Estimativa:** 1h

---

### S08.3 - Registrar fonte de vaga

**Descrição:** Adicionar fonte em `vagas_grupo_fontes`.

```python
async def registrar_fonte_vaga(
    vaga_principal_id: UUID,
    mensagem_id: UUID,
    grupo_id: UUID,
    contato_id: Optional[UUID] = None,
    texto_original: str = "",
    valor_informado: Optional[int] = None
) -> UUID:
    """Registra uma fonte adicional para a vaga."""

    # Contar fontes existentes
    count = supabase.table("vagas_grupo_fontes") \
        .select("id", count="exact") \
        .eq("vaga_grupo_id", str(vaga_principal_id)) \
        .execute()

    ordem = (count.count or 0) + 1

    dados = {
        "vaga_grupo_id": str(vaga_principal_id),
        "mensagem_id": str(mensagem_id),
        "grupo_id": str(grupo_id),
        "contato_id": str(contato_id) if contato_id else None,
        "ordem": ordem,
        "texto_original": texto_original[:500] if texto_original else None,
        "valor_informado": valor_informado,
    }

    result = supabase.table("vagas_grupo_fontes").insert(dados).execute()

    # Atualizar contador na vaga principal
    supabase.table("vagas_grupo") \
        .update({"qtd_fontes": ordem}) \
        .eq("id", str(vaga_principal_id)) \
        .execute()

    return UUID(result.data[0]["id"])
```

**Estimativa:** 1h

---

### S08.4 - Marcar vaga como duplicada

**Descrição:** Atualizar status da vaga duplicada.

```python
async def marcar_como_duplicada(
    vaga_id: UUID,
    duplicada_de: UUID
) -> None:
    """Marca vaga como duplicada de outra."""

    supabase.table("vagas_grupo") \
        .update({
            "status": "duplicada",
            "eh_duplicada": True,
            "duplicada_de": str(duplicada_de),
            "motivo_status": "duplicata_detectada",
        }) \
        .eq("id", str(vaga_id)) \
        .execute()
```

**Estimativa:** 0.5h

---

### S08.5 - Processador de deduplicação

**Descrição:** Orquestra o processo de deduplicação.

```python
async def processar_deduplicacao(vaga_id: UUID) -> dict:
    """
    Processa deduplicação para uma vaga.

    Returns:
        {"duplicada": bool, "principal_id": UUID ou None}
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

    # Verificar se tem dados para hash
    if not dados.get("hospital_id") or not dados.get("especialidade_id"):
        return {"erro": "dados_insuficientes"}

    # Calcular hash
    hash_dedup = calcular_hash_dedup(
        hospital_id=UUID(dados["hospital_id"]),
        data=dados.get("data", ""),
        periodo_id=UUID(dados["periodo_id"]) if dados.get("periodo_id") else None,
        especialidade_id=UUID(dados["especialidade_id"])
    )

    # Salvar hash
    supabase.table("vagas_grupo") \
        .update({"hash_dedup": hash_dedup}) \
        .eq("id", str(vaga_id)) \
        .execute()

    # Verificar duplicata
    existente = await buscar_vaga_duplicada(hash_dedup, excluir_id=vaga_id)

    if existente:
        # É duplicata
        principal_id = UUID(existente["id"])

        await registrar_fonte_vaga(
            vaga_principal_id=principal_id,
            mensagem_id=UUID(dados["mensagem_id"]),
            grupo_id=UUID(dados["grupo_origem_id"]),
            contato_id=UUID(dados["contato_responsavel_id"]) if dados.get("contato_responsavel_id") else None,
            valor_informado=dados.get("valor")
        )

        await marcar_como_duplicada(vaga_id, principal_id)

        return {"duplicada": True, "principal_id": principal_id}

    # Não é duplicata - registrar como fonte principal
    await registrar_fonte_vaga(
        vaga_principal_id=vaga_id,
        mensagem_id=UUID(dados["mensagem_id"]),
        grupo_id=UUID(dados["grupo_origem_id"]),
        contato_id=UUID(dados["contato_responsavel_id"]) if dados.get("contato_responsavel_id") else None,
        valor_informado=dados.get("valor")
    )

    return {"duplicada": False, "principal_id": vaga_id}


async def processar_batch_deduplicacao(limite: int = 100) -> dict:
    """Processa batch de vagas normalizadas para deduplicação."""

    vagas = supabase.table("vagas_grupo") \
        .select("id") \
        .eq("status", "normalizada") \
        .is_("hash_dedup", "null") \
        .limit(limite) \
        .execute()

    stats = {
        "total": len(vagas.data),
        "novas": 0,
        "duplicadas": 0,
        "erros": 0,
    }

    for vaga in vagas.data:
        try:
            resultado = await processar_deduplicacao(UUID(vaga["id"]))

            if resultado.get("duplicada"):
                stats["duplicadas"] += 1
            else:
                stats["novas"] += 1

        except Exception as e:
            logger.error(f"Erro ao deduplicar vaga {vaga['id']}: {e}")
            stats["erros"] += 1

    return stats
```

**Estimativa:** 2h

---

### S08.6 - Testes de deduplicação

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S08.1 | Cálculo de hash | 0.5h |
| S08.2 | Verificar duplicatas | 1h |
| S08.3 | Registrar fonte | 1h |
| S08.4 | Marcar duplicada | 0.5h |
| S08.5 | Processador | 2h |
| S08.6 | Testes | 2h |

**Total:** 7h (~1 dia)

## Dependências

- E06 (Fuzzy Match) - hospital_id e especialidade_id normalizados

## Entregáveis

- Hash de deduplicação
- Rastreamento de múltiplas fontes
- Janela temporal de 48h
- Métricas de duplicação
