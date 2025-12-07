# Epic 07: Briefing via Google Docs

## Prioridade: P2 (Melhoria)

## Objetivo

> **Permitir que gestor configure diretrizes da Júlia editando um Google Docs.**

Documentado em `docs/FLUXOS.md` - Fluxo 10: Briefing do Gestor.

---

## Referência: FLUXOS.md

```
GESTOR         GOOGLE DOCS       WORKER         BANCO
  │                │               │              │
  │  1. Edita      │               │              │
  │     documento  │               │              │
  │────────────────▶               │              │
  │                │               │              │
  │                │  2. Worker    │              │
  │                │◀──────────────│              │
  │                │  busca doc    │              │
  │                │  (a cada 60m) │              │
  │                │               │              │
  │                │───────────────▶              │
  │                │  conteúdo     │              │
  │                │               │              │
  │                │               │  3. Compara  │
  │                │               │     hash     │
  │                │               │              │
  │                │               │  4. Se mudou:│
  │                │               │     • Parseia│
  │                │               │     • Extrai │
  │                │               │       seções │
  │                │               │              │
  │                │               │  5. INSERT/  │
  │                │               │     UPDATE   │
  │                │               │─────────────▶│
  │                │               │  diretrizes  │
```

---

## Problema Atual

- Não existe integração com Google Docs
- Diretrizes são configuradas diretamente no banco
- Gestor não tem forma fácil de atualizar comportamento

---

## Stories

---

# S7.E7.1 - Configurar Google Docs API

## Objetivo

> **Configurar credenciais e acesso à API do Google Docs.**

## Pré-requisitos

1. Conta Google Workspace ou Gmail
2. Projeto no Google Cloud Console
3. API do Google Docs habilitada
4. Service Account com acesso ao documento

## Passos de Configuração

### 1. Google Cloud Console

```
1. Acessar console.cloud.google.com
2. Criar projeto "Julia-Briefing"
3. Ativar APIs:
   - Google Docs API
   - Google Drive API
4. Criar Service Account:
   - Nome: julia-briefing-reader
   - Papel: Viewer
5. Gerar chave JSON
6. Salvar como credentials.json
```

### 2. Compartilhar Documento

```
1. Criar Google Docs com template de briefing
2. Compartilhar com email do Service Account
3. Dar permissão de "Leitor"
4. Copiar Document ID da URL
```

### 3. Variáveis de Ambiente

**Arquivo:** `.env.example` (adicionar)

```bash
# Google Docs (Briefing)
GOOGLE_DOCS_CREDENTIALS_PATH=./credentials/google_docs.json
GOOGLE_BRIEFING_DOC_ID=1abc...xyz
```

## Código Esperado

**Arquivo:** `app/services/google_docs.py` (criar)

```python
import os
import json
import hashlib
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# Configuração
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
CREDENTIALS_PATH = os.getenv('GOOGLE_DOCS_CREDENTIALS_PATH')
DOC_ID = os.getenv('GOOGLE_BRIEFING_DOC_ID')


def _get_credentials():
    """Carrega credenciais do Service Account."""
    if not CREDENTIALS_PATH:
        raise ValueError("GOOGLE_DOCS_CREDENTIALS_PATH não configurado")

    return service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=SCOPES
    )


def _get_docs_service():
    """Retorna cliente da API do Google Docs."""
    credentials = _get_credentials()
    return build('docs', 'v1', credentials=credentials)


async def buscar_documento_briefing() -> dict:
    """
    Busca conteúdo do documento de briefing.

    Returns:
        dict com:
        - content: str (texto completo)
        - hash: str (hash do conteúdo para comparação)
        - title: str (título do documento)
    """
    try:
        service = _get_docs_service()
        document = service.documents().get(documentId=DOC_ID).execute()

        # Extrair texto de todos os elementos
        content = _extrair_texto(document)

        # Calcular hash para detectar mudanças
        content_hash = hashlib.md5(content.encode()).hexdigest()

        return {
            "success": True,
            "content": content,
            "hash": content_hash,
            "title": document.get('title', 'Briefing'),
            "doc_id": DOC_ID
        }

    except Exception as e:
        logger.error(f"Erro ao buscar documento Google Docs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def _extrair_texto(document: dict) -> str:
    """Extrai texto plano de um documento do Google Docs."""
    content = document.get('body', {}).get('content', [])
    text_parts = []

    for element in content:
        if 'paragraph' in element:
            for text_run in element['paragraph'].get('elements', []):
                if 'textRun' in text_run:
                    text_parts.append(text_run['textRun'].get('content', ''))

    return ''.join(text_parts)
```

## Critérios de Aceite

1. **Credenciais:** Service Account configurado
2. **Acesso:** Consegue ler documento compartilhado
3. **Extração:** Texto extraído corretamente
4. **Hash:** Calcula hash para detectar mudanças

## DoD

- [x] Service Account criado no Google Cloud
- [x] Credenciais JSON salvas em local seguro
- [x] Variáveis de ambiente configuradas
- [x] `buscar_documento_briefing()` funciona
- [x] Teste: retorna conteúdo do documento

---

# S7.E7.2 - Implementar parser de briefing

## Objetivo

> **Parsear documento e extrair seções estruturadas.**

## Estrutura Esperada do Documento

```markdown
# Briefing Júlia - Semana 09/12

## Foco da Semana
- Priorizar anestesistas do ABC
- Empurrar vagas do Hospital Brasil (urgente)

## Vagas Prioritárias
- Hospital Brasil - Sábado 14/12 - até R$ 2.800
- São Luiz - Domingo 15/12 - até R$ 3.000

## Médicos VIP
- Dr. Carlos (CRM 123456) - sempre dar atenção especial
- Dra. Ana (CRM 789012) - potencial alto volume

## Médicos Bloqueados
- Dr. João (CRM 111111) - não contatar (pediu opt-out)

## Tom da Semana
- Mais urgente (vagas precisam preencher)
- Pode oferecer até 15% a mais em negociação

## Observações
- Evitar contato segunda-feira (feriado regional)
```

## Código Esperado

**Arquivo:** `app/services/briefing_parser.py` (criar)

```python
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def parsear_briefing(conteudo: str) -> dict:
    """
    Parseia documento de briefing e extrai seções.

    Args:
        conteudo: Texto completo do documento

    Returns:
        dict com seções parseadas
    """
    secoes = {
        "foco_semana": [],
        "vagas_prioritarias": [],
        "medicos_vip": [],
        "medicos_bloqueados": [],
        "tom_semana": [],
        "observacoes": [],
        "margem_negociacao": None,
        "raw": conteudo
    }

    # Dividir por seções (## Título)
    partes = re.split(r'\n##\s+', conteudo)

    for parte in partes:
        linhas = parte.strip().split('\n')
        if not linhas:
            continue

        titulo = linhas[0].lower().strip()
        itens = [l.strip().lstrip('- ') for l in linhas[1:] if l.strip().startswith('-')]

        if 'foco' in titulo:
            secoes["foco_semana"] = itens
        elif 'vaga' in titulo and 'priorit' in titulo:
            secoes["vagas_prioritarias"] = _parsear_vagas(itens)
        elif 'vip' in titulo:
            secoes["medicos_vip"] = _parsear_medicos(itens)
        elif 'bloqueado' in titulo:
            secoes["medicos_bloqueados"] = _parsear_medicos(itens)
        elif 'tom' in titulo:
            secoes["tom_semana"] = itens
            # Extrair margem de negociação se mencionada
            for item in itens:
                match = re.search(r'(\d+)%', item)
                if match and 'mais' in item.lower():
                    secoes["margem_negociacao"] = int(match.group(1))
        elif 'observa' in titulo:
            secoes["observacoes"] = itens

    return secoes


def _parsear_vagas(itens: list) -> list:
    """Extrai informações de vagas prioritárias."""
    vagas = []
    for item in itens:
        # Formato esperado: "Hospital X - Data - até R$ Y"
        match = re.search(r'(.+?)\s*-\s*(.+?)\s*-\s*(?:até\s*)?R\$\s*([\d.,]+)', item)
        if match:
            vagas.append({
                "hospital": match.group(1).strip(),
                "data": match.group(2).strip(),
                "valor_max": float(match.group(3).replace('.', '').replace(',', '.'))
            })
        else:
            vagas.append({"raw": item})

    return vagas


def _parsear_medicos(itens: list) -> list:
    """Extrai informações de médicos (VIP ou bloqueados)."""
    medicos = []
    for item in itens:
        # Formato esperado: "Dr. Nome (CRM XXXXX) - observação"
        match = re.search(r'(?:Dr\.?a?\.?\s*)?(.+?)\s*\(CRM\s*(\d+)\)', item, re.IGNORECASE)
        if match:
            obs = item.split('-')[-1].strip() if '-' in item else ""
            medicos.append({
                "nome": match.group(1).strip(),
                "crm": match.group(2),
                "observacao": obs
            })
        else:
            medicos.append({"raw": item})

    return medicos
```

## Critérios de Aceite

1. **Extrai seções:** Todas as seções do template são parseadas
2. **Estrutura vagas:** Hospital, data, valor extraídos
3. **Estrutura médicos:** Nome, CRM, observação extraídos
4. **Margem negociação:** Percentual extraído do tom
5. **Tolerante a erros:** Não quebra se formato diferente

## DoD

- [x] `parsear_briefing()` implementada
- [x] Extrai 6 seções diferentes
- [x] `_parsear_vagas()` estrutura corretamente
- [x] `_parsear_medicos()` estrutura corretamente
- [x] Extrai margem de negociação
- [x] Teste: documento exemplo → dict estruturado

---

# S7.E7.3 - Implementar worker de sincronização

## Objetivo

> **Worker que verifica mudanças no documento a cada 60min.**

## Código Esperado

**Arquivo:** `app/services/briefing.py` (criar)

```python
from datetime import datetime
from app.services.google_docs import buscar_documento_briefing
from app.services.briefing_parser import parsear_briefing
from app.services.supabase import supabase
from app.services.slack import enviar_slack
import logging

logger = logging.getLogger(__name__)

# Cache do último hash processado
_ultimo_hash: str = None


async def sincronizar_briefing() -> dict:
    """
    Sincroniza briefing do Google Docs com o banco.

    Executado a cada 60 minutos pelo scheduler.

    Returns:
        dict com status da sincronização
    """
    global _ultimo_hash

    # 1. Buscar documento
    doc = await buscar_documento_briefing()
    if not doc.get("success"):
        return {"success": False, "error": doc.get("error")}

    # 2. Verificar se mudou
    if doc["hash"] == _ultimo_hash:
        logger.debug("Briefing não mudou desde última verificação")
        return {"success": True, "changed": False}

    logger.info(f"Briefing mudou! Hash anterior: {_ultimo_hash}, novo: {doc['hash']}")

    # 3. Parsear conteúdo
    briefing = parsear_briefing(doc["content"])

    # 4. Atualizar diretrizes no banco
    await _atualizar_diretrizes(briefing)

    # 5. Atualizar médicos VIP/bloqueados
    await _atualizar_medicos_vip(briefing.get("medicos_vip", []))
    await _atualizar_medicos_bloqueados(briefing.get("medicos_bloqueados", []))

    # 6. Atualizar vagas prioritárias
    await _atualizar_vagas_prioritarias(briefing.get("vagas_prioritarias", []))

    # 7. Salvar registro de sincronização
    await supabase.table("briefing_sync_log").insert({
        "doc_hash": doc["hash"],
        "doc_title": doc["title"],
        "conteudo_raw": doc["content"][:5000],  # Limitar tamanho
        "parseado": briefing,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    # 8. Notificar no Slack
    await _notificar_atualizacao(briefing)

    # 9. Atualizar cache
    _ultimo_hash = doc["hash"]

    return {
        "success": True,
        "changed": True,
        "hash": doc["hash"],
        "secoes_atualizadas": list(briefing.keys())
    }


async def _atualizar_diretrizes(briefing: dict):
    """Atualiza tabela de diretrizes com novo briefing."""

    # Foco da semana
    if briefing.get("foco_semana"):
        await _upsert_diretriz(
            tipo="foco_semana",
            conteudo="\n".join(briefing["foco_semana"]),
            prioridade=10
        )

    # Tom da semana
    if briefing.get("tom_semana"):
        await _upsert_diretriz(
            tipo="tom_semana",
            conteudo="\n".join(briefing["tom_semana"]),
            prioridade=9
        )

    # Margem de negociação
    if briefing.get("margem_negociacao"):
        await _upsert_diretriz(
            tipo="margem_negociacao",
            conteudo=str(briefing["margem_negociacao"]),
            prioridade=8
        )

    # Observações
    if briefing.get("observacoes"):
        await _upsert_diretriz(
            tipo="observacoes",
            conteudo="\n".join(briefing["observacoes"]),
            prioridade=5
        )


async def _upsert_diretriz(tipo: str, conteudo: str, prioridade: int):
    """Insere ou atualiza diretriz."""
    # Verificar se existe
    existing = await supabase.table("diretrizes").select("id").eq("tipo", tipo).execute()

    if existing.data:
        await supabase.table("diretrizes").update({
            "conteudo": conteudo,
            "prioridade": prioridade,
            "ativo": True,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("tipo", tipo).execute()
    else:
        await supabase.table("diretrizes").insert({
            "tipo": tipo,
            "conteudo": conteudo,
            "prioridade": prioridade,
            "ativo": True
        }).execute()


async def _atualizar_medicos_vip(medicos: list):
    """Marca médicos como VIP baseado no briefing."""
    for med in medicos:
        if crm := med.get("crm"):
            await supabase.table("clientes").update({
                "vip": True,
                "notas_vip": med.get("observacao", "")
            }).eq("crm", crm).execute()


async def _atualizar_medicos_bloqueados(medicos: list):
    """Marca médicos como bloqueados baseado no briefing."""
    for med in medicos:
        if crm := med.get("crm"):
            await supabase.table("clientes").update({
                "bloqueado": True,
                "motivo_bloqueio": med.get("observacao", "")
            }).eq("crm", crm).execute()


async def _atualizar_vagas_prioritarias(vagas: list):
    """Atualiza prioridade de vagas baseado no briefing."""
    for vaga in vagas:
        if hospital := vaga.get("hospital"):
            # Buscar vagas do hospital e marcar como urgente
            await supabase.table("vagas").update({
                "prioridade": "urgente"
            }).ilike("hospitais.nome", f"%{hospital}%").eq(
                "status", "aberta"
            ).execute()


async def _notificar_atualizacao(briefing: dict):
    """Notifica no Slack que briefing foi atualizado."""
    await enviar_slack({
        "text": "📋 Briefing atualizado!",
        "attachments": [{
            "color": "#36a64f",
            "fields": [
                {"title": "Foco", "value": briefing.get("foco_semana", ["N/A"])[0][:50] if briefing.get("foco_semana") else "N/A"},
                {"title": "Vagas Prioritárias", "value": str(len(briefing.get("vagas_prioritarias", [])))},
                {"title": "Médicos VIP", "value": str(len(briefing.get("medicos_vip", [])))},
                {"title": "Médicos Bloqueados", "value": str(len(briefing.get("medicos_bloqueados", [])))},
            ]
        }]
    })
```

## DoD

- [x] `sincronizar_briefing()` implementada
- [x] Detecta mudanças via hash
- [x] Atualiza tabela `diretrizes`
- [x] Atualiza flags de médicos VIP/bloqueados
- [x] Atualiza prioridade de vagas
- [x] Notifica Slack quando atualiza
- [x] Log de sincronização salvo

---

# S7.E7.4 - Adicionar job no scheduler

## Objetivo

> **Configurar job para rodar sincronização a cada 60 minutos.**

## Código Esperado

**Arquivo:** `app/workers/scheduler.py` (adicionar)

```python
JOBS = [
    # ... outros jobs ...

    {
        "name": "sincronizar_briefing",
        "endpoint": "/jobs/sincronizar-briefing",
        "schedule": "0 * * * *",  # A cada hora, minuto 0
    },
]
```

**Arquivo:** `app/api/routes/jobs.py` (adicionar)

```python
@router.post("/sincronizar-briefing")
async def job_sincronizar_briefing():
    """Job para sincronizar briefing do Google Docs."""
    from app.services.briefing import sincronizar_briefing
    result = await sincronizar_briefing()
    return {"status": "ok", "result": result}
```

## DoD

- [x] Job `sincronizar_briefing` configurado
- [x] Roda a cada 60 minutos
- [x] Endpoint `/jobs/sincronizar-briefing` funciona
- [x] Teste: chamar endpoint → sincroniza

---

# S7.E7.5 - Integrar diretrizes no contexto do agente

## Objetivo

> **Carregar diretrizes ativas no contexto para o LLM usar.**

## Código Esperado

**Arquivo:** `app/services/contexto.py` (modificar)

```python
async def montar_contexto_completo(medico, conversa, incluir_vagas=True):
    """Monta contexto completo para o agente."""

    # ... código existente ...

    # Carregar diretrizes ativas
    diretrizes = await _carregar_diretrizes_ativas()

    return {
        # ... outros campos ...
        "diretrizes": diretrizes,
    }


async def _carregar_diretrizes_ativas() -> dict:
    """Carrega diretrizes ativas do briefing."""
    response = await supabase.table("diretrizes").select(
        "tipo, conteudo"
    ).eq("ativo", True).order("prioridade", desc=True).execute()

    diretrizes = {}
    for d in response.data or []:
        diretrizes[d["tipo"]] = d["conteudo"]

    return diretrizes
```

**Arquivo:** `app/core/prompts.py` (adicionar)

```python
INSTRUCOES_DIRETRIZES = """
## Diretrizes do Gestor

{diretrizes_foco}

{diretrizes_tom}

{diretrizes_observacoes}

Siga essas diretrizes como prioridade máxima.
"""
```

## DoD

- [x] Diretrizes carregadas no contexto
- [x] System prompt inclui diretrizes
- [x] Teste: diretriz "urgente" → Júlia usa tom urgente

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E7.1 | Configurar Google API | Alta |
| S7.E7.2 | Parser de briefing | Média |
| S7.E7.3 | Worker de sincronização | Alta |
| S7.E7.4 | Job no scheduler | Baixa |
| S7.E7.5 | Integrar no contexto | Média |

## Arquivos Criados/Modificados

| Arquivo | Ação |
|---------|------|
| `app/services/google_docs.py` | Criar |
| `app/services/briefing_parser.py` | Criar |
| `app/services/briefing.py` | Criar |
| `app/workers/scheduler.py` | Modificar |
| `app/api/routes/jobs.py` | Modificar |
| `app/services/contexto.py` | Modificar |
| `app/core/prompts.py` | Modificar |

## Fluxo Completo

```
1. Gestor edita Google Docs
2. Worker detecta mudança (a cada 60min)
3. Parser extrai seções
4. Banco atualizado (diretrizes, médicos, vagas)
5. Slack notificado
6. Próxima conversa usa novas diretrizes
```
