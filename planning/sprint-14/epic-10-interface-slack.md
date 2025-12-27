# E10 - Interface Slack

## Objetivo

Tools no Slack para revisar e gerenciar vagas capturadas de grupos.

## Contexto

O gestor precisa:
- Ver vagas aguardando revisão
- Aprovar/rejeitar vagas manualmente
- Ver estatísticas de captura
- Corrigir dados extraídos
- Gerenciar aliases de hospitais

## Stories

### S10.1 - Tool: Listar vagas para revisão

**Descrição:** Tool para listar vagas aguardando aprovação.

```python
# app/tools/slack/grupos.py

from typing import Optional
from app.services.supabase import supabase


async def tool_listar_vagas_revisao(
    limite: int = 10,
    grupo: Optional[str] = None
) -> dict:
    """
    Lista vagas de grupos aguardando revisão.

    Args:
        limite: Máximo de vagas (default 10)
        grupo: Filtrar por nome do grupo

    Returns:
        Lista de vagas com detalhes
    """
    query = supabase.table("vagas_grupo") \
        .select("""
            id,
            hospital_raw,
            especialidade_raw,
            data,
            periodo_raw,
            valor,
            confianca_geral,
            created_at,
            grupos_whatsapp!inner(nome),
            hospitais(nome),
            especialidades(nome)
        """) \
        .eq("status", "aguardando_revisao") \
        .order("confianca_geral", desc=True) \
        .limit(limite)

    if grupo:
        query = query.ilike("grupos_whatsapp.nome", f"%{grupo}%")

    result = query.execute()

    vagas = []
    for v in result.data:
        vagas.append({
            "id": v["id"][:8],  # ID curto
            "id_completo": v["id"],
            "hospital": v.get("hospitais", {}).get("nome") or v["hospital_raw"],
            "hospital_raw": v["hospital_raw"],
            "especialidade": v.get("especialidades", {}).get("nome") or v["especialidade_raw"],
            "data": v["data"],
            "periodo": v["periodo_raw"],
            "valor": v["valor"],
            "confianca": f"{v['confianca_geral']*100:.0f}%" if v.get("confianca_geral") else "N/A",
            "grupo": v["grupos_whatsapp"]["nome"],
            "criada": v["created_at"][:10],
        })

    return {
        "total": len(vagas),
        "vagas": vagas,
        "mensagem": f"Encontradas {len(vagas)} vagas aguardando revisão"
    }
```

**Estimativa:** 1.5h

---

### S10.2 - Tool: Aprovar vaga

**Descrição:** Aprovar e importar vaga manualmente.

```python
async def tool_aprovar_vaga(
    vaga_id: str,
    correcoes: Optional[dict] = None
) -> dict:
    """
    Aprova vaga para importação.

    Args:
        vaga_id: ID da vaga (curto ou completo)
        correcoes: Dicionário com correções opcionais
            - hospital_id
            - especialidade_id
            - data
            - valor

    Returns:
        Resultado da aprovação
    """
    from app.services.grupos.importador import criar_vaga_principal, atualizar_vaga_grupo_importada
    from uuid import UUID

    # Buscar vaga
    vaga_id_completo = await resolver_id_vaga(vaga_id)
    if not vaga_id_completo:
        return {"erro": f"Vaga não encontrada: {vaga_id}"}

    vaga = supabase.table("vagas_grupo") \
        .select("*") \
        .eq("id", vaga_id_completo) \
        .single() \
        .execute()

    if not vaga.data:
        return {"erro": "Vaga não encontrada"}

    dados = vaga.data

    # Verificar status
    if dados["status"] != "aguardando_revisao":
        return {"erro": f"Vaga não está em revisão. Status: {dados['status']}"}

    # Aplicar correções
    if correcoes:
        for campo, valor in correcoes.items():
            if campo in ["hospital_id", "especialidade_id", "data", "valor", "periodo_id"]:
                dados[campo] = valor

        # Salvar correções
        supabase.table("vagas_grupo") \
            .update(correcoes) \
            .eq("id", vaga_id_completo) \
            .execute()

    # Validar dados mínimos
    if not dados.get("hospital_id") or not dados.get("especialidade_id"):
        return {
            "erro": "Dados insuficientes para importar",
            "faltando": [
                "hospital_id" if not dados.get("hospital_id") else None,
                "especialidade_id" if not dados.get("especialidade_id") else None,
            ]
        }

    # Importar
    try:
        vaga_principal_id = await criar_vaga_principal(dados)
        await atualizar_vaga_grupo_importada(UUID(vaga_id_completo), vaga_principal_id)

        return {
            "sucesso": True,
            "vaga_id": str(vaga_principal_id),
            "mensagem": f"Vaga importada com sucesso! ID: {str(vaga_principal_id)[:8]}"
        }

    except Exception as e:
        return {"erro": f"Falha ao importar: {str(e)}"}


async def resolver_id_vaga(vaga_id: str) -> Optional[str]:
    """Resolve ID curto para completo."""
    if len(vaga_id) == 36:  # UUID completo
        return vaga_id

    # Buscar por prefixo
    result = supabase.table("vagas_grupo") \
        .select("id") \
        .ilike("id", f"{vaga_id}%") \
        .limit(1) \
        .execute()

    return result.data[0]["id"] if result.data else None
```

**Estimativa:** 2h

---

### S10.3 - Tool: Rejeitar vaga

**Descrição:** Rejeitar vaga com motivo.

```python
async def tool_rejeitar_vaga(
    vaga_id: str,
    motivo: str = "rejeitada_manualmente"
) -> dict:
    """
    Rejeita vaga de grupo.

    Args:
        vaga_id: ID da vaga
        motivo: Motivo da rejeição

    Returns:
        Resultado da rejeição
    """
    vaga_id_completo = await resolver_id_vaga(vaga_id)
    if not vaga_id_completo:
        return {"erro": f"Vaga não encontrada: {vaga_id}"}

    supabase.table("vagas_grupo") \
        .update({
            "status": "descartada",
            "motivo_status": motivo,
            "revisado_em": "now()",
        }) \
        .eq("id", vaga_id_completo) \
        .execute()

    return {
        "sucesso": True,
        "mensagem": f"Vaga {vaga_id} rejeitada. Motivo: {motivo}"
    }
```

**Estimativa:** 0.5h

---

### S10.4 - Tool: Ver detalhes da vaga

**Descrição:** Ver todos os dados extraídos de uma vaga.

```python
async def tool_detalhes_vaga(vaga_id: str) -> dict:
    """
    Mostra detalhes completos de uma vaga de grupo.

    Args:
        vaga_id: ID da vaga

    Returns:
        Todos os dados da vaga
    """
    vaga_id_completo = await resolver_id_vaga(vaga_id)
    if not vaga_id_completo:
        return {"erro": f"Vaga não encontrada: {vaga_id}"}

    vaga = supabase.table("vagas_grupo") \
        .select("""
            *,
            grupos_whatsapp(nome, regiao),
            contatos_grupo(nome, telefone),
            hospitais(nome, cidade),
            especialidades(nome),
            periodos(nome),
            vagas_grupo_fontes(
                ordem,
                grupos_whatsapp(nome),
                valor_informado
            )
        """) \
        .eq("id", vaga_id_completo) \
        .single() \
        .execute()

    if not vaga.data:
        return {"erro": "Vaga não encontrada"}

    dados = vaga.data

    return {
        "id": dados["id"][:8],
        "status": dados["status"],
        "confianca": f"{dados.get('confianca_geral', 0)*100:.0f}%",

        "dados_extraidos": {
            "hospital_raw": dados["hospital_raw"],
            "especialidade_raw": dados["especialidade_raw"],
            "data": dados["data"],
            "periodo_raw": dados["periodo_raw"],
            "valor": dados["valor"],
            "observacoes": dados.get("observacoes_raw"),
        },

        "dados_normalizados": {
            "hospital": dados.get("hospitais", {}).get("nome"),
            "hospital_score": f"{dados.get('hospital_match_score', 0)*100:.0f}%",
            "especialidade": dados.get("especialidades", {}).get("nome"),
            "especialidade_score": f"{dados.get('especialidade_match_score', 0)*100:.0f}%",
            "periodo": dados.get("periodos", {}).get("nome"),
        },

        "origem": {
            "grupo": dados["grupos_whatsapp"]["nome"],
            "regiao": dados["grupos_whatsapp"].get("regiao"),
            "contato": dados.get("contatos_grupo", {}).get("nome"),
            "telefone": dados.get("contatos_grupo", {}).get("telefone"),
        },

        "fontes": [
            {
                "ordem": f["ordem"],
                "grupo": f["grupos_whatsapp"]["nome"],
                "valor": f["valor_informado"],
            }
            for f in dados.get("vagas_grupo_fontes", [])
        ],

        "timestamps": {
            "criada": dados["created_at"],
            "mensagem": dados.get("mensagem_created_at"),
        }
    }
```

**Estimativa:** 1.5h

---

### S10.5 - Tool: Estatísticas de captura

**Descrição:** Ver métricas de captura de grupos.

```python
async def tool_estatisticas_grupos(periodo: str = "hoje") -> dict:
    """
    Mostra estatísticas de captura de vagas de grupos.

    Args:
        periodo: hoje, semana, mes

    Returns:
        Estatísticas consolidadas
    """
    from datetime import datetime, timedelta

    # Calcular data início
    hoje = datetime.now().date()
    if periodo == "hoje":
        data_inicio = hoje
    elif periodo == "semana":
        data_inicio = hoje - timedelta(days=7)
    elif periodo == "mes":
        data_inicio = hoje - timedelta(days=30)
    else:
        data_inicio = hoje

    data_inicio_str = data_inicio.isoformat()

    # Mensagens processadas
    msgs = supabase.table("mensagens_grupo") \
        .select("id", count="exact") \
        .gte("created_at", data_inicio_str) \
        .execute()

    # Vagas extraídas (por status)
    vagas_stats = supabase.rpc("stats_vagas_grupo", {
        "data_inicio": data_inicio_str
    }).execute()

    # Top grupos
    top_grupos = supabase.rpc("top_grupos_vagas", {
        "data_inicio": data_inicio_str,
        "limite": 5
    }).execute()

    stats = vagas_stats.data[0] if vagas_stats.data else {}

    return {
        "periodo": periodo,
        "data_inicio": data_inicio_str,

        "mensagens": {
            "total": msgs.count or 0,
        },

        "vagas": {
            "total": stats.get("total", 0),
            "importadas": stats.get("importadas", 0),
            "aguardando_revisao": stats.get("revisao", 0),
            "descartadas": stats.get("descartadas", 0),
            "duplicadas": stats.get("duplicadas", 0),
        },

        "taxas": {
            "conversao": f"{stats.get('taxa_conversao', 0)*100:.1f}%",
            "auto_import": f"{stats.get('taxa_auto', 0)*100:.1f}%",
            "duplicacao": f"{stats.get('taxa_dup', 0)*100:.1f}%",
        },

        "top_grupos": [
            {"nome": g["nome"], "vagas": g["total"]}
            for g in (top_grupos.data or [])
        ],

        "mensagem": f"Estatísticas de {periodo}: {stats.get('importadas', 0)} vagas importadas"
    }
```

**Estimativa:** 2h

---

### S10.6 - Tool: Gerenciar alias de hospital

**Descrição:** Adicionar alias para melhorar match futuro.

```python
async def tool_adicionar_alias_hospital(
    hospital_id: str,
    alias: str
) -> dict:
    """
    Adiciona alias para hospital.

    Args:
        hospital_id: ID do hospital
        alias: Novo alias a adicionar

    Returns:
        Resultado da operação
    """
    from app.services.grupos.normalizador import normalizar_para_busca

    # Verificar hospital existe
    hospital = supabase.table("hospitais") \
        .select("id, nome") \
        .eq("id", hospital_id) \
        .single() \
        .execute()

    if not hospital.data:
        return {"erro": f"Hospital não encontrado: {hospital_id}"}

    # Normalizar alias
    alias_norm = normalizar_para_busca(alias)

    # Verificar se já existe
    existente = supabase.table("hospitais_alias") \
        .select("id") \
        .eq("alias_normalizado", alias_norm) \
        .limit(1) \
        .execute()

    if existente.data:
        return {"erro": f"Alias já existe: {alias}"}

    # Criar alias
    supabase.table("hospitais_alias").insert({
        "hospital_id": hospital_id,
        "alias": alias,
        "alias_normalizado": alias_norm,
        "origem": "gestor_manual",
        "confianca": 1.0,
    }).execute()

    return {
        "sucesso": True,
        "mensagem": f"Alias '{alias}' adicionado ao hospital '{hospital.data['nome']}'"
    }


async def tool_buscar_hospital(termo: str) -> dict:
    """
    Busca hospital por nome ou alias.

    Args:
        termo: Termo de busca

    Returns:
        Lista de hospitais encontrados
    """
    from app.services.grupos.normalizador import normalizar_para_busca

    termo_norm = normalizar_para_busca(termo)

    result = supabase.rpc("buscar_hospital_por_alias", {
        "p_texto": termo_norm
    }).execute()

    return {
        "termo": termo,
        "resultados": [
            {
                "id": r["hospital_id"],
                "nome": r["nome"],
                "score": f"{r['score']*100:.0f}%",
            }
            for r in (result.data or [])[:5]
        ]
    }
```

**Estimativa:** 1.5h

---

### S10.7 - Registrar tools no sistema

**Descrição:** Adicionar tools ao registro de Slack.

```python
# Adicionar em app/tools/slack/__init__.py

TOOLS_GRUPOS = [
    {
        "nome": "listar_vagas_revisao",
        "descricao": "Lista vagas de grupos aguardando revisão",
        "funcao": tool_listar_vagas_revisao,
        "parametros": ["limite", "grupo"],
    },
    {
        "nome": "aprovar_vaga",
        "descricao": "Aprova vaga para importação",
        "funcao": tool_aprovar_vaga,
        "parametros": ["vaga_id", "correcoes"],
        "confirmacao": True,
    },
    {
        "nome": "rejeitar_vaga",
        "descricao": "Rejeita vaga de grupo",
        "funcao": tool_rejeitar_vaga,
        "parametros": ["vaga_id", "motivo"],
        "confirmacao": True,
    },
    {
        "nome": "detalhes_vaga_grupo",
        "descricao": "Mostra detalhes de vaga de grupo",
        "funcao": tool_detalhes_vaga,
        "parametros": ["vaga_id"],
    },
    {
        "nome": "estatisticas_grupos",
        "descricao": "Mostra estatísticas de captura de grupos",
        "funcao": tool_estatisticas_grupos,
        "parametros": ["periodo"],
    },
    {
        "nome": "adicionar_alias_hospital",
        "descricao": "Adiciona alias para hospital",
        "funcao": tool_adicionar_alias_hospital,
        "parametros": ["hospital_id", "alias"],
        "confirmacao": True,
    },
    {
        "nome": "buscar_hospital",
        "descricao": "Busca hospital por nome",
        "funcao": tool_buscar_hospital,
        "parametros": ["termo"],
    },
]
```

**Estimativa:** 1h

---

### S10.8 - Funções SQL auxiliares

**Descrição:** Criar funções no banco para estatísticas.

```sql
-- Função: Estatísticas de vagas de grupo
CREATE OR REPLACE FUNCTION stats_vagas_grupo(data_inicio DATE)
RETURNS TABLE (
    total BIGINT,
    importadas BIGINT,
    revisao BIGINT,
    descartadas BIGINT,
    duplicadas BIGINT,
    taxa_conversao NUMERIC,
    taxa_auto NUMERIC,
    taxa_dup NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total,
        COUNT(*) FILTER (WHERE status = 'importada')::BIGINT as importadas,
        COUNT(*) FILTER (WHERE status = 'aguardando_revisao')::BIGINT as revisao,
        COUNT(*) FILTER (WHERE status = 'descartada')::BIGINT as descartadas,
        COUNT(*) FILTER (WHERE eh_duplicada = true)::BIGINT as duplicadas,
        COALESCE(
            COUNT(*) FILTER (WHERE status = 'importada')::NUMERIC / NULLIF(COUNT(*), 0),
            0
        ) as taxa_conversao,
        COALESCE(
            COUNT(*) FILTER (WHERE status = 'importada' AND revisado_em IS NULL)::NUMERIC
            / NULLIF(COUNT(*) FILTER (WHERE status = 'importada'), 0),
            0
        ) as taxa_auto,
        COALESCE(
            COUNT(*) FILTER (WHERE eh_duplicada = true)::NUMERIC / NULLIF(COUNT(*), 0),
            0
        ) as taxa_dup
    FROM vagas_grupo
    WHERE created_at >= data_inicio;
END;
$$ LANGUAGE plpgsql;


-- Função: Top grupos por vagas
CREATE OR REPLACE FUNCTION top_grupos_vagas(data_inicio DATE, limite INT DEFAULT 5)
RETURNS TABLE (
    grupo_id UUID,
    nome TEXT,
    total BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        g.id as grupo_id,
        g.nome,
        COUNT(v.id)::BIGINT as total
    FROM grupos_whatsapp g
    JOIN vagas_grupo v ON v.grupo_origem_id = g.id
    WHERE v.created_at >= data_inicio
      AND v.status = 'importada'
    GROUP BY g.id, g.nome
    ORDER BY total DESC
    LIMIT limite;
END;
$$ LANGUAGE plpgsql;
```

**Estimativa:** 1h

---

### S10.9 - Testes de tools Slack

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S10.1 | Listar vagas revisão | 1.5h |
| S10.2 | Aprovar vaga | 2h |
| S10.3 | Rejeitar vaga | 0.5h |
| S10.4 | Detalhes vaga | 1.5h |
| S10.5 | Estatísticas | 2h |
| S10.6 | Gerenciar alias | 1.5h |
| S10.7 | Registrar tools | 1h |
| S10.8 | Funções SQL | 1h |
| S10.9 | Testes | 2h |

**Total:** 13h (~1.5 dias)

## Dependências

- E09 (Importação) - processo de importação
- Sistema de Slack existente (Sprint 9)

## Entregáveis

- 7 tools de Slack para gestão de grupos
- Fluxo de revisão manual
- Estatísticas de captura
- Gestão de aliases
