# E12: Group Entry Engine

**Sprint:** 25 (Foundation: S12.1-S12.5) + 26 (Discovery: S12.6)
**Prioridade:** Alta (causa raiz do ban)
**Dependencias:** E01 (Modelo Dados), E04 (Trust Score), E08 (Warming Scheduler)
**Pool alvo:** LISTENERS (não Julia)

---

## Contexto

O ban do dia 31/12/2025 foi causado por entrada agressiva em grupos:
- 124 grupos em 2 dias (26-27/12)
- Delay de apenas 10s entre entradas
- Sem integração com sistema de warming
- Reincidência após primeiro ban

**Este épico resolve o problema na raiz.**

### Separação de Pools

```
┌─────────────────────────────────────────────────────────────┐
│                    POOLS DE CHIPS                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   LISTENERS (tipo='listener')    │   JULIA (tipo='julia')   │
│   ─────────────────────────────  │   ─────────────────────   │
│   • Entram em grupos ✅          │   • NÃO entram em grupos  │
│   • Apenas recebem mensagens     │   • Conversam 1:1         │
│   • Coletam ofertas              │   • Prospecção/Follow-up  │
│   • E12 aplica-se aqui           │   • E12 NÃO se aplica     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

> **IMPORTANTE:** O Group Entry Engine usa apenas chips do tipo `listener`.
> Chips `julia` NUNCA entram em grupos.

---

## Objetivo

Criar sistema seguro de entrada em grupos que:
1. **Integra com Trust Score** - Entrada só quando chip está saudável
2. **Respeita fases de warmup** - Limites progressivos por fase
3. **Distribui entre N chips** - Não sobrecarrega um único chip
4. **Gerencia CSV/Excel de links** - Pipeline de importação e validação
5. **Anti-ban by design** - Delays humanizados, janelas temporais, circuit breaker

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GROUP ENTRY ENGINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      GROUP LINK MANAGER                                 │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │   Import    │  │  Validate   │  │  Enqueue    │  │   Status    │   │ │
│  │  │  CSV/Excel  │──│   Links     │──│   Links     │──│   Track     │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      ENTRY SCHEDULER                                    │ │
│  │                                                                         │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │   │ Fase Warmup    │ /dia │ /6h │ Delay min │ Janela horária        │ │ │
│  │   ├──────────────────────────────────────────────────────────────────┤ │ │
│  │   │ setup          │   0  │  0  │    -      │         -             │ │ │
│  │   │ primeiros      │   0  │  0  │    -      │         -             │ │ │
│  │   │ expansao       │   2  │  2  │  10 min   │   09h-18h             │ │ │
│  │   │ pre_operacao   │   5  │  3  │   5 min   │   08h-20h             │ │ │
│  │   │ operacao       │  10  │  5  │   3 min   │   08h-21h             │ │ │
│  │   └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │   ⚠️ Limite /6h evita "rajadas" (10 grupos em 30min é suspeito)         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      CHIP SELECTOR (Groups)                             │ │
│  │                                                                         │ │
│  │   Criterios de selecao:                                                │ │
│  │   0. tipo = 'listener' (NUNCA usa chips julia)                         │ │
│  │   1. Trust Score >= 70                                                 │ │
│  │   2. grupos_hoje < limite_dia AND grupos_6h < limite_6h                │ │
│  │   3. Menor quantidade de grupos total                                  │ │
│  │   4. Chip com menos falhas recentes                                    │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────────┐     │
│         │                            │                                │     │
│         ▼                            ▼                                ▼     │
│  ┌─────────────┐            ┌─────────────┐               ┌─────────────┐  │
│  │   CHIP 001  │            │   CHIP 002  │               │   CHIP 00N  │  │
│  │  grupos: 12 │            │  grupos: 8  │               │  grupos: 15 │  │
│  │  hoje: 1    │            │  hoje: 2    │               │  hoje: 0    │  │
│  └─────────────┘            └─────────────┘               └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Modelo de Dados

### Migration

```sql
-- =====================================================
-- LINKS DE GRUPOS (importados de CSV/Excel)
-- =====================================================
CREATE TABLE group_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacao
    invite_code TEXT UNIQUE NOT NULL,
    invite_url TEXT,
    nome TEXT,

    -- Categorizacao
    categoria TEXT,      -- 'medicos', 'saude', 'enfermagem', etc
    estado TEXT,         -- 'SP', 'RJ', etc
    regiao TEXT,         -- 'ABC', 'Capital', etc
    fonte TEXT,          -- Nome do arquivo CSV de origem

    -- Status
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN (
            'pendente',       -- Aguardando processamento
            'validado',       -- Link validado (grupo existe)
            'invalido',       -- Link inválido/expirado
            'agendado',       -- Na fila para entrada
            'em_progresso',   -- Tentando entrar
            'sucesso',        -- Entrou no grupo
            'aguardando',     -- Aguardando aprovação do admin
            'rejeitado',      -- Admin rejeitou
            'erro',           -- Erro na tentativa
            'desistido'       -- Muitas tentativas, desistiu
        )),

    -- Tentativas
    tentativas INT DEFAULT 0,
    max_tentativas INT DEFAULT 3,
    ultimo_erro TEXT,
    proxima_tentativa TIMESTAMPTZ,

    -- Resultado
    grupo_jid TEXT,           -- JID do grupo (após entrada)
    chip_id UUID REFERENCES chips(id),  -- Chip que entrou

    -- Auditoria
    validado_em TIMESTAMPTZ,
    agendado_em TIMESTAMPTZ,
    processado_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_group_links_status ON group_links(status);
CREATE INDEX idx_group_links_agendado ON group_links(proxima_tentativa)
    WHERE status IN ('agendado', 'erro');
CREATE INDEX idx_group_links_categoria ON group_links(categoria, estado);


-- =====================================================
-- FILA DE ENTRADA EM GRUPOS
-- =====================================================
CREATE TABLE group_entry_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    link_id UUID NOT NULL REFERENCES group_links(id) ON DELETE CASCADE,
    chip_id UUID REFERENCES chips(id),  -- Chip designado (pode ser NULL até alocação)

    -- Prioridade e agendamento
    prioridade INT DEFAULT 50,  -- 1-100 (maior = mais urgente)
    agendado_para TIMESTAMPTZ NOT NULL,

    -- Controle
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'processando', 'concluido', 'erro', 'cancelado')),

    -- Resultado
    resultado TEXT,
    erro TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    processado_em TIMESTAMPTZ
);

CREATE INDEX idx_group_entry_queue_pendente ON group_entry_queue(agendado_para)
    WHERE status = 'pendente';
CREATE INDEX idx_group_entry_queue_chip ON group_entry_queue(chip_id, status);


-- =====================================================
-- METRICAS DE ENTRADA POR CHIP/DIA
-- =====================================================
CREATE TABLE chip_group_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,
    data DATE NOT NULL,

    -- Contadores
    tentativas INT DEFAULT 0,
    sucessos INT DEFAULT 0,
    aguardando INT DEFAULT 0,
    erros INT DEFAULT 0,

    UNIQUE(chip_id, data)
);

CREATE INDEX idx_chip_group_metrics_data ON chip_group_metrics(chip_id, data DESC);


-- =====================================================
-- TELEMETRIA DE ENTRADA (detecção de anomalias)
-- =====================================================
CREATE TABLE group_entry_telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    latencia_segundos DECIMAL(6,2) NOT NULL,
    sucesso BOOLEAN NOT NULL,
    erro TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_group_entry_telemetry_chip ON group_entry_telemetry(chip_id, created_at DESC);
CREATE INDEX idx_group_entry_telemetry_latencia ON group_entry_telemetry(latencia_segundos DESC)
    WHERE latencia_segundos > 30;  -- Alertas de latência alta

COMMENT ON TABLE group_entry_telemetry IS 'Telemetria de entradas para detecção de anomalias';


-- =====================================================
-- ADICIONAR CAMPOS NA TABELA chips (E01)
-- =====================================================

-- CRÍTICO: Tipo de chip (julia vs listener)
ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    tipo TEXT DEFAULT 'julia' CHECK (tipo IN ('julia', 'listener'));

COMMENT ON COLUMN chips.tipo IS 'julia: conversa 1:1, listener: entra em grupos';

-- Contadores de grupos
ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    grupos_hoje INT DEFAULT 0;

ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    grupos_ultimas_6h INT DEFAULT 0;  -- NOVO: Evita rajadas

ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    limite_grupos_dia INT DEFAULT 0;  -- Calculado da fase

ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    ultimo_grupo_entrada TIMESTAMPTZ;

ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    grupos_falhas_consecutivas INT DEFAULT 0;

-- Circuit breaker
ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    circuit_breaker_ativo BOOLEAN DEFAULT false;

ALTER TABLE chips ADD COLUMN IF NOT EXISTS
    circuit_breaker_desde TIMESTAMPTZ;


-- =====================================================
-- CONFIG DE LIMITES POR FASE
-- =====================================================
CREATE TABLE group_entry_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Limites DIÁRIOS por fase
    limite_setup INT DEFAULT 0,
    limite_primeiros_contatos INT DEFAULT 0,
    limite_expansao INT DEFAULT 2,
    limite_pre_operacao INT DEFAULT 5,
    limite_operacao INT DEFAULT 10,

    -- Limites por JANELA DE 6H (evita rajadas)
    limite_6h_expansao INT DEFAULT 2,         -- = limite diário (não faz diferença)
    limite_6h_pre_operacao INT DEFAULT 3,     -- Max 3 a cada 6h
    limite_6h_operacao INT DEFAULT 5,         -- Max 5 a cada 6h (espalha ao longo do dia)

    -- Delays (segundos)
    delay_min_expansao INT DEFAULT 600,       -- 10 min
    delay_min_pre_operacao INT DEFAULT 300,   -- 5 min
    delay_min_operacao INT DEFAULT 180,       -- 3 min

    -- Janelas horárias (UTC)
    hora_inicio_expansao INT DEFAULT 12,      -- 09h BRT
    hora_fim_expansao INT DEFAULT 21,         -- 18h BRT
    hora_inicio_pre_op INT DEFAULT 11,        -- 08h BRT
    hora_fim_pre_op INT DEFAULT 23,           -- 20h BRT
    hora_inicio_op INT DEFAULT 11,            -- 08h BRT
    hora_fim_op INT DEFAULT 24,               -- 21h BRT

    -- Circuit breaker
    max_falhas_consecutivas INT DEFAULT 3,    -- Pausa chip após N falhas
    pausa_apos_falhas_minutos INT DEFAULT 60, -- Duração da pausa
    recovery_apos_horas INT DEFAULT 6,        -- Recovery automático após 6h

    -- Trust Score mínimo
    trust_minimo_grupos INT DEFAULT 70,

    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Config padrão
INSERT INTO group_entry_config DEFAULT VALUES;

-- NOTA: Estes valores default devem ser consistentes com LIMITES_GRUPOS_FASE
--       e DELAY_GRUPOS_FASE definidos em E08 (Warming Scheduler).
--       Ver: epic-08-warming-scheduler.md


-- =====================================================
-- JOBS: Reset de contadores
-- =====================================================

-- Reset diário (meia-noite)
CREATE OR REPLACE FUNCTION resetar_grupos_hoje()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE chips SET grupos_hoje = 0 WHERE tipo = 'listener';
END;
$$;

-- Reset a cada 6h (00h, 06h, 12h, 18h)
CREATE OR REPLACE FUNCTION resetar_grupos_6h()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE chips SET grupos_ultimas_6h = 0 WHERE tipo = 'listener';
END;
$$;

-- Recovery automático do circuit breaker
CREATE OR REPLACE FUNCTION recovery_circuit_breaker()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    config_recovery INT;
BEGIN
    -- Buscar tempo de recovery da config
    SELECT recovery_apos_horas INTO config_recovery
    FROM group_entry_config LIMIT 1;

    -- Resetar chips que passaram do tempo de recovery
    UPDATE chips
    SET
        circuit_breaker_ativo = false,
        grupos_falhas_consecutivas = 0,
        circuit_breaker_desde = NULL
    WHERE
        tipo = 'listener'
        AND circuit_breaker_ativo = true
        AND circuit_breaker_desde < (now() - (config_recovery || ' hours')::interval);
END;
$$;
```

---

## Implementação

### S12.1 - Importador de CSV/Excel

**Arquivo:** `app/services/groups/importer.py`

```python
"""
Importador de links de grupos de CSV/Excel.

Suporta:
- CSV com colunas: name, url, invite_code, state, category
- Excel (.xlsx) com mesma estrutura
"""
import csv
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from openpyxl import load_workbook
from pydantic import BaseModel

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class GroupLink(BaseModel):
    """Link de grupo para importação."""
    invite_code: str
    nome: Optional[str] = None
    invite_url: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[str] = None
    regiao: Optional[str] = None


def extrair_invite_code(url: str) -> Optional[str]:
    """
    Extrai invite code de uma URL de grupo.

    Formatos suportados:
    - https://chat.whatsapp.com/ABC123...
    - ABC123... (código direto)
    """
    if not url:
        return None

    url = url.strip()

    # Se for URL completa
    if "chat.whatsapp.com/" in url:
        parts = url.split("chat.whatsapp.com/")
        if len(parts) > 1:
            return parts[1].split("?")[0].strip()

    # Se for código direto (alfanumérico, ~22 chars)
    if len(url) >= 20 and url.isalnum():
        return url

    return None


def validar_formato_invite_code(invite_code: str) -> bool:
    """
    Valida formato do invite code ANTES de inserir no banco.
    Evita poluir DB com links obviamente inválidos.
    """
    if not invite_code:
        return False

    # Formato esperado: alfanumérico, 20-24 caracteres
    if not re.match(r'^[A-Za-z0-9_-]{20,24}$', invite_code):
        return False

    return True


async def verificar_duplicado(invite_code: str) -> bool:
    """
    Verifica se link já existe no banco.
    """
    result = supabase.table("group_links").select("id").eq(
        "invite_code", invite_code
    ).execute()

    return len(result.data) > 0 if result.data else False


async def _validar_link_antes_importar(invite_code: str) -> Tuple[bool, str]:
    """
    Validação completa ANTES de inserir no banco.

    Returns:
        (valido, motivo)
    """
    # 1. Formato válido?
    if not validar_formato_invite_code(invite_code):
        return False, "formato_invalido"

    # 2. Já existe no banco?
    if await verificar_duplicado(invite_code):
        return False, "duplicado"

    return True, "ok"


async def importar_csv(
    arquivo: Path,
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
) -> dict:
    """
    Importa links de um arquivo CSV.

    Args:
        arquivo: Caminho do arquivo CSV
        categoria: Categoria padrão (sobrescreve se não houver coluna)
        estado: Estado padrão

    Returns:
        {
            "total_linhas": N,
            "importados": N,
            "duplicados": N,
            "invalidos": N,
            "erros": [...]
        }
    """
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

    resultado = {
        "total_linhas": 0,
        "importados": 0,
        "duplicados": 0,
        "invalidos": 0,
        "erros": [],
    }

    links_para_inserir = []

    with open(arquivo, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, 1):
            resultado["total_linhas"] += 1

            # Extrair invite code
            invite_code = extrair_invite_code(
                row.get("invite_code") or row.get("url") or row.get("link", "")
            )

            if not invite_code:
                resultado["invalidos"] += 1
                resultado["erros"].append(f"Linha {i}: invite_code inválido")
                continue

            link = GroupLink(
                invite_code=invite_code,
                nome=row.get("name") or row.get("nome"),
                invite_url=row.get("url") or row.get("link"),
                categoria=row.get("category") or row.get("categoria") or categoria,
                estado=row.get("state") or row.get("estado") or estado,
                regiao=row.get("regiao") or row.get("region"),
            )

            links_para_inserir.append({
                "invite_code": link.invite_code,
                "invite_url": link.invite_url,
                "nome": link.nome,
                "categoria": link.categoria,
                "estado": link.estado,
                "regiao": link.regiao,
                "fonte": arquivo.name,
                "status": "pendente",
            })

    # Inserir em batch (ignorando duplicados)
    if links_para_inserir:
        try:
            result = supabase.table("group_links").upsert(
                links_para_inserir,
                on_conflict="invite_code",
                ignore_duplicates=True,
            ).execute()

            resultado["importados"] = len(result.data) if result.data else 0
            resultado["duplicados"] = len(links_para_inserir) - resultado["importados"]

        except Exception as e:
            logger.error(f"Erro ao inserir links: {e}")
            resultado["erros"].append(f"Erro no banco: {str(e)}")

    logger.info(
        f"[GroupImporter] {arquivo.name}: "
        f"{resultado['importados']} importados, "
        f"{resultado['duplicados']} duplicados, "
        f"{resultado['invalidos']} inválidos"
    )

    return resultado


async def importar_excel(
    arquivo: Path,
    sheet_name: Optional[str] = None,
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
) -> dict:
    """
    Importa links de um arquivo Excel (.xlsx).

    Espera colunas: name, url/invite_code, state, category
    """
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

    wb = load_workbook(arquivo, read_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    resultado = {
        "total_linhas": 0,
        "importados": 0,
        "duplicados": 0,
        "invalidos": 0,
        "erros": [],
    }

    links_para_inserir = []
    headers = None

    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        # Primeira linha = headers
        if i == 1:
            headers = [str(h).lower().strip() if h else "" for h in row]
            continue

        resultado["total_linhas"] += 1

        # Montar dict da linha
        row_dict = dict(zip(headers, row))

        # Extrair invite code
        invite_code = extrair_invite_code(
            str(row_dict.get("invite_code") or row_dict.get("url") or row_dict.get("link", ""))
        )

        if not invite_code:
            resultado["invalidos"] += 1
            continue

        links_para_inserir.append({
            "invite_code": invite_code,
            "invite_url": str(row_dict.get("url") or row_dict.get("link") or ""),
            "nome": str(row_dict.get("name") or row_dict.get("nome") or ""),
            "categoria": str(row_dict.get("category") or row_dict.get("categoria") or categoria or ""),
            "estado": str(row_dict.get("state") or row_dict.get("estado") or estado or ""),
            "regiao": str(row_dict.get("regiao") or row_dict.get("region") or ""),
            "fonte": arquivo.name,
            "status": "pendente",
        })

    wb.close()

    # Inserir em batch
    if links_para_inserir:
        try:
            result = supabase.table("group_links").upsert(
                links_para_inserir,
                on_conflict="invite_code",
                ignore_duplicates=True,
            ).execute()

            resultado["importados"] = len(result.data) if result.data else 0
            resultado["duplicados"] = len(links_para_inserir) - resultado["importados"]

        except Exception as e:
            logger.error(f"Erro ao inserir links: {e}")
            resultado["erros"].append(f"Erro no banco: {str(e)}")

    logger.info(
        f"[GroupImporter] {arquivo.name}: "
        f"{resultado['importados']} importados, "
        f"{resultado['duplicados']} duplicados, "
        f"{resultado['invalidos']} inválidos"
    )

    return resultado


async def importar_diretorio(diretorio: Path) -> dict:
    """
    Importa todos os CSVs e Excel de um diretório.
    """
    resultado_total = {
        "arquivos_processados": 0,
        "total_importados": 0,
        "total_duplicados": 0,
        "total_invalidos": 0,
        "detalhes": [],
    }

    for arquivo in diretorio.glob("*.csv"):
        resultado = await importar_csv(arquivo)
        resultado_total["arquivos_processados"] += 1
        resultado_total["total_importados"] += resultado["importados"]
        resultado_total["total_duplicados"] += resultado["duplicados"]
        resultado_total["total_invalidos"] += resultado["invalidos"]
        resultado_total["detalhes"].append({
            "arquivo": arquivo.name,
            **resultado
        })

    for arquivo in diretorio.glob("*.xlsx"):
        resultado = await importar_excel(arquivo)
        resultado_total["arquivos_processados"] += 1
        resultado_total["total_importados"] += resultado["importados"]
        resultado_total["total_duplicados"] += resultado["duplicados"]
        resultado_total["total_invalidos"] += resultado["invalidos"]
        resultado_total["detalhes"].append({
            "arquivo": arquivo.name,
            **resultado
        })

    return resultado_total
```

---

### S12.2 - Validador de Links

**Arquivo:** `app/services/groups/validator.py`

```python
"""
Validador de links de grupos.

Verifica se o link é válido antes de tentar entrar.
"""
import logging
from typing import Optional, List
from datetime import datetime, UTC

from app.services.supabase import supabase
from app.services.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)


async def validar_link(
    invite_code: str,
    chip_id: Optional[str] = None,
) -> dict:
    """
    Valida se um link de grupo é válido.

    Args:
        invite_code: Código de convite
        chip_id: ID do chip a usar (opcional, usa qualquer ativo)

    Returns:
        {
            "valido": bool,
            "grupo_nome": str,
            "grupo_tamanho": int,
            "erro": str (se inválido)
        }
    """
    # Buscar chip para validação
    if chip_id:
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        chip = result.data
    else:
        # Usar qualquer chip ativo
        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).limit(1).execute()
        chip = result.data[0] if result.data else None

    if not chip:
        return {"valido": False, "erro": "Nenhum chip disponível para validação"}

    # Buscar info do grupo via Evolution API
    client = WhatsAppClient(instance=chip["instance_name"])

    try:
        info = await client.buscar_info_grupo(invite_code)

        if info:
            return {
                "valido": True,
                "grupo_nome": info.get("subject", ""),
                "grupo_tamanho": info.get("size", 0),
                "grupo_descricao": info.get("desc", ""),
            }
        else:
            return {"valido": False, "erro": "Link inválido ou expirado"}

    except Exception as e:
        return {"valido": False, "erro": str(e)}


async def validar_links_pendentes(limite: int = 50) -> dict:
    """
    Valida batch de links pendentes.

    Returns:
        {
            "validados": N,
            "invalidos": N,
            "erros": N
        }
    """
    # Buscar links pendentes
    result = supabase.table("group_links").select("*").eq(
        "status", "pendente"
    ).limit(limite).execute()

    links = result.data or []

    stats = {"validados": 0, "invalidos": 0, "erros": 0}

    for link in links:
        try:
            validacao = await validar_link(link["invite_code"])

            if validacao["valido"]:
                supabase.table("group_links").update({
                    "status": "validado",
                    "nome": validacao.get("grupo_nome") or link["nome"],
                    "validado_em": datetime.now(UTC).isoformat(),
                }).eq("id", link["id"]).execute()
                stats["validados"] += 1
            else:
                supabase.table("group_links").update({
                    "status": "invalido",
                    "ultimo_erro": validacao.get("erro"),
                }).eq("id", link["id"]).execute()
                stats["invalidos"] += 1

        except Exception as e:
            logger.error(f"Erro ao validar {link['invite_code']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"[GroupValidator] Validação: "
        f"{stats['validados']} válidos, "
        f"{stats['invalidos']} inválidos, "
        f"{stats['erros']} erros"
    )

    return stats
```

---

### S12.3 - Scheduler de Entrada

**Arquivo:** `app/services/groups/entry_scheduler.py`

```python
"""
Scheduler de entrada em grupos.

Agenda entradas respeitando:
- Fase de warmup do chip
- Limites diários
- Janelas horárias
- Delays mínimos
"""
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict
import random

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# Mapeamento fase -> campo de limite
LIMITE_POR_FASE = {
    "setup": "limite_setup",
    "primeiros_contatos": "limite_primeiros_contatos",
    "expansao": "limite_expansao",
    "pre_operacao": "limite_pre_operacao",
    "operacao": "limite_operacao",
}

DELAY_POR_FASE = {
    "expansao": "delay_min_expansao",
    "pre_operacao": "delay_min_pre_operacao",
    "operacao": "delay_min_operacao",
}

JANELA_POR_FASE = {
    "expansao": ("hora_inicio_expansao", "hora_fim_expansao"),
    "pre_operacao": ("hora_inicio_pre_op", "hora_fim_pre_op"),
    "operacao": ("hora_inicio_op", "hora_fim_op"),
}


class GroupEntryScheduler:
    """Scheduler de entrada em grupos."""

    def __init__(self):
        self.config: Optional[Dict] = None

    async def carregar_config(self) -> Dict:
        """Carrega configuração de limites."""
        result = supabase.table("group_entry_config").select("*").single().execute()
        self.config = result.data
        return self.config

    def obter_limite_fase(self, fase: str) -> int:
        """Retorna limite diário para uma fase."""
        campo = LIMITE_POR_FASE.get(fase)
        if not campo or not self.config:
            return 0
        return self.config.get(campo, 0)

    def obter_delay_fase(self, fase: str) -> int:
        """Retorna delay mínimo (segundos) para uma fase."""
        campo = DELAY_POR_FASE.get(fase)
        if not campo or not self.config:
            return 600  # Default 10 min
        return self.config.get(campo, 600)

    def obter_janela_fase(self, fase: str) -> tuple:
        """Retorna janela horária (hora_inicio, hora_fim) UTC."""
        campos = JANELA_POR_FASE.get(fase)
        if not campos or not self.config:
            return (12, 21)  # Default 09h-18h BRT
        return (
            self.config.get(campos[0], 12),
            self.config.get(campos[1], 21),
        )

    async def selecionar_chip_para_grupo(self) -> Optional[Dict]:
        """
        Seleciona melhor chip para entrada em grupo.

        Critérios:
        1. Trust Score >= trust_minimo_grupos
        2. Fase permite entrada em grupos
        3. grupos_hoje < limite da fase
        4. Sem muitas falhas consecutivas
        5. Menor quantidade de grupos (balanceamento)
        """
        if not self.config:
            await self.carregar_config()

        trust_min = self.config.get("trust_minimo_grupos", 70)
        max_falhas = self.config.get("max_falhas_consecutivas", 3)

        # Buscar chips elegíveis
        result = supabase.table("chips").select("*").in_(
            "status", ["active", "warming"]
        ).gte(
            "trust_score", trust_min
        ).lt(
            "grupos_falhas_consecutivas", max_falhas
        ).in_(
            "fase_warmup", ["expansao", "pre_operacao", "operacao"]
        ).order(
            "grupos_count"  # Menor primeiro (balanceamento)
        ).execute()

        chips = result.data or []

        # Filtrar por limite diário
        for chip in chips:
            fase = chip["fase_warmup"]
            limite = self.obter_limite_fase(fase)

            if chip["grupos_hoje"] < limite:
                return chip

        return None

    async def agendar_proxima_entrada(
        self,
        link_id: str,
        chip_id: Optional[str] = None,
        prioridade: int = 50,
    ) -> Optional[Dict]:
        """
        Agenda próxima entrada em grupo.

        Args:
            link_id: ID do link de grupo
            chip_id: ID do chip (opcional, será selecionado)
            prioridade: 1-100 (maior = mais urgente)

        Returns:
            Item da fila criado ou None
        """
        if not self.config:
            await self.carregar_config()

        # Selecionar chip se não fornecido
        if not chip_id:
            chip = await self.selecionar_chip_para_grupo()
            if not chip:
                logger.warning("[GroupScheduler] Nenhum chip disponível para grupos")
                return None
            chip_id = chip["id"]
        else:
            result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()
            chip = result.data

        if not chip:
            return None

        # Calcular próximo horário
        agora = datetime.now(UTC)
        fase = chip["fase_warmup"]

        # Verificar janela horária
        hora_inicio, hora_fim = self.obter_janela_fase(fase)
        hora_atual = agora.hour

        if hora_atual < hora_inicio:
            # Antes da janela - agendar para início
            proximo = agora.replace(hour=hora_inicio, minute=random.randint(0, 30))
        elif hora_atual >= hora_fim:
            # Depois da janela - agendar para amanhã
            proximo = (agora + timedelta(days=1)).replace(hour=hora_inicio, minute=random.randint(0, 30))
        else:
            # Dentro da janela
            delay = self.obter_delay_fase(fase)

            # Verificar última entrada do chip
            if chip.get("ultimo_grupo_entrada"):
                ultima = datetime.fromisoformat(chip["ultimo_grupo_entrada"].replace("Z", "+00:00"))
                tempo_desde_ultima = (agora - ultima).total_seconds()

                if tempo_desde_ultima < delay:
                    # Ainda dentro do delay
                    proximo = ultima + timedelta(seconds=delay + random.randint(30, 120))
                else:
                    # Pode entrar agora (com pequeno delay aleatório)
                    proximo = agora + timedelta(seconds=random.randint(30, 120))
            else:
                proximo = agora + timedelta(seconds=random.randint(30, 120))

        # Criar item na fila
        result = supabase.table("group_entry_queue").insert({
            "link_id": link_id,
            "chip_id": chip_id,
            "prioridade": prioridade,
            "agendado_para": proximo.isoformat(),
            "status": "pendente",
        }).execute()

        # Atualizar status do link
        supabase.table("group_links").update({
            "status": "agendado",
            "agendado_em": agora.isoformat(),
        }).eq("id", link_id).execute()

        logger.info(
            f"[GroupScheduler] Link {link_id} agendado para "
            f"{proximo.strftime('%H:%M')} no chip {chip['telefone']}"
        )

        return result.data[0] if result.data else None

    async def agendar_batch_validados(self, limite: int = 20) -> int:
        """
        Agenda batch de links validados.

        Returns:
            Quantidade agendada
        """
        # Buscar links validados não agendados
        result = supabase.table("group_links").select("*").eq(
            "status", "validado"
        ).limit(limite).execute()

        links = result.data or []
        agendados = 0

        for link in links:
            item = await self.agendar_proxima_entrada(link["id"])
            if item:
                agendados += 1

        logger.info(f"[GroupScheduler] {agendados}/{len(links)} links agendados")

        return agendados


# Singleton
group_entry_scheduler = GroupEntryScheduler()
```

---

### S12.4 - Worker de Entrada

**Arquivo:** `app/services/groups/entry_worker.py`

```python
"""
Worker que processa a fila de entrada em grupos.

Características:
- Processa um item por vez
- Respeita agendamento
- Atualiza Trust Score em caso de erro
- Circuit breaker por chip
"""
import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from app.services.supabase import supabase
from app.services.whatsapp import WhatsAppClient
from app.services.notificacoes import notificar_slack
from app.services.groups.entry_scheduler import group_entry_scheduler

logger = logging.getLogger(__name__)


class GroupEntryWorker:
    """Worker de processamento de entrada em grupos."""

    def __init__(self):
        self._running = False
        self.config: Optional[dict] = None

    async def carregar_config(self):
        """Carrega configuração."""
        result = supabase.table("group_entry_config").select("*").single().execute()
        self.config = result.data

    async def processar_proximo(self) -> bool:
        """
        Processa próximo item da fila.

        Returns:
            True se processou algo, False se fila vazia
        """
        agora = datetime.now(UTC)

        # Buscar próximo item pronto
        result = supabase.table("group_entry_queue").select(
            "*, group_links(*), chips(*)"
        ).eq(
            "status", "pendente"
        ).lte(
            "agendado_para", agora.isoformat()
        ).order(
            "prioridade", desc=True
        ).order(
            "agendado_para"
        ).limit(1).execute()

        if not result.data:
            return False

        item = result.data[0]
        link = item["group_links"]
        chip = item["chips"]

        # Marcar como processando
        supabase.table("group_entry_queue").update({
            "status": "processando",
        }).eq("id", item["id"]).execute()

        supabase.table("group_links").update({
            "status": "em_progresso",
        }).eq("id", link["id"]).execute()

        logger.info(
            f"[GroupWorker] Entrando em '{link['nome']}' via chip {chip['telefone']}"
        )

        # TELEMETRIA: Início da operação
        inicio = time.time()
        client = WhatsAppClient(instance=chip["instance_name"])

        try:
            sucesso, mensagem = await client.entrar_grupo(link["invite_code"])
            latencia = time.time() - inicio

            # Registrar telemetria
            await self._registrar_telemetria(
                chip_id=chip["id"],
                latencia=latencia,
                sucesso=sucesso,
                erro=None if sucesso else mensagem,
            )

            if sucesso:
                await self._registrar_sucesso(item, link, chip, mensagem)
            elif "aguardando" in mensagem.lower() or "pending" in mensagem.lower():
                await self._registrar_aguardando(item, link, chip)
            else:
                await self._registrar_erro(item, link, chip, mensagem)

        except Exception as e:
            latencia = time.time() - inicio
            logger.error(f"[GroupWorker] Erro ao entrar em grupo: {e}")

            # Registrar telemetria de erro
            await self._registrar_telemetria(
                chip_id=chip["id"],
                latencia=latencia,
                sucesso=False,
                erro=str(e),
            )

            await self._registrar_erro(item, link, chip, str(e))

        # Alerta se latência muito alta
        if latencia > 30:
            logger.warning(
                f"[GroupWorker] ⚠️ Latência alta: {latencia:.1f}s (chip {chip['telefone']})"
            )

        return True

    async def _registrar_telemetria(
        self,
        chip_id: str,
        latencia: float,
        sucesso: bool,
        erro: Optional[str] = None,
    ):
        """Registra telemetria de entrada para detecção de anomalias."""
        supabase.table("group_entry_telemetry").insert({
            "chip_id": chip_id,
            "latencia_segundos": round(latencia, 2),
            "sucesso": sucesso,
            "erro": erro[:500] if erro else None,
        }).execute()

    async def _registrar_sucesso(self, item: dict, link: dict, chip: dict, mensagem: str):
        """Registra entrada com sucesso."""
        agora = datetime.now(UTC)

        # Atualizar link
        supabase.table("group_links").update({
            "status": "sucesso",
            "chip_id": chip["id"],
            "processado_em": agora.isoformat(),
        }).eq("id", link["id"]).execute()

        # Atualizar fila
        supabase.table("group_entry_queue").update({
            "status": "concluido",
            "resultado": "sucesso",
            "processado_em": agora.isoformat(),
        }).eq("id", item["id"]).execute()

        # Atualizar chip
        supabase.table("chips").update({
            "grupos_count": chip["grupos_count"] + 1,
            "grupos_hoje": chip["grupos_hoje"] + 1,
            "ultimo_grupo_entrada": agora.isoformat(),
            "grupos_falhas_consecutivas": 0,  # Reset falhas
        }).eq("id", chip["id"]).execute()

        # Atualizar métricas diárias
        hoje = agora.date().isoformat()
        supabase.table("chip_group_metrics").upsert({
            "chip_id": chip["id"],
            "data": hoje,
            "tentativas": 1,
            "sucessos": 1,
        }, on_conflict="chip_id,data").execute()

        logger.info(f"[GroupWorker] ✅ Entrou em '{link['nome']}'")

    async def _registrar_aguardando(self, item: dict, link: dict, chip: dict):
        """Registra entrada aguardando aprovação."""
        agora = datetime.now(UTC)

        # Atualizar link
        supabase.table("group_links").update({
            "status": "aguardando",
            "chip_id": chip["id"],
            "processado_em": agora.isoformat(),
        }).eq("id", link["id"]).execute()

        # Atualizar fila
        supabase.table("group_entry_queue").update({
            "status": "concluido",
            "resultado": "aguardando_aprovacao",
            "processado_em": agora.isoformat(),
        }).eq("id", item["id"]).execute()

        # Atualizar chip (conta como tentativa, mas não como grupo)
        supabase.table("chips").update({
            "ultimo_grupo_entrada": agora.isoformat(),
        }).eq("id", chip["id"]).execute()

        # Atualizar métricas diárias
        hoje = agora.date().isoformat()
        supabase.table("chip_group_metrics").upsert({
            "chip_id": chip["id"],
            "data": hoje,
            "tentativas": 1,
            "aguardando": 1,
        }, on_conflict="chip_id,data").execute()

        logger.info(f"[GroupWorker] ⏳ Aguardando aprovação para '{link['nome']}'")

    async def _registrar_erro(self, item: dict, link: dict, chip: dict, erro: str):
        """Registra erro na entrada."""
        agora = datetime.now(UTC)
        tentativas = link["tentativas"] + 1
        max_tentativas = link["max_tentativas"]

        # Verificar se deve desistir
        if tentativas >= max_tentativas:
            status_link = "desistido"
            status_fila = "erro"
            logger.warning(f"[GroupWorker] ❌ Desistindo de '{link['nome']}' após {tentativas} tentativas")
        else:
            status_link = "erro"
            status_fila = "erro"
            logger.warning(f"[GroupWorker] ⚠️ Erro em '{link['nome']}': {erro}")

        # Atualizar link
        supabase.table("group_links").update({
            "status": status_link,
            "tentativas": tentativas,
            "ultimo_erro": erro[:500],
            "proxima_tentativa": (agora + timedelta(hours=1)).isoformat() if tentativas < max_tentativas else None,
        }).eq("id", link["id"]).execute()

        # Atualizar fila
        supabase.table("group_entry_queue").update({
            "status": status_fila,
            "erro": erro[:500],
            "processado_em": agora.isoformat(),
        }).eq("id", item["id"]).execute()

        # Atualizar chip (incrementar falhas consecutivas)
        falhas = chip["grupos_falhas_consecutivas"] + 1
        max_falhas = self.config.get("max_falhas_consecutivas", 3) if self.config else 3

        updates = {
            "grupos_falhas_consecutivas": falhas,
            "ultimo_grupo_entrada": agora.isoformat(),
        }

        # Circuit breaker: pausar chip se muitas falhas
        if falhas >= max_falhas:
            pausa_min = self.config.get("pausa_apos_falhas_minutos", 60) if self.config else 60
            logger.warning(
                f"[GroupWorker] 🚨 Circuit breaker: chip {chip['telefone']} "
                f"pausado por {pausa_min} min após {falhas} falhas"
            )

            await notificar_slack(
                f":warning: *Circuit Breaker Grupos*\n"
                f"Chip `{chip['telefone']}` pausado para entrada em grupos "
                f"após {falhas} falhas consecutivas.\n"
                f"Último erro: {erro[:100]}",
                canal="alertas"
            )

        supabase.table("chips").update(updates).eq("id", chip["id"]).execute()

        # Atualizar métricas diárias
        hoje = agora.date().isoformat()
        supabase.table("chip_group_metrics").upsert({
            "chip_id": chip["id"],
            "data": hoje,
            "tentativas": 1,
            "erros": 1,
        }, on_conflict="chip_id,data").execute()

    async def executar_ciclo(self):
        """Executa um ciclo de processamento."""
        if not self.config:
            await self.carregar_config()

        processado = await self.processar_proximo()

        if processado:
            logger.debug("[GroupWorker] Item processado")

        return processado

    async def iniciar(self, intervalo_segundos: int = 30):
        """
        Inicia loop do worker.

        Args:
            intervalo_segundos: Intervalo entre verificações quando fila vazia
        """
        self._running = True
        logger.info("[GroupWorker] Iniciando...")

        while self._running:
            try:
                processado = await self.executar_ciclo()

                # Se não processou nada, aguardar mais
                if not processado:
                    await asyncio.sleep(intervalo_segundos)
                else:
                    # Pequeno delay entre processamentos
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"[GroupWorker] Erro no ciclo: {e}")
                await asyncio.sleep(60)

    def parar(self):
        """Para o worker."""
        self._running = False
        logger.info("[GroupWorker] Parando...")


# Singleton
group_entry_worker = GroupEntryWorker()
```

---

### S12.5 - API de Gerenciamento

**Arquivo:** `app/api/routes/groups.py`

```python
"""
API de gerenciamento de entrada em grupos.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from typing import Optional
import tempfile

from app.services.groups.importer import importar_csv, importar_excel, importar_diretorio
from app.services.groups.validator import validar_links_pendentes
from app.services.groups.entry_scheduler import group_entry_scheduler
from app.services.supabase import supabase

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("/import/csv")
async def upload_csv(file: UploadFile = File(...)):
    """Importa CSV de links de grupos."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Arquivo deve ser CSV")

    # Salvar temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        resultado = await importar_csv(tmp_path)
        return resultado
    finally:
        tmp_path.unlink()


@router.post("/import/excel")
async def upload_excel(file: UploadFile = File(...)):
    """Importa Excel de links de grupos."""
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Arquivo deve ser .xlsx")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        resultado = await importar_excel(tmp_path)
        return resultado
    finally:
        tmp_path.unlink()


@router.post("/validate")
async def validar_pendentes(limite: int = 50):
    """Valida batch de links pendentes."""
    return await validar_links_pendentes(limite)


@router.post("/schedule")
async def agendar_validados(limite: int = 20):
    """Agenda batch de links validados."""
    agendados = await group_entry_scheduler.agendar_batch_validados(limite)
    return {"agendados": agendados}


@router.get("/status")
async def status_grupos():
    """Retorna status geral de links e fila."""
    # Contar por status
    links_result = supabase.rpc("contar_group_links_por_status").execute()
    fila_result = supabase.rpc("contar_group_queue_por_status").execute()

    return {
        "links": links_result.data,
        "fila": fila_result.data,
    }


@router.get("/links")
async def listar_links(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    limite: int = 100,
):
    """Lista links de grupos."""
    query = supabase.table("group_links").select("*")

    if status:
        query = query.eq("status", status)
    if categoria:
        query = query.eq("categoria", categoria)

    result = query.limit(limite).execute()
    return result.data


@router.get("/queue")
async def listar_fila(
    status: str = "pendente",
    limite: int = 50,
):
    """Lista fila de entrada."""
    result = supabase.table("group_entry_queue").select(
        "*, group_links(nome, invite_code), chips(telefone)"
    ).eq(
        "status", status
    ).order(
        "agendado_para"
    ).limit(limite).execute()

    return result.data


@router.delete("/links/{link_id}")
async def remover_link(link_id: str):
    """Remove link e cancela agendamento."""
    # Cancelar da fila
    supabase.table("group_entry_queue").update({
        "status": "cancelado"
    }).eq("link_id", link_id).eq("status", "pendente").execute()

    # Remover link
    supabase.table("group_links").delete().eq("id", link_id).execute()

    return {"status": "removido"}


@router.get("/metrics")
async def metricas_entrada():
    """Métricas de entrada em grupos."""
    result = supabase.rpc("metricas_entrada_grupos").execute()
    return result.data
```

---

## Jobs do Scheduler

Adicionar ao `app/workers/scheduler.py`:

```python
# ============================================================
# JOBS DE ENTRADA EM GRUPOS
# ============================================================

@scheduler.scheduled_job("cron", hour=8, minute=0)  # 05h BRT
async def validar_links_grupos():
    """Valida links pendentes diariamente."""
    await validar_links_pendentes(limite=100)

@scheduler.scheduled_job("interval", minutes=15)
async def agendar_grupos_validados():
    """Agenda links validados a cada 15 min."""
    await group_entry_scheduler.agendar_batch_validados(limite=10)

@scheduler.scheduled_job("cron", hour=3, minute=0)  # 00h BRT
async def resetar_grupos_diarios():
    """Reset contadores diários de grupos."""
    supabase.rpc("resetar_grupos_hoje").execute()

# Worker roda separado (não é cron, é loop contínuo)
```

---

## DoD (Definition of Done)

- [ ] Migration aplicada (todas as tabelas)
- [ ] Importador CSV funcionando
- [ ] Importador Excel funcionando
- [ ] Validador de links funcionando
- [ ] Scheduler respeitando fases de warmup
- [ ] Scheduler respeitando janelas horárias
- [ ] Scheduler respeitando delays mínimos
- [ ] Worker processando fila
- [ ] Circuit breaker funcionando
- [ ] API de gerenciamento funcionando
- [ ] Jobs do scheduler configurados
- [ ] Métricas sendo registradas
- [ ] Notificações Slack funcionando
- [ ] Testes unitários
- [ ] Testes de integração

---

## Limites Recomendados (Revisados)

Com base no incidente do ban:

| Fase | Limite/dia | Delay mínimo | Janela |
|------|-----------|--------------|--------|
| setup | 0 | - | - |
| primeiros_contatos | 0 | - | - |
| expansao | 2 | 10 min | 09h-18h |
| pre_operacao | 5 | 5 min | 08h-20h |
| operacao | 10 | 3 min | 08h-21h |

**Total máximo por chip em operação: 10 grupos/dia**

Com 5 chips em produção = 50 grupos/dia (máximo seguro)

---

## Migração do Script Atual

O script `scripts/join_groups.py` deve ser **descontinuado** após implementação deste épico.

Para migrar dados existentes:

```python
# Migrar join_log.json para group_links
async def migrar_log_antigo():
    log_file = Path("data/grupos_zap/join_log.json")
    with open(log_file) as f:
        log = json.load(f)

    for invite_code, info in log.get("entradas", {}).items():
        status = "sucesso" if info.get("sucesso") else "erro"
        if "aguardando" in info.get("mensagem", "").lower():
            status = "aguardando"

        supabase.table("group_links").upsert({
            "invite_code": invite_code,
            "nome": info.get("nome"),
            "status": status,
            "ultimo_erro": info.get("mensagem") if not info.get("sucesso") else None,
            "processado_em": info.get("data"),
            "fonte": "migrado_join_log",
        }, on_conflict="invite_code").execute()
```

---

---

## S12.6 - Crawler & Source Discovery

### Contexto

Os CSVs atuais vêm de web scraping de sites agregadores:
- escaladeplantao.com.br (49 grupos)
- gruposmedicos.com.br (214 grupos)
- queroplantao.com.br (falhou)
- searchplantao.com.br (falhou)
- plantoesmedicosbrasil.com.br (falhou)

**Problema:** Esses sites têm atualizações pouco frequentes e são fonte finita.

**Solução:** Crawler periódico + descoberta ativa de novas fontes.

---

### Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SOURCE DISCOVERY ENGINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     DESCOBERTA DE FONTES                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │   Google    │  │   Bing      │  │  Social     │  │   Link      │   │ │
│  │  │   Search    │  │   Search    │  │  Listening  │  │   Follower  │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  │        │                │                │                │           │ │
│  │        └────────────────┴────────────────┴────────────────┘           │ │
│  │                                  │                                     │ │
│  │                                  ▼                                     │ │
│  │                    ┌─────────────────────────┐                        │ │
│  │                    │    FONTE CANDIDATA      │                        │ │
│  │                    │  (URL + score + tipo)   │                        │ │
│  │                    └─────────────────────────┘                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      CRAWLER ADAPTATIVO                                │ │
│  │                                                                         │ │
│  │   Fonte conhecida?                                                     │ │
│  │   ├─ SIM → Usa parser específico                                      │ │
│  │   └─ NÃO → Usa parser genérico (busca chat.whatsapp.com/*)            │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      PIPELINE DE IMPORTAÇÃO                            │ │
│  │                                                                         │ │
│  │   Links extraídos → Deduplicação → Validação → Fila de entrada        │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Modelo de Dados Adicional

```sql
-- =====================================================
-- FONTES DE GRUPOS (sites agregadores)
-- =====================================================
CREATE TABLE group_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificação
    url TEXT UNIQUE NOT NULL,
    nome TEXT,
    dominio TEXT NOT NULL,  -- ex: escaladeplantao.com.br

    -- Tipo e método
    tipo TEXT NOT NULL DEFAULT 'agregador'
        CHECK (tipo IN (
            'agregador',      -- Site que lista grupos
            'diretorio',      -- Diretório tipo lista.me
            'rede_social',    -- Twitter, LinkedIn, Facebook
            'telegram',       -- Canal/grupo Telegram com links
            'forum',          -- Fórum médico
            'blog',           -- Blog com posts de grupos
            'outro'
        )),

    metodo_crawl TEXT NOT NULL DEFAULT 'requests'
        CHECK (metodo_crawl IN ('requests', 'playwright', 'api')),

    -- Parser
    parser_config JSONB DEFAULT '{}',  -- Seletores CSS, XPath, etc

    -- Status
    status TEXT NOT NULL DEFAULT 'ativo'
        CHECK (status IN ('ativo', 'inativo', 'erro', 'bloqueado')),

    -- Métricas
    total_grupos_extraidos INT DEFAULT 0,
    grupos_validos INT DEFAULT 0,
    taxa_sucesso DECIMAL(5,4) DEFAULT 0,

    -- Controle de crawl
    ultimo_crawl TIMESTAMPTZ,
    proximo_crawl TIMESTAMPTZ,
    frequencia_dias INT DEFAULT 7,  -- Crawl semanal por padrão
    falhas_consecutivas INT DEFAULT 0,

    -- Descoberta
    descoberto_via TEXT,  -- 'manual', 'google', 'bing', 'link_follower'
    descoberto_em TIMESTAMPTZ DEFAULT now(),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_group_sources_proximo ON group_sources(proximo_crawl)
    WHERE status = 'ativo';
CREATE INDEX idx_group_sources_dominio ON group_sources(dominio);


-- =====================================================
-- HISTÓRICO DE CRAWLS
-- =====================================================
CREATE TABLE crawl_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES group_sources(id) ON DELETE CASCADE,

    -- Resultado
    status TEXT NOT NULL CHECK (status IN ('sucesso', 'parcial', 'erro')),
    duracao_segundos INT,

    -- Métricas
    links_encontrados INT DEFAULT 0,
    links_novos INT DEFAULT 0,
    links_duplicados INT DEFAULT 0,
    links_invalidos INT DEFAULT 0,

    -- Erro (se houver)
    erro TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_crawl_history_source ON crawl_history(source_id, created_at DESC);


-- =====================================================
-- QUERIES DE DESCOBERTA (para buscar novas fontes)
-- =====================================================
CREATE TABLE discovery_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Query
    query TEXT NOT NULL,
    engine TEXT NOT NULL DEFAULT 'google'
        CHECK (engine IN ('google', 'bing', 'duckduckgo')),

    -- Controle
    ativo BOOLEAN DEFAULT true,
    ultimo_run TIMESTAMPTZ,
    proximo_run TIMESTAMPTZ,
    frequencia_dias INT DEFAULT 14,  -- Quinzenal

    -- Métricas
    fontes_descobertas INT DEFAULT 0,
    fontes_validas INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Queries iniciais
INSERT INTO discovery_queries (query, engine) VALUES
    ('grupos whatsapp plantão médico', 'google'),
    ('grupos whatsapp vagas médicas', 'google'),
    ('whatsapp groups medical shifts brazil', 'google'),
    ('site:chat.whatsapp.com plantão', 'google'),
    ('grupos telegram plantão médico', 'google'),
    ('agregador grupos médicos whatsapp', 'bing'),
    ('lista grupos whatsapp médicos', 'bing'),
    ('diretório grupos whatsapp saúde', 'duckduckgo');
```

---

### Implementação

#### S12.6.1 - Source Discovery

**Arquivo:** `app/services/groups/discovery.py`

```python
"""
Source Discovery - Descoberta ativa de novas fontes de grupos.

Estratégias:
1. Google/Bing Search - Busca por termos relacionados
2. Link Follower - Segue links de sites conhecidos
3. Social Listening - Monitora menções em redes sociais
"""
import logging
import re
from typing import List, Optional, Dict
from datetime import datetime, timedelta, UTC
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class SourceDiscovery:
    """Descoberta de novas fontes de grupos."""

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Domínios a ignorar (já são fontes ou não relevantes)
        self.dominios_ignorados = {
            "chat.whatsapp.com",
            "wa.me",
            "t.me",
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "x.com",
            "youtube.com",
            "google.com",
            "bing.com",
        }

        # Indicadores de que é um site de grupos médicos
        self.indicadores_positivos = [
            "plantão", "plantao", "vagas médicas", "vagas medicas",
            "escala médica", "escala medica", "grupos médicos",
            "grupos medicos", "whatsapp médico", "whatsapp medico",
            "grupos whatsapp", "saúde", "saude", "hospital",
        ]

    async def buscar_google(self, query: str, num_results: int = 20) -> List[str]:
        """
        Busca no Google por sites relevantes.

        Usa scraping do Google (respeitar rate limits!).
        Alternativa: usar Google Custom Search API.
        """
        urls_encontradas = []

        # URL do Google
        search_url = "https://www.google.com/search"
        params = {
            "q": query,
            "num": num_results,
            "hl": "pt-BR",
            "gl": "BR",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    search_url,
                    params=params,
                    headers={"User-Agent": self.user_agent},
                    timeout=30,
                    follow_redirects=True,
                )

                soup = BeautifulSoup(resp.text, "html.parser")

                # Extrai links dos resultados
                for link in soup.find_all("a", href=True):
                    href = link["href"]

                    # Google encapsula URLs em /url?q=...
                    if href.startswith("/url?q="):
                        url = href.split("/url?q=")[1].split("&")[0]
                        urls_encontradas.append(url)
                    elif href.startswith("http") and "google" not in href:
                        urls_encontradas.append(href)

            except Exception as e:
                logger.error(f"[Discovery] Erro no Google: {e}")

        return urls_encontradas

    async def buscar_bing(self, query: str, num_results: int = 20) -> List[str]:
        """Busca no Bing por sites relevantes."""
        urls_encontradas = []

        search_url = "https://www.bing.com/search"
        params = {
            "q": query,
            "count": num_results,
            "setlang": "pt-BR",
            "cc": "BR",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    search_url,
                    params=params,
                    headers={"User-Agent": self.user_agent},
                    timeout=30,
                )

                soup = BeautifulSoup(resp.text, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("http") and "bing" not in href and "microsoft" not in href:
                        urls_encontradas.append(href)

            except Exception as e:
                logger.error(f"[Discovery] Erro no Bing: {e}")

        return urls_encontradas

    def extrair_dominio(self, url: str) -> Optional[str]:
        """Extrai domínio de uma URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower().replace("www.", "")
        except:
            return None

    def pontuar_url(self, url: str, html: str = "") -> int:
        """
        Pontua relevância de uma URL para grupos médicos.

        Returns:
            Score 0-100
        """
        score = 0
        url_lower = url.lower()
        html_lower = html.lower() if html else ""

        # Pontos por URL
        for indicador in self.indicadores_positivos:
            if indicador in url_lower:
                score += 15

        # Pontos por conteúdo
        for indicador in self.indicadores_positivos:
            if indicador in html_lower:
                score += 5

        # Pontos por ter links de WhatsApp
        whatsapp_count = html_lower.count("chat.whatsapp.com")
        score += min(whatsapp_count * 10, 30)  # Max 30 pontos

        # Penalidades
        if "login" in url_lower or "signin" in url_lower:
            score -= 20
        if "facebook.com" in url_lower or "instagram.com" in url_lower:
            score -= 50

        return max(0, min(100, score))

    async def analisar_url(self, url: str) -> Optional[Dict]:
        """
        Analisa uma URL candidata.

        Returns:
            Dict com info da fonte ou None se não relevante
        """
        dominio = self.extrair_dominio(url)

        if not dominio or dominio in self.dominios_ignorados:
            return None

        # Verificar se já existe
        result = supabase.table("group_sources").select("id").eq(
            "dominio", dominio
        ).execute()

        if result.data:
            return None  # Já conhecemos

        # Buscar conteúdo
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    timeout=30,
                    follow_redirects=True,
                )
                html = resp.text
            except Exception as e:
                logger.debug(f"[Discovery] Erro ao acessar {url}: {e}")
                return None

        # Pontuar
        score = self.pontuar_url(url, html)

        if score < 30:
            return None  # Não relevante

        # Contar links de WhatsApp
        whatsapp_links = len(re.findall(r"chat\.whatsapp\.com/[A-Za-z0-9]+", html))

        if whatsapp_links == 0:
            return None  # Sem links de WhatsApp

        # Detectar método necessário
        metodo = "requests"
        if any(x in html.lower() for x in ["react", "vue", "angular", "__next"]):
            metodo = "playwright"

        return {
            "url": url,
            "dominio": dominio,
            "nome": dominio.split(".")[0].title(),
            "tipo": "agregador",
            "metodo_crawl": metodo,
            "score": score,
            "whatsapp_links": whatsapp_links,
        }

    async def executar_discovery(self) -> Dict:
        """
        Executa ciclo de descoberta de fontes.

        Returns:
            {
                "queries_executadas": N,
                "urls_analisadas": N,
                "fontes_novas": N,
                "fontes": [...]
            }
        """
        resultado = {
            "queries_executadas": 0,
            "urls_analisadas": 0,
            "fontes_novas": 0,
            "fontes": [],
        }

        # Buscar queries ativas
        queries_result = supabase.table("discovery_queries").select("*").eq(
            "ativo", True
        ).lte(
            "proximo_run", datetime.now(UTC).isoformat()
        ).execute()

        queries = queries_result.data or []

        for query_row in queries:
            query = query_row["query"]
            engine = query_row["engine"]

            logger.info(f"[Discovery] Executando: '{query}' via {engine}")

            # Buscar URLs
            if engine == "google":
                urls = await self.buscar_google(query)
            elif engine == "bing":
                urls = await self.buscar_bing(query)
            else:
                urls = []

            resultado["queries_executadas"] += 1
            resultado["urls_analisadas"] += len(urls)

            # Analisar cada URL
            for url in urls:
                fonte = await self.analisar_url(url)

                if fonte:
                    # Salvar nova fonte
                    try:
                        supabase.table("group_sources").insert({
                            "url": fonte["url"],
                            "dominio": fonte["dominio"],
                            "nome": fonte["nome"],
                            "tipo": fonte["tipo"],
                            "metodo_crawl": fonte["metodo_crawl"],
                            "descoberto_via": engine,
                            "proximo_crawl": datetime.now(UTC).isoformat(),
                        }).execute()

                        resultado["fontes_novas"] += 1
                        resultado["fontes"].append(fonte)

                        logger.info(
                            f"[Discovery] Nova fonte: {fonte['dominio']} "
                            f"({fonte['whatsapp_links']} links, score={fonte['score']})"
                        )

                    except Exception as e:
                        # Provavelmente duplicata
                        pass

            # Atualizar próximo run da query
            proximo = datetime.now(UTC) + timedelta(days=query_row["frequencia_dias"])
            supabase.table("discovery_queries").update({
                "ultimo_run": datetime.now(UTC).isoformat(),
                "proximo_run": proximo.isoformat(),
                "fontes_descobertas": query_row["fontes_descobertas"] + resultado["fontes_novas"],
            }).eq("id", query_row["id"]).execute()

        return resultado


# Singleton
source_discovery = SourceDiscovery()
```

---

#### S12.6.2 - Crawler Manager

**Arquivo:** `app/services/groups/crawler.py`

```python
"""
Crawler Manager - Gerencia crawling de fontes conhecidas.

Características:
- Parser genérico para novos sites
- Parsers específicos para sites conhecidos
- Rate limiting por domínio
- Retry com backoff
"""
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, UTC
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.supabase import supabase
from app.services.groups.importer import extrair_invite_code

logger = logging.getLogger(__name__)


class CrawlerManager:
    """Gerenciador de crawling de fontes."""

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def crawl_fonte(self, source_id: str) -> Dict:
        """
        Executa crawl de uma fonte específica.

        Returns:
            {
                "status": "sucesso" | "parcial" | "erro",
                "links_encontrados": N,
                "links_novos": N,
                "erro": str (se houver)
            }
        """
        # Buscar fonte
        result = supabase.table("group_sources").select("*").eq(
            "id", source_id
        ).single().execute()

        if not result.data:
            return {"status": "erro", "erro": "Fonte não encontrada"}

        fonte = result.data
        inicio = datetime.now(UTC)

        logger.info(f"[Crawler] Iniciando: {fonte['dominio']}")

        try:
            # Executar crawl baseado no método
            if fonte["metodo_crawl"] == "requests":
                links = await self._crawl_requests(fonte)
            elif fonte["metodo_crawl"] == "playwright":
                links = await self._crawl_playwright(fonte)
            else:
                links = []

            # Processar links
            resultado = await self._processar_links(links, fonte)

            # Calcular duração
            duracao = int((datetime.now(UTC) - inicio).total_seconds())

            # Atualizar fonte
            supabase.table("group_sources").update({
                "ultimo_crawl": datetime.now(UTC).isoformat(),
                "proximo_crawl": (
                    datetime.now(UTC) + timedelta(days=fonte["frequencia_dias"])
                ).isoformat(),
                "total_grupos_extraidos": fonte["total_grupos_extraidos"] + resultado["links_novos"],
                "falhas_consecutivas": 0,
            }).eq("id", source_id).execute()

            # Registrar histórico
            supabase.table("crawl_history").insert({
                "source_id": source_id,
                "status": "sucesso",
                "duracao_segundos": duracao,
                "links_encontrados": resultado["links_encontrados"],
                "links_novos": resultado["links_novos"],
                "links_duplicados": resultado["links_duplicados"],
            }).execute()

            logger.info(
                f"[Crawler] {fonte['dominio']}: "
                f"{resultado['links_novos']} novos de {resultado['links_encontrados']}"
            )

            return resultado

        except Exception as e:
            logger.error(f"[Crawler] Erro em {fonte['dominio']}: {e}")

            # Atualizar falhas
            falhas = fonte["falhas_consecutivas"] + 1
            status = "erro" if falhas >= 3 else "ativo"

            supabase.table("group_sources").update({
                "falhas_consecutivas": falhas,
                "status": status,
                "proximo_crawl": (
                    datetime.now(UTC) + timedelta(days=1)  # Retry amanhã
                ).isoformat(),
            }).eq("id", source_id).execute()

            # Registrar histórico
            supabase.table("crawl_history").insert({
                "source_id": source_id,
                "status": "erro",
                "erro": str(e)[:500],
            }).execute()

            return {"status": "erro", "erro": str(e)}

    async def _crawl_requests(self, fonte: Dict) -> List[Dict]:
        """Crawl usando requests (sites HTML simples)."""
        links = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                fonte["url"],
                headers={"User-Agent": self.user_agent},
                timeout=30,
                follow_redirects=True,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Buscar links de WhatsApp
            for a in soup.find_all("a", href=re.compile(r"chat\.whatsapp\.com")):
                href = a.get("href", "")
                invite_code = extrair_invite_code(href)

                if invite_code:
                    # Tentar extrair nome do contexto
                    nome = a.get_text(strip=True)
                    if not nome or len(nome) < 3:
                        parent = a.find_parent(["div", "li", "article"])
                        if parent:
                            title = parent.find(["h2", "h3", "h4", "strong"])
                            if title:
                                nome = title.get_text(strip=True)

                    links.append({
                        "invite_code": invite_code,
                        "invite_url": href,
                        "nome": nome[:100] if nome else None,
                    })

        return links

    async def _crawl_playwright(self, fonte: Dict) -> List[Dict]:
        """Crawl usando Playwright (sites JavaScript)."""
        from playwright.async_api import async_playwright

        links = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()

            try:
                await page.goto(fonte["url"], timeout=60000)
                await page.wait_for_timeout(5000)

                # Scroll para carregar lazy content
                for _ in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                # Extrair links
                whatsapp_links = await page.query_selector_all('a[href*="chat.whatsapp.com"]')

                for link in whatsapp_links:
                    href = await link.get_attribute("href")
                    nome = await link.inner_text()

                    invite_code = extrair_invite_code(href or "")
                    if invite_code:
                        links.append({
                            "invite_code": invite_code,
                            "invite_url": href,
                            "nome": nome[:100] if nome else None,
                        })

            finally:
                await browser.close()

        return links

    async def _processar_links(self, links: List[Dict], fonte: Dict) -> Dict:
        """Processa links extraídos e salva novos."""
        resultado = {
            "links_encontrados": len(links),
            "links_novos": 0,
            "links_duplicados": 0,
            "links_invalidos": 0,
        }

        for link in links:
            invite_code = link["invite_code"]

            # Verificar se já existe
            exists = supabase.table("group_links").select("id").eq(
                "invite_code", invite_code
            ).execute()

            if exists.data:
                resultado["links_duplicados"] += 1
                continue

            # Inserir novo
            try:
                supabase.table("group_links").insert({
                    "invite_code": invite_code,
                    "invite_url": link.get("invite_url"),
                    "nome": link.get("nome"),
                    "fonte": fonte["dominio"],
                    "status": "pendente",
                }).execute()
                resultado["links_novos"] += 1
            except:
                resultado["links_duplicados"] += 1

        return resultado

    async def executar_crawls_pendentes(self, limite: int = 5) -> Dict:
        """
        Executa crawls de fontes que estão prontas.

        Returns:
            {
                "fontes_processadas": N,
                "total_links_novos": N
            }
        """
        # Buscar fontes prontas
        result = supabase.table("group_sources").select("id, dominio").eq(
            "status", "ativo"
        ).lte(
            "proximo_crawl", datetime.now(UTC).isoformat()
        ).limit(limite).execute()

        fontes = result.data or []

        total = {
            "fontes_processadas": 0,
            "total_links_novos": 0,
        }

        for fonte in fontes:
            resultado = await self.crawl_fonte(fonte["id"])
            total["fontes_processadas"] += 1
            total["total_links_novos"] += resultado.get("links_novos", 0)

        return total


# Singleton
crawler_manager = CrawlerManager()
```

---

### Jobs do Scheduler

```python
# ============================================================
# JOBS DE DESCOBERTA E CRAWLING
# ============================================================

# Discovery QUINZENAL (a cada 2 semanas) - sites agregadores mudam pouco
# Roda no dia 1 e 15 de cada mês, às 00h BRT (03h UTC)
@scheduler.scheduled_job("cron", day="1,15", hour=3)
async def executar_discovery_quinzenal():
    """Descobre novas fontes de grupos (quinzenal)."""
    from app.services.groups.discovery import source_discovery
    from app.services.notificacoes import notificar_slack

    resultado = await source_discovery.executar_discovery()
    logger.info(f"[Discovery] {resultado['fontes_novas']} novas fontes descobertas")

    # Notificar Slack
    if resultado["fontes_novas"] > 0:
        fontes_lista = "\n".join([
            f"  • {f['dominio']} ({f['whatsapp_links']} links)"
            for f in resultado["fontes"][:5]
        ])
        await notificar_slack(
            f":mag: *Discovery Quinzenal*\n"
            f"Queries executadas: {resultado['queries_executadas']}\n"
            f"URLs analisadas: {resultado['urls_analisadas']}\n"
            f"*Novas fontes: {resultado['fontes_novas']}*\n\n"
            f"{fontes_lista}",
            canal="operacoes"
        )
    else:
        await notificar_slack(
            f":mag: *Discovery Quinzenal*\n"
            f"Queries: {resultado['queries_executadas']} | "
            f"URLs: {resultado['urls_analisadas']} | "
            f"Novas fontes: 0",
            canal="operacoes"
        )


@scheduler.scheduled_job("cron", day_of_week="mon,thu", hour=4)  # Seg/Qui 01h BRT
async def executar_crawls_fontes():
    """Crawl de fontes conhecidas (2x/semana)."""
    from app.services.groups.crawler import crawler_manager
    from app.services.notificacoes import notificar_slack

    resultado = await crawler_manager.executar_crawls_pendentes(limite=10)
    logger.info(
        f"[Crawler] {resultado['fontes_processadas']} fontes, "
        f"{resultado['total_links_novos']} novos links"
    )

    # Notificar Slack
    emoji = ":white_check_mark:" if resultado["total_links_novos"] > 0 else ":information_source:"
    await notificar_slack(
        f"{emoji} *Crawler de Grupos*\n"
        f"Fontes processadas: {resultado['fontes_processadas']}\n"
        f"*Links novos: {resultado['total_links_novos']}*\n\n"
        f"Próximo crawl: Seg/Qui 01h",
        canal="operacoes"
    )
```

---

### Fontes Iniciais (Seed)

```sql
-- Fontes conhecidas (seed inicial)
INSERT INTO group_sources (url, dominio, nome, tipo, metodo_crawl, frequencia_dias) VALUES
    ('https://escaladeplantao.com.br/grupos', 'escaladeplantao.com.br', 'Escala de Plantão', 'agregador', 'requests', 7),
    ('https://gruposmedicos.com.br/', 'gruposmedicos.com.br', 'Grupos Médicos', 'agregador', 'requests', 7),
    ('https://queroplantao.com.br/grupos/', 'queroplantao.com.br', 'Quero Plantão', 'agregador', 'playwright', 7),
    ('https://web.searchplantao.com.br/grupos', 'searchplantao.com.br', 'Search Plantão', 'agregador', 'playwright', 7),
    ('https://plantoesmedicosbrasil.com.br/', 'plantoesmedicosbrasil.com.br', 'Plantões Brasil', 'agregador', 'playwright', 7)
ON CONFLICT (url) DO NOTHING;
```

---

### Periodicidade Recomendada

| Tarefa | Frequência | Motivo |
|--------|-----------|--------|
| Crawl de fontes conhecidas | 2x/semana | Sites atualizam pouco |
| Discovery de novas fontes | Quinzenal (dia 1 e 15) | Busca é cara (rate limits) |
| Validação de links | Diária | Links expiram |
| Limpeza de links inválidos | Semanal | Manutenção |
| Recovery circuit breaker | A cada hora | Recuperação automática |
| Reset contador 6h | A cada 6h (00,06,12,18h) | Evita rajadas |

---

### DoD Adicional (S12.6)

- [ ] Tabelas de fontes e histórico criadas
- [ ] Discovery via Google/Bing funcionando
- [ ] Crawler genérico (requests) funcionando
- [ ] Crawler JavaScript (Playwright) funcionando
- [ ] Jobs agendados configurados
- [ ] Fontes seed inseridas
- [ ] Deduplicação funcionando
- [ ] Métricas sendo registradas

---

## Priorização das Sub-tarefas

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRIORIZAÇÃO E12                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SPRINT 25 - Foundation (8h):                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                  │
│  ✅ S12.1 - Group Link Manager (import CSV/Excel)    ~2h        │
│  ✅ S12.2 - Link Validator                           ~1h        │
│  ✅ S12.3 - Entry Scheduler (limites por fase)       ~2h        │
│  ✅ S12.4 - Entry Worker (circuit breaker)           ~2h        │
│  ✅ S12.5 - Management API + Dashboard               ~1h        │
│                                                                  │
│  SPRINT 26 - Discovery (3h):                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                   │
│  ✅ S12.6 - Crawler & Source Discovery               ~3h        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Estimativa total E12:** 11h (8h Sprint 25 + 3h Sprint 26)

---

## Métricas de Sucesso

```
┌─────────────────────────────────────────────────────┐
│        MÉTRICAS E12 - GROUP ENTRY ENGINE           │
├─────────────────────────────────────────────────────┤
│ Taxa de entrada bem-sucedida:   > 80%              │
│ Média de tentativas por grupo:  < 1.5              │
│ Circuit breakers ativados/dia:  0                  │
│ Grupos/dia (por chip listener): 2-10 (por fase)    │
│ Tempo médio de espera na fila:  < 30 min           │
│ Links inválidos descobertos:    < 20%              │
│ Latência média de entrada:      < 10s              │
└─────────────────────────────────────────────────────┘
```

**Alertas críticos:**
- 3+ circuit breakers no mesmo dia → Investigar padrão
- Taxa de sucesso < 60% → Links podem estar expirados
- Fila com 50+ itens pendentes → Aumentar capacidade
- Latência > 30s consistente → Problema na Evolution API

---

## Plano de Testes

### Fase 1: Validação Básica (Dia 1-3)
```
- [ ] Importar 20 links conhecidos via CSV
- [ ] Distribuir entre 2 chips LISTENERS em fase 'expansao'
- [ ] Validar que respeita limite 2 grupos/dia
- [ ] Validar delays mínimos de 10min
- [ ] Verificar que chips JULIA não são selecionados
```

### Fase 2: Escala Moderada (Dia 4-7)
```
- [ ] Importar 50 links
- [ ] Usar 3 chips em fase 'pre_operacao'
- [ ] Validar limite 5 grupos/dia
- [ ] Validar limite 3 grupos/6h (anti-rajada)
- [ ] Verificar distribuição balanceada entre chips
```

### Fase 3: Produção (Dia 8-14)
```
- [ ] 100+ links na fila
- [ ] 5 chips em 'operacao'
- [ ] Validar limite 10 grupos/dia
- [ ] Validar limite 5 grupos/6h
- [ ] Monitorar Trust Score (não deve cair)
- [ ] Testar circuit breaker (simular erros)
- [ ] Verificar recovery automático após 6h
```

### Critérios de Aprovação
```
✅ Se todos os testes passarem: deploy em produção
❌ Se qualquer falha: ajustar parâmetros e repetir
```

---

*Épico criado em 31/12/2025*
*Atualizado em 31/12/2025 - Incorporadas melhorias:*
- *Separação de pools (julia vs listener)*
- *Limite por janela de 6h (anti-rajada)*
- *Telemetria de latência*
- *Recovery automático do circuit breaker*
- *Discovery quinzenal (não semanal)*
- *Priorização: S12.1-S12.5 Sprint 25, S12.6 Sprint 26*
- *Métricas de sucesso e plano de testes*
