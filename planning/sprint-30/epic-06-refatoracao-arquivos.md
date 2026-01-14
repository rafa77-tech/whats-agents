# Epic 06: Refatoracao de Arquivos Grandes

## Severidade: BAIXO

## Objetivo

Dividir arquivos com mais de 500 linhas em modulos menores e mais coesos, facilitando manutencao e navegacao.

## Problema Atual

### Arquivos Identificados

| Arquivo | Linhas | Funcoes/Classes |
|---------|--------|-----------------|
| `app/services/agente.py` | 982 | 9 funcoes principais |
| `app/api/routes/health.py` | 917 | Multiplos endpoints |
| `app/services/whatsapp.py` | 625 | Cliente + helpers |

### Consequencias

1. **Navegacao dificil:** Encontrar funcao especifica eh trabalhoso
2. **Conflitos de merge:** Multiplos devs editando mesmo arquivo
3. **Testes lentos:** Importar arquivo grande carrega tudo
4. **Cognitive load:** Dificil entender responsabilidades

---

## Stories

### S30.E6.1: Dividir `agente.py`

**Objetivo:** Separar agente.py (982 linhas) em modulos com responsabilidades claras.

**Estrutura Proposta:**

```
app/services/agente/
├── __init__.py              # Re-exports principais
├── core.py                  # gerar_resposta_julia, processar_mensagem_completo
├── tools.py                 # processar_tool_call
├── events.py                # _emitir_offer_events, _emitir_fallback_event
├── sender.py                # enviar_mensagens_sequencia, enviar_resposta
└── helpers.py               # _resposta_parece_incompleta, ProcessamentoResult
```

**Tarefas:**

1. Criar diretorio:
   ```bash
   mkdir -p app/services/agente
   ```

2. Criar `app/services/agente/helpers.py`:
   ```python
   """
   Helpers e tipos auxiliares do agente.

   Sprint 30 - S30.E6.1
   """
   from dataclasses import dataclass
   from typing import Optional, List


   def _resposta_parece_incompleta(texto: str, stop_reason: str = None) -> bool:
       """Verifica se resposta parece incompleta."""
       # Mover implementacao de agente.py linhas 79-120
       pass


   @dataclass
   class ProcessamentoResult:
       """Resultado do processamento de mensagem."""
       # Mover de agente.py linhas 517-522
       success: bool
       response: Optional[str] = None
       error: Optional[str] = None
       tool_calls: List[str] = None
   ```

3. Criar `app/services/agente/tools.py`:
   ```python
   """
   Processamento de tool calls do agente.

   Sprint 30 - S30.E6.1
   """
   import logging
   from typing import Any, Dict

   logger = logging.getLogger(__name__)


   async def processar_tool_call(
       tool_name: str,
       tool_input: Dict[str, Any],
       context: dict
   ) -> Any:
       """Processa chamada de tool."""
       # Mover de agente.py linhas 123-165
       pass
   ```

4. Criar `app/services/agente/events.py`:
   ```python
   """
   Emissao de eventos de negocio do agente.

   Sprint 30 - S30.E6.1
   """
   import logging
   from typing import Optional

   logger = logging.getLogger(__name__)


   async def emitir_offer_events(
       medico_id: str,
       vaga: dict,
       event_type: str
   ) -> None:
       """Emite eventos relacionados a ofertas."""
       # Mover de agente.py linhas 524-588
       pass


   async def emitir_fallback_event(
       telefone: str,
       function_name: str
   ) -> None:
       """Emite evento de fallback."""
       # Mover de agente.py linhas 830-858
       pass
   ```

5. Criar `app/services/agente/sender.py`:
   ```python
   """
   Envio de mensagens pelo agente.

   Sprint 30 - S30.E6.1
   """
   import logging
   from typing import List, Optional

   logger = logging.getLogger(__name__)


   async def enviar_mensagens_sequencia(
       telefone: str,
       mensagens: List[str],
       instance_name: Optional[str] = None
   ) -> bool:
       """Envia sequencia de mensagens."""
       # Mover de agente.py linhas 861-930
       pass


   async def enviar_resposta(
       telefone: str,
       resposta: str,
       instance_name: Optional[str] = None
   ) -> bool:
       """Envia resposta unica."""
       # Mover de agente.py linhas 933-980
       pass
   ```

6. Criar `app/services/agente/core.py`:
   ```python
   """
   Core do agente Julia - geracao de respostas.

   Sprint 30 - S30.E6.1
   """
   import logging
   from typing import Optional

   from .helpers import ProcessamentoResult, _resposta_parece_incompleta
   from .tools import processar_tool_call
   from .events import emitir_offer_events

   logger = logging.getLogger(__name__)


   async def gerar_resposta_julia(
       # ... parametros
   ) -> str:
       """Gera resposta usando LLM."""
       # Mover de agente.py linhas 168-514
       pass


   async def processar_mensagem_completo(
       # ... parametros
   ) -> ProcessamentoResult:
       """Processa mensagem completa com pipeline."""
       # Mover de agente.py linhas 591-827
       pass
   ```

7. Criar `app/services/agente/__init__.py`:
   ```python
   """
   Agente Julia - Modulo principal.

   Sprint 30 - S30.E6.1

   Este modulo foi dividido de um unico arquivo (982 linhas)
   em submodulos com responsabilidades claras.

   Uso:
       from app.services.agente import (
           gerar_resposta_julia,
           processar_mensagem_completo,
           enviar_resposta,
       )
   """
   from .core import gerar_resposta_julia, processar_mensagem_completo
   from .tools import processar_tool_call
   from .events import emitir_offer_events, emitir_fallback_event
   from .sender import enviar_mensagens_sequencia, enviar_resposta
   from .helpers import ProcessamentoResult

   __all__ = [
       # Core
       "gerar_resposta_julia",
       "processar_mensagem_completo",
       # Tools
       "processar_tool_call",
       # Events
       "emitir_offer_events",
       "emitir_fallback_event",
       # Sender
       "enviar_mensagens_sequencia",
       "enviar_resposta",
       # Types
       "ProcessamentoResult",
   ]
   ```

8. Atualizar imports nos consumidores:
   ```bash
   # Encontrar consumidores
   grep -rn "from app.services.agente import\|from app.services import agente" app/
   ```

9. Manter arquivo original renomeado temporariamente:
   ```bash
   mv app/services/agente.py app/services/agente_old.py
   # Testar, e se tudo OK:
   rm app/services/agente_old.py
   ```

10. Rodar testes:
    ```bash
    uv run pytest tests/ -v
    ```

**Como Testar:**

```bash
# 1. Verificar imports
python -c "from app.services.agente import gerar_resposta_julia, processar_mensagem_completo; print('OK')"

# 2. Rodar testes do agente
uv run pytest tests/services/test_agente.py -v

# 3. Rodar todos os testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] Diretorio `app/services/agente/` criado
- [ ] 6 submodulos criados (init, core, tools, events, sender, helpers)
- [ ] Arquivo original removido
- [ ] Todos os imports atualizados
- [ ] Todos os testes passando
- [ ] Commit: `refactor(agente): divide em submodulos`

---

### S30.E6.2: Dividir `health.py`

**Objetivo:** Separar health.py (917 linhas) em modulos por tipo de check.

**Estrutura Proposta:**

```
app/api/routes/health/
├── __init__.py              # Router principal + re-exports
├── basic.py                 # /, /health, /ping
├── deep.py                  # /health/deep - checks detalhados
├── jobs.py                  # /health/jobs - verificacao de jobs
└── dependencies.py          # /health/dependencies - servicos externos
```

**Tarefas:**

1. Criar diretorio:
   ```bash
   mkdir -p app/api/routes/health
   ```

2. Criar `app/api/routes/health/basic.py`:
   ```python
   """
   Health checks basicos.

   Sprint 30 - S30.E6.2
   """
   from fastapi import APIRouter

   router = APIRouter()


   @router.get("/ping")
   async def ping():
       """Ping simples."""
       return {"status": "pong"}


   @router.get("/health")
   async def health():
       """Health check basico."""
       # Mover implementacao
       pass
   ```

3. Criar `app/api/routes/health/deep.py`:
   ```python
   """
   Health checks profundos.

   Sprint 30 - S30.E6.2
   """
   from fastapi import APIRouter

   router = APIRouter()


   @router.get("/health/deep")
   async def deep_health():
       """Health check profundo com todas as verificacoes."""
       # Mover implementacao (maior parte do arquivo)
       pass
   ```

4. Criar `app/api/routes/health/jobs.py`:
   ```python
   """
   Health checks de jobs/workers.

   Sprint 30 - S30.E6.2
   """
   from fastapi import APIRouter

   router = APIRouter()


   @router.get("/health/jobs")
   async def jobs_health():
       """Verifica status dos jobs agendados."""
       pass
   ```

5. Criar `app/api/routes/health/__init__.py`:
   ```python
   """
   Health checks - Router principal.

   Sprint 30 - S30.E6.2
   """
   from fastapi import APIRouter

   from .basic import router as basic_router
   from .deep import router as deep_router
   from .jobs import router as jobs_router

   router = APIRouter(prefix="/health", tags=["Health"])

   # Incluir sub-routers
   router.include_router(basic_router)
   router.include_router(deep_router)
   router.include_router(jobs_router)
   ```

6. Atualizar `main.py`:
   ```python
   # DE:
   from app.api.routes import health
   app.include_router(health.router)

   # PARA: (mesmo import, pois __init__.py exporta router)
   from app.api.routes import health
   app.include_router(health.router)
   ```

7. Rodar testes:
   ```bash
   uv run pytest tests/api/test_health.py -v
   ```

**DoD:**
- [ ] Diretorio `app/api/routes/health/` criado
- [ ] 4 submodulos criados
- [ ] Router principal configurado
- [ ] Arquivo original removido
- [ ] Todos os testes passando
- [ ] Commit: `refactor(health): divide em submodulos`

---

### S30.E6.3: Dividir `whatsapp.py`

**Objetivo:** Separar whatsapp.py (625 linhas) em cliente e helpers.

**Estrutura Proposta:**

```
app/services/whatsapp/
├── __init__.py              # Re-exports
├── client.py                # EvolutionClient classe principal
├── sender.py                # Funcoes de envio de mensagem
├── presence.py              # Funcoes de presenca (typing, online)
└── helpers.py               # Formatacao, validacao de telefone
```

**Tarefas:**

1. Criar estrutura similar as anteriores

2. Separar por responsabilidade:
   - `client.py`: Classe EvolutionClient com configuracao
   - `sender.py`: `enviar_mensagem`, `enviar_mensagem_com_retry`
   - `presence.py`: `enviar_presence`, `marcar_como_lida`
   - `helpers.py`: `formatar_telefone`, validacoes

3. Atualizar imports

4. Rodar testes

**DoD:**
- [ ] Diretorio `app/services/whatsapp/` criado
- [ ] Submodulos criados
- [ ] Todos os imports atualizados
- [ ] Todos os testes passando
- [ ] Commit: `refactor(whatsapp): divide em submodulos`

---

### S30.E6.4: Atualizar Imports nos Consumidores

**Objetivo:** Garantir que todos os imports foram atualizados.

**Tarefas:**

1. Buscar imports antigos:
   ```bash
   # Agente
   grep -rn "from app.services.agente import" app/ tests/

   # Health (se path mudou)
   grep -rn "from app.api.routes.health import" app/

   # WhatsApp
   grep -rn "from app.services.whatsapp import" app/ tests/
   ```

2. Verificar que todos funcionam:
   ```bash
   python -c "
   from app.services.agente import gerar_resposta_julia
   from app.services.whatsapp import enviar_mensagem
   print('Imports OK')
   "
   ```

3. Rodar suite completa de testes:
   ```bash
   uv run pytest tests/ -v
   ```

**DoD:**
- [ ] Todos os imports funcionando
- [ ] Zero erros de import
- [ ] Suite completa passando
- [ ] Commit: `refactor: atualiza imports apos split de arquivos`

---

## Checklist do Epic

- [ ] **S30.E6.1** - `agente.py` dividido
- [ ] **S30.E6.2** - `health.py` dividido
- [ ] **S30.E6.3** - `whatsapp.py` dividido
- [ ] **S30.E6.4** - Imports atualizados
- [ ] Nenhum arquivo com mais de 500 linhas (exceto se justificado)
- [ ] Todos os testes passando

---

## Ordem de Execucao

```
S30.E6.1 (agente.py)
    │
    ▼
S30.E6.2 (health.py)
    │
    ▼
S30.E6.3 (whatsapp.py)
    │
    ▼
S30.E6.4 (imports)
```

**Nota:** Podem ser feitas em paralelo por devs diferentes, mas E6.4 deve ser feita por ultimo.

---

## Metricas

| Arquivo Original | Linhas | Apos Split | Maior Submodulo |
|------------------|--------|------------|-----------------|
| `agente.py` | 982 | 6 arquivos | ~350 (core.py) |
| `health.py` | 917 | 4 arquivos | ~400 (deep.py) |
| `whatsapp.py` | 625 | 4 arquivos | ~250 (client.py) |

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E6.1 | Alta | 3h |
| S30.E6.2 | Media | 2h |
| S30.E6.3 | Media | 1.5h |
| S30.E6.4 | Media | 1h |
| **Total** | | **~7.5h** |
