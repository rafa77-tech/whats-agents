# Guia de Migracao de Padroes Deprecated

Guia para migrar codigo que usa padroes antigos (deprecated) para padroes atuais recomendados.

**Data de Atualizacao:** 10/02/2026
**Status:** Versao 1.0
**Manutencao:** Engenharia

---

## Visao Geral

Este documento mapeia padroes deprecated para seus equivalentes atuais, baseado em:
- Refatoracoes arquiteturais (Sprint 10, 30, 44)
- Evolucao de convencoes de codigo
- Mudancas de estrutura de diretorios

**Quando usar este guia:**
- Ao fazer refactoring de codigo antigo
- Ao revisar PRs que usam padroes deprecated
- Ao escrever novo codigo (sempre usar padroes atuais)

---

## 1. Import do Supabase

### Deprecated

```python
from app.services.supabase import get_supabase_client

client = get_supabase_client()
response = client.table("clientes").select("*").execute()
```

### Atual (Sprint 30+)

```python
from app.services.supabase import supabase

response = supabase.table("clientes").select("*").execute()
```

**Por que mudou:**
- `supabase` eh singleton global, nao precisa chamar funcao
- Menos verboso, imports mais limpos
- Consistente com outros servicos (claude, evolution)

**Como encontrar codigo deprecated:**

```bash
# Buscar imports antigos
grep -r "get_supabase_client" app/

# Buscar uso de get_supabase_client()
grep -r "get_supabase_client()" app/
```

**Migracao automatica (sed):**

```bash
# Substituir import
find app/ -name "*.py" -exec sed -i '' 's/from app.services.supabase import get_supabase_client/from app.services.supabase import supabase/g' {} +

# Substituir uso (mais complexo, revisar manualmente)
# client = get_supabase_client() -> supabase
# client.table -> supabase.table
```

---

## 2. Modulo de Campanhas

### Deprecated (Sprint 1-34)

```python
# Import antigo
from app.services.campanha import (
    criar_envios_campanha,
    executar_campanha,
    listar_campanhas
)

# Uso
envios = criar_envios_campanha(campaign_id, medico_ids)
```

### Atual (Sprint 35+)

```python
# Import novo (submodulo campanhas/)
from app.services.campanhas import campanha_repository, campanha_executor
from app.services.campanhas.types import TipoCampanha, StatusCampanha

# Uso
envios = await campanha_executor.criar_envios(campaign_id, medico_ids)
campanhas = await campanha_repository.listar(status=StatusCampanha.ATIVA)
```

**Por que mudou:**
- Modulo `campanha.py` cresceu para 800+ linhas
- Refatorado em submodulo `campanhas/` com responsabilidades separadas:
  - `campanha_repository.py`: CRUD de campanhas
  - `campanha_executor.py`: Logica de execucao
  - `segmentacao.py`: Logica de segmentacao
  - `templates.py`: Templates de mensagem
  - `types.py`: Tipos e enums

**Estrutura atual:**

```
app/services/campanhas/
├── __init__.py
├── campanha_repository.py
├── campanha_executor.py
├── segmentacao.py
├── templates.py
└── types.py
```

**Como encontrar codigo deprecated:**

```bash
# Buscar imports antigos
grep -r "from app.services.campanha import" app/

# Buscar uso de funcoes antigas
grep -r "criar_envios_campanha\|executar_campanha" app/
```

**Mapeamento de funcoes:**

| Deprecated | Atual | Modulo |
|------------|-------|--------|
| `criar_envios_campanha()` | `campanha_executor.criar_envios()` | `campanha_executor.py` |
| `executar_campanha()` | `campanha_executor.executar()` | `campanha_executor.py` |
| `listar_campanhas()` | `campanha_repository.listar()` | `campanha_repository.py` |
| `criar_campanha()` | `campanha_repository.criar()` | `campanha_repository.py` |
| `atualizar_campanha()` | `campanha_repository.atualizar()` | `campanha_repository.py` |
| `segmentar_medicos()` | `segmentacao.segmentar()` | `segmentacao.py` |
| `renderizar_template()` | `templates.renderizar()` | `templates.py` |

---

## 3. Pipeline de Processamento

### Deprecated (Sprint 1-9)

```python
# Codigo monolitico em webhook.py
@router.post("/webhook/evolution")
async def webhook_evolution(payload: dict):
    # Validacao inline
    if not payload.get("message"):
        return

    # Deteccao inline
    if eh_bot(payload["message"]["text"]):
        return

    # Rate limiting inline
    if not pode_enviar(medico_id):
        return

    # LLM call inline
    response = await claude.generate(...)

    # Humanizacao inline
    chunks = quebrar_em_chunks(response)
    for chunk in chunks:
        await enviar(chunk)
```

### Atual (Sprint 10+)

```python
# Pipeline plugavel
from app.pipeline import MessagePipeline
from app.pipeline.setup import setup_pipeline

# Setup
pipeline = setup_pipeline()

# Uso
@router.post("/webhook/evolution")
async def webhook_evolution(payload: dict):
    message = parse_payload(payload)
    response = await pipeline.process(message)
    return response
```

**Por que mudou:**
- Codigo monolitico de 500+ linhas refatorado em pipeline modular
- Cada etapa (deteccao, validacao, processamento) eh um processor isolado
- Facil de testar, adicionar novos processors, reordenar

**Estrutura atual:**

```
app/pipeline/
├── base.py              # Classes abstratas
├── core.py              # Orquestrador principal
├── processor.py         # Interface MessageProcessor
├── setup.py             # Bootstrap do pipeline
├── pre_processors.py    # Pre-processadores
├── post_processors.py   # Pos-processadores
└── processors/          # Implementacoes concretas
    ├── opt_out_detector.py
    ├── bot_detector.py
    ├── handoff_detector.py
    ├── rate_limiter.py
    ├── business_hours_validator.py
    ├── llm_processor.py
    ├── humanizer.py
    └── event_emitter.py
```

**Como migrar:**

1. Identificar logica inline em `webhook.py`
2. Extrair para processor dedicado
3. Adicionar processor em `setup.py`

Exemplo:

```python
# Antes: deteccao inline
if eh_horario_comercial():
    processar()

# Depois: processor
class BusinessHoursValidator(MessageProcessor):
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        if not eh_horario_comercial():
            return ProcessingResult(should_stop=True, reason="fora_horario")
        return ProcessingResult(should_stop=False)

# Registrar
pipeline.add_pre_processor(BusinessHoursValidator())
```

**Como encontrar codigo deprecated:**

```bash
# Buscar logica inline em webhook.py
grep -A 10 "def webhook_" app/api/routes/webhook.py | grep "if\|for"

# Buscar arquivos grandes (candidatos a refactoring)
find app/ -name "*.py" -exec wc -l {} + | sort -rn | head -20
```

---

## 4. Tools do Slack

### Deprecated (Sprint 1-46)

```python
# Import antigo (tools no mesmo arquivo)
from app.tools.slack_tools import (
    buscar_metricas,
    listar_medicos,
    criar_campanha
)

# Uso direto
resultado = await buscar_metricas(periodo="7d")
```

### Atual (Sprint 47+)

```python
# Import novo (tools organizadas por agente)
from app.tools.helena import HELENA_TOOLS
from app.tools.helena.agent import AgenteHelena

# Uso via agente Helena
helena = AgenteHelena(user_id="U123", channel_id="C456")
resposta = await helena.processar_mensagem("Quais as metricas dos ultimos 7 dias?")
```

**Por que mudou:**
- Tools do Slack foram refatoradas para agente Helena dedicado
- Separacao clara: tools de Julia (WhatsApp) vs tools de Helena (Slack Analytics)
- Helena tem session management, multi-turn conversation, SQL dinamico

**Estrutura atual:**

```
app/tools/
├── helena/                   # Agente Helena (Slack Analytics)
│   ├── __init__.py
│   ├── agent.py              # Logica do agente
│   ├── tools.py              # 5 tools pre-configuradas
│   ├── sql_validator.py      # Validacao SQL (SELECT only)
│   └── session_manager.py    # Session com TTL 30min
│
├── slack/                    # Tools genericas Slack
│   ├── __init__.py
│   ├── tools.py
│   └── types.py
│
├── vagas.py                  # Tools de vagas (Julia)
├── memoria.py                # Tools de memoria (Julia)
└── lembrete.py               # Tools de lembretes (Julia)
```

**Mapeamento de tools:**

| Deprecated | Atual (Helena) |
|------------|----------------|
| `buscar_metricas()` | Tool `metricas_sistema` |
| `listar_medicos()` | Tool `listar_medicos` |
| `buscar_conversas()` | Tool `buscar_conversas` |
| `gerar_relatorio()` | Tool `gerar_relatorio_customizado` + SQL dinamico |

**Como encontrar codigo deprecated:**

```bash
# Buscar imports antigos
grep -r "from app.tools.slack_tools import" app/

# Buscar uso direto de tools (sem agente)
grep -r "buscar_metricas\|listar_medicos" app/ --exclude-dir=helena
```

---

## 5. Timezone Handling

### Deprecated (Sprint 1-39)

```python
# Uso direto de datetime.now() ou datetime.utcnow()
from datetime import datetime

# ERRADO - usa timezone do servidor (UTC no Railway)
agora = datetime.now()
hora_atual = agora.hour  # Sera 3h a mais que Brasilia!

# ERRADO - deprecated em Python 3.12+
agora_utc = datetime.utcnow()
```

### Atual (Sprint 40+)

```python
# Uso de funcoes centralizadas de timezone
from app.core.timezone import agora_utc, agora_brasilia, iso_utc

# Para salvar no banco (sempre UTC)
supabase.table("eventos").insert({
    "created_at": iso_utc()  # ou agora_utc().isoformat()
})

# Para logica de horario comercial (Brasilia)
hora_atual = agora_brasilia().hour
if hora_atual < 8 or hora_atual >= 20:
    return "Fora do horario comercial"

# Para verificar dia da semana (seg-sex = 0-4 em Brasilia)
if agora_brasilia().weekday() > 4:
    return "Final de semana"
```

**Por que mudou:**
- Railway roda em UTC, mas logica de negocio eh em BRT (America/Sao_Paulo)
- `datetime.now()` sem timezone eh ambiguo
- `datetime.utcnow()` foi deprecated em Python 3.12
- Centralizacao em `app/core/timezone.py` evita bugs

**Funcoes disponiveis:**

| Funcao | Uso | Retorno |
|--------|-----|---------|
| `agora_utc()` | Timestamps para banco | datetime UTC |
| `agora_brasilia()` | Logica de negocio | datetime BRT |
| `para_brasilia(dt)` | Converter para BRT | datetime BRT |
| `para_utc(dt)` | Converter para UTC | datetime UTC |
| `iso_utc(dt=None)` | String ISO para banco | str |
| `formatar_data_brasilia(dt)` | Exibicao para usuario | str |

**Como encontrar codigo deprecated:**

```bash
# Buscar datetime.now()
grep -r "datetime.now()" app/ --include="*.py"

# Buscar datetime.utcnow()
grep -r "datetime.utcnow()" app/ --include="*.py"

# Buscar imports de datetime sem timezone
grep -r "from datetime import datetime$" app/ --include="*.py"
```

**Migracao automatica:**

```bash
# Adicionar import de timezone
# Antes: from datetime import datetime
# Depois: from datetime import datetime
#         from app.core.timezone import agora_utc, agora_brasilia

# Substituir usos (revisar manualmente)
# datetime.now() -> agora_brasilia()
# datetime.utcnow() -> agora_utc()
```

---

## 6. Modulos de Extracao (Sprint 52-53)

### Deprecated (Sprint 14, 51)

```python
# Extrator v1 (regex basico)
from app.services.grupos import extrair_vagas_texto

vagas = extrair_vagas_texto(mensagem)
```

### Atual (Sprint 52-53)

```python
# Extrator v2 (regex avancado + parser)
from app.services.grupos.extrator_v2 import extrair_vagas_v2
from app.services.grupos.extrator_v2.extrator_llm import extrair_com_llm

# v2: Regex + parser (rapido, estruturado)
resultado = await extrair_vagas_v2(
    texto=mensagem,
    mensagem_id=msg_id,
    grupo_id=grupo_id,
    data_referencia=date.today()
)

# v3: LLM unificado (lento, mais preciso)
resultado_llm = await extrair_com_llm(
    texto=mensagem,
    mensagem_id=msg_id
)
```

**Por que mudou:**
- v1: Regex simples, muitos falsos positivos
- v2: Parser de linhas + extratores especializados (hospitais, datas, valores)
- v3: LLM unificado para casos complexos

**Estrutura atual:**

```
app/services/grupos/extrator_v2/
├── __init__.py
├── pipeline.py              # Orquestrador v2
├── parser_mensagem.py       # Classifica linhas (LOCAL, DATA, VALOR)
├── extrator_hospitais.py    # Extrai hospitais
├── extrator_datas.py        # Extrai datas e periodos
├── extrator_valores.py      # Extrai valores
├── extrator_contatos.py     # Extrai contatos
├── gerador_vagas.py         # Gera vagas atomicas
└── extrator_llm.py          # Extrator v3 (LLM unificado)
```

**Quando usar cada versao:**

| Versao | Quando usar | Performance | Precisao |
|--------|-------------|-------------|----------|
| v2 (regex) | Mensagens bem estruturadas | ~100ms | 85% |
| v3 (LLM) | Mensagens complexas/ambiguas | ~2s | 95% |

**Como encontrar codigo deprecated:**

```bash
# Buscar imports antigos
grep -r "from app.services.grupos import extrair_vagas" app/

# Buscar uso de v1
grep -r "extrair_vagas_texto" app/
```

---

## 7. Notificacoes Slack (Helena)

### Deprecated (Sprint 1-46)

```python
# Notificacoes diretas via slack.py
from app.services.slack import enviar_notificacao

await enviar_notificacao(
    canal="#alerts",
    mensagem="Handoff escalado"
)
```

### Atual (Sprint 47+)

```python
# Dashboard substituiu notificacoes
# Helena nao envia notificacoes automaticas, apenas responde a queries

# Para alertas criticos, usar sistema de incidentes
from app.services.incidents import registrar_incidente

await registrar_incidente(
    from_status="healthy",
    to_status="critical",
    trigger_source="handoff_detector"
)
```

**Por que mudou:**
- Dashboard (Sprint 28-43) substituiu notificacoes Slack para operacao
- Helena (Sprint 47) focada em analytics sob demanda, nao notificacoes push
- Sistema de incidentes (Sprint 55) centraliza alertas criticos

**Fluxo atual:**
1. Evento critico detectado -> `registrar_incidente()`
2. Dashboard mostra incidente em real-time
3. Supervisor consulta Helena para detalhes: "O que causou o incidente?"

**Como encontrar codigo deprecated:**

```bash
# Buscar envio direto de notificacoes
grep -r "enviar_notificacao" app/

# Buscar referencias a canais Slack
grep -r "#alerts\|#handoffs" app/
```

---

## 8. Checklist de Migracao

Ao fazer refactoring de codigo antigo, verificar:

### Imports

- [ ] `get_supabase_client()` -> `supabase`
- [ ] `from app.services.campanha` -> `from app.services.campanhas`
- [ ] `from app.tools.slack_tools` -> `from app.tools.helena`
- [ ] `from datetime import datetime` -> `from app.core.timezone import agora_*`

### Padroes de Codigo

- [ ] Logica inline em webhook -> Pipeline processors
- [ ] Deteccao/validacao inline -> Processor dedicado
- [ ] `datetime.now()` -> `agora_brasilia()`
- [ ] `datetime.utcnow()` -> `agora_utc()`

### Estrutura de Modulos

- [ ] Modulo `campanha.py` -> Submodulo `campanhas/`
- [ ] Tools Slack diretas -> Agente Helena
- [ ] Extrator v1 -> Extrator v2 ou v3

### Notificacoes

- [ ] `enviar_notificacao()` Slack -> Sistema de incidentes
- [ ] Notificacoes push -> Dashboard + Helena on-demand

---

## 9. Ferramentas de Deteccao

### Grep Patterns

```bash
# Buscar todos os padroes deprecated
grep -r "get_supabase_client\|from app.services.campanha import\|datetime.now()\|datetime.utcnow()\|enviar_notificacao" app/ --include="*.py"
```

### Script de Validacao

Criar script `scripts/validate_patterns.py`:

```python
import os
import re
from pathlib import Path

DEPRECATED_PATTERNS = {
    r'get_supabase_client': 'Use: from app.services.supabase import supabase',
    r'from app\.services\.campanha import': 'Use: from app.services.campanhas import',
    r'datetime\.now\(\)': 'Use: from app.core.timezone import agora_brasilia',
    r'datetime\.utcnow\(\)': 'Use: from app.core.timezone import agora_utc',
    r'enviar_notificacao': 'Use: Sistema de incidentes ou Dashboard',
}

def validar_arquivo(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    issues = []
    for pattern, message in DEPRECATED_PATTERNS.items():
        if re.search(pattern, content):
            issues.append(f"{filepath}: {message}")

    return issues

# Rodar em app/
for filepath in Path('app').rglob('*.py'):
    issues = validar_arquivo(filepath)
    for issue in issues:
        print(issue)
```

**Uso:**

```bash
python scripts/validate_patterns.py
```

---

## 10. Pre-commit Hook

Adicionar validacao automatica em `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Validar padroes deprecated
echo "Validando padroes deprecated..."

# Buscar padroes
DEPRECATED=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$" | xargs grep -l "get_supabase_client\|from app.services.campanha import\|datetime.now()\|datetime.utcnow()" || true)

if [ -n "$DEPRECATED" ]; then
    echo "ERRO: Padroes deprecated encontrados:"
    echo "$DEPRECATED"
    echo ""
    echo "Consultar: docs/arquitetura/migration-guide.md"
    exit 1
fi

echo "OK: Sem padroes deprecated"
exit 0
```

**Ativar:**

```bash
chmod +x .git/hooks/pre-commit
```

---

## 11. Referencias

### Documentacao

- Convencoes de codigo: `app/CONVENTIONS.md`
- ADRs: `docs/adrs/` (decisoes arquiteturais)
- Visao geral: `docs/arquitetura/visao-geral.md`

### Sprints de Refactoring

| Sprint | Mudanca | Arquivo |
|--------|---------|---------|
| Sprint 10 | Pipeline plugavel | ADR-003 |
| Sprint 30 | Refatoracao arquitetural | - |
| Sprint 35 | Campanhas submodulo | - |
| Sprint 40 | Timezone centralizado | - |
| Sprint 44 | Correcoes arquiteturais | - |
| Sprint 47 | Helena agent | - |
| Sprint 52-53 | Extratores v2/v3 | - |

### Contato

Duvidas sobre migracao: Consultar equipe de engenharia ou abrir issue no GitHub.

---

**Documento:** migration-guide.md
**Versao:** 1.0
**Data:** 10/02/2026
**Proxima Review:** 30/04/2026
