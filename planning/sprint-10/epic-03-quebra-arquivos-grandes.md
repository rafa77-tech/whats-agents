# Epic 03: Quebra de Arquivos Grandes

## Objetivo

Quebrar arquivos com mais de 500 linhas em modulos menores e focados, respeitando Single Responsibility Principle.

## Arquivos Alvo

| Arquivo | Linhas | Problema |
|---------|--------|----------|
| `routes/jobs.py` | 623 | 14 endpoints com logica de negocio inline |
| `services/vaga.py` | 498 | Cache + preferencias + queries misturados |
| `services/relatorio.py` | 527 | 10 funcoes de reports sem organizacao |
| `services/handoff.py` | 499 | Logica de transicao + notificacao + banco |

---

## Stories

### S10.E3.1: Refatorar routes/jobs.py

**Objetivo:** Extrair logica de negocio dos endpoints para services dedicados.

**Problema:** Endpoints com 50+ linhas de logica que deveria estar em services.

**Exemplo do Problema:**
```python
# routes/jobs.py - endpoint com logica de negocio inline
@router.post("/primeira-mensagem")
async def primeira_mensagem(request: PrimeiraMensagemRequest):
    # 60 linhas de:
    # - Validacao de horario
    # - Busca de medicos
    # - Geracao de mensagem
    # - Envio
    # - Registro de metricas
    # Tudo isso deveria estar em um service!
```

**Nova Estrutura:**

```
routes/jobs.py (~200 linhas)
    └── Apenas validacao de request e chamada ao service

services/jobs/
├── __init__.py
├── primeira_mensagem.py (~150 linhas)
├── campanhas.py (~150 linhas)
├── followups.py (~100 linhas)
└── scheduler.py (~100 linhas)
```

**Tarefas:**

1. Criar diretorio `app/services/jobs/`

2. Criar `primeira_mensagem.py`:
   ```python
   # app/services/jobs/primeira_mensagem.py
   """Service para envio de primeira mensagem."""

   from dataclasses import dataclass
   from typing import Optional
   from datetime import datetime

   @dataclass
   class ResultadoPrimeiraMensagem:
       sucesso: bool
       medico_id: Optional[str] = None
       mensagem_enviada: Optional[str] = None
       erro: Optional[str] = None

   async def enviar_primeira_mensagem(
       telefone: str,
       tipo_abordagem: str = "discovery",
       vaga_id: Optional[str] = None
   ) -> ResultadoPrimeiraMensagem:
       """Envia primeira mensagem para um medico.

       Args:
           telefone: Numero do medico
           tipo_abordagem: discovery, oferta, reativacao, followup, custom
           vaga_id: ID da vaga (obrigatorio para tipo=oferta)

       Returns:
           ResultadoPrimeiraMensagem com status
       """
       # Validar horario comercial
       if not _horario_permitido():
           return ResultadoPrimeiraMensagem(
               sucesso=False,
               erro="Fora do horario comercial"
           )

       # Verificar rate limit
       if not await _verificar_rate_limit(telefone):
           return ResultadoPrimeiraMensagem(
               sucesso=False,
               erro="Rate limit atingido"
           )

       # Buscar/criar medico
       medico = await _obter_ou_criar_medico(telefone)

       # Gerar mensagem
       mensagem = await _gerar_mensagem(medico, tipo_abordagem, vaga_id)

       # Enviar
       await _enviar_whatsapp(medico.telefone, mensagem)

       # Registrar metricas
       await _registrar_envio(medico.id, tipo_abordagem)

       return ResultadoPrimeiraMensagem(
           sucesso=True,
           medico_id=medico.id,
           mensagem_enviada=mensagem
       )

   def _horario_permitido() -> bool:
       """Verifica se esta em horario comercial."""
       agora = datetime.now()
       return (
           agora.weekday() < 5 and  # Seg-Sex
           8 <= agora.hour < 20     # 8h-20h
       )
   ```

3. Refatorar endpoint para usar service:
   ```python
   # routes/jobs.py
   from app.services.jobs.primeira_mensagem import enviar_primeira_mensagem

   @router.post("/primeira-mensagem")
   async def primeira_mensagem(request: PrimeiraMensagemRequest):
       resultado = await enviar_primeira_mensagem(
           telefone=request.telefone,
           tipo_abordagem=request.tipo_abordagem,
           vaga_id=request.vaga_id
       )

       if not resultado.sucesso:
           raise HTTPException(400, resultado.erro)

       return {"status": "ok", "medico_id": resultado.medico_id}
   ```

4. Repetir para outros endpoints: `/campanhas`, `/followups`, `/processar-fila`

**Como Testar:**
```bash
# Testar endpoint
curl -X POST http://localhost:8000/jobs/primeira-mensagem \
  -H "Content-Type: application/json" \
  -d '{"telefone": "11999887766"}'

# Rodar testes
uv run pytest tests/ -v -k "jobs"
```

**DoD:**
- [x] `services/jobs/` criado com 4 arquivos
- [x] `primeira_mensagem.py` = 189 linhas (contem dataclasses e helpers)
- [x] `campanhas.py` = 76 linhas
- [x] `fila_mensagens.py` = 129 linhas (extrai logica de /processar-fila-mensagens)
- [x] `routes/jobs.py` = 247 linhas (era 623, reducao de 60%)
- [x] Logica de negocio extraida para services
- [x] Todos os testes passando
- [x] Commit: `refactor(jobs): extrai logica de negocio para services`

**Status:** 🟢 Concluida

---

### S10.E3.2: Refatorar services/vaga.py

**Objetivo:** Separar responsabilidades de cache, preferencias e queries.

**Problema:** Arquivo mistura 3 responsabilidades distintas:
- Cache de vagas (Redis)
- Sistema de preferencias do medico
- Queries ao banco

**Nova Estrutura:**

```
services/vagas/
├── __init__.py          # Re-exports
├── repository.py        # Queries ao banco (~150 linhas)
├── cache.py             # Cache Redis (~100 linhas)
├── preferencias.py      # Match de preferencias (~150 linhas)
└── service.py           # Orquestracao (~100 linhas)
```

**Tarefas:**

1. Criar `repository.py` com queries puras:
   ```python
   # app/services/vagas/repository.py
   """Queries de vagas no banco de dados."""

   from typing import Optional
   from app.services.supabase import supabase

   async def buscar_por_id(vaga_id: str) -> Optional[dict]:
       """Busca vaga pelo ID."""
       response = supabase.table("vagas").select(
           "*, hospitais(nome, endereco), especialidades(nome)"
       ).eq("id", vaga_id).execute()
       return response.data[0] if response.data else None

   async def listar_disponiveis(
       especialidade_id: Optional[str] = None,
       regiao: Optional[str] = None,
       limite: int = 10
   ) -> list[dict]:
       """Lista vagas disponiveis com filtros."""
       query = supabase.table("vagas").select(
           "*, hospitais(nome, endereco), especialidades(nome)"
       ).eq("status", "aberta")

       if especialidade_id:
           query = query.eq("especialidade_id", especialidade_id)
       if regiao:
           query = query.eq("regiao", regiao)

       response = query.limit(limite).execute()
       return response.data or []

   async def reservar(vaga_id: str, medico_id: str) -> bool:
       """Reserva vaga para um medico."""
       response = supabase.table("vagas").update({
           "status": "reservada",
           "medico_id": medico_id
       }).eq("id", vaga_id).eq("status", "aberta").execute()
       return len(response.data) > 0
   ```

2. Criar `cache.py` com logica de cache:
   ```python
   # app/services/vagas/cache.py
   """Cache de vagas usando Redis."""

   import json
   from typing import Optional
   from app.services.redis import redis_client
   from app.core.config import DatabaseConfig

   CACHE_PREFIX = "vagas:"

   async def get_cached(key: str) -> Optional[list[dict]]:
       """Busca vagas do cache."""
       cached = await redis_client.get(f"{CACHE_PREFIX}{key}")
       return json.loads(cached) if cached else None

   async def set_cached(key: str, vagas: list[dict]) -> None:
       """Salva vagas no cache."""
       await redis_client.setex(
           f"{CACHE_PREFIX}{key}",
           DatabaseConfig.CACHE_TTL_VAGAS,
           json.dumps(vagas)
       )

   async def invalidar(pattern: str = "*") -> None:
       """Invalida cache por pattern."""
       keys = await redis_client.keys(f"{CACHE_PREFIX}{pattern}")
       if keys:
           await redis_client.delete(*keys)
   ```

3. Criar `preferencias.py` com matching:
   ```python
   # app/services/vagas/preferencias.py
   """Sistema de matching de preferencias do medico."""

   from typing import Optional

   def calcular_score(vaga: dict, preferencias: dict) -> float:
       """Calcula score de compatibilidade vaga x preferencias.

       Args:
           vaga: Dados da vaga
           preferencias: Preferencias do medico

       Returns:
           Score de 0.0 a 1.0
       """
       score = 0.0
       peso_total = 0.0

       # Especialidade (peso 3)
       if vaga.get("especialidade_id") == preferencias.get("especialidade_id"):
           score += 3.0
       peso_total += 3.0

       # Regiao (peso 2)
       if vaga.get("regiao") in preferencias.get("regioes_aceitas", []):
           score += 2.0
       peso_total += 2.0

       # Valor (peso 2)
       valor_minimo = preferencias.get("valor_minimo", 0)
       if vaga.get("valor", 0) >= valor_minimo:
           score += 2.0
       peso_total += 2.0

       # Periodo (peso 1)
       if vaga.get("periodo") in preferencias.get("periodos_aceitos", []):
           score += 1.0
       peso_total += 1.0

       return score / peso_total if peso_total > 0 else 0.0

   def filtrar_por_preferencias(
       vagas: list[dict],
       preferencias: dict,
       score_minimo: float = 0.5
   ) -> list[dict]:
       """Filtra e ordena vagas por compatibilidade."""
       vagas_com_score = [
           (vaga, calcular_score(vaga, preferencias))
           for vaga in vagas
       ]

       return [
           vaga for vaga, score in sorted(
               vagas_com_score,
               key=lambda x: x[1],
               reverse=True
           )
           if score >= score_minimo
       ]
   ```

4. Criar `service.py` como orquestrador:
   ```python
   # app/services/vagas/service.py
   """Service principal de vagas."""

   from typing import Optional
   from . import repository, cache, preferencias

   async def buscar_vagas_para_medico(
       medico_id: str,
       usar_cache: bool = True
   ) -> list[dict]:
       """Busca vagas compativeis com o medico.

       Args:
           medico_id: ID do medico
           usar_cache: Se deve usar cache

       Returns:
           Lista de vagas ordenadas por compatibilidade
       """
       cache_key = f"medico:{medico_id}"

       if usar_cache:
           cached = await cache.get_cached(cache_key)
           if cached:
               return cached

       # Buscar preferencias do medico
       prefs = await _buscar_preferencias(medico_id)

       # Buscar vagas disponiveis
       vagas = await repository.listar_disponiveis(
           especialidade_id=prefs.get("especialidade_id")
       )

       # Filtrar por preferencias
       vagas_filtradas = preferencias.filtrar_por_preferencias(vagas, prefs)

       # Cachear resultado
       await cache.set_cached(cache_key, vagas_filtradas)

       return vagas_filtradas
   ```

5. Atualizar imports:
   ```python
   # DE:
   from app.services.vaga import buscar_vagas_compativeis

   # PARA:
   from app.services.vagas import buscar_vagas_para_medico
   ```

**Como Testar:**
```bash
uv run pytest tests/ -v -k "vaga"
```

**DoD:**
- [x] `services/vagas/` criado com 6 arquivos
- [x] `repository.py` = 129 linhas
- [x] `cache.py` = 51 linhas
- [x] `preferencias.py` = 75 linhas
- [x] `formatters.py` = 83 linhas
- [x] `service.py` = 175 linhas
- [x] Arquivo original com deprecation warning (55 linhas)
- [x] Todos os testes passando (411 passed)
- [x] Commit: `refactor(vagas): separa repository, cache e preferencias`

**Status:** 🟢 Concluida

---

### S10.E3.3: Refatorar services/relatorio.py

**Objetivo:** Organizar funcoes de relatorio por tipo.

**Problema:** 10 funcoes de relatorio sem organizacao, algumas com logica duplicada.

**Nova Estrutura:**

```
services/relatorios/
├── __init__.py           # Re-exports
├── diario.py             # Relatorios diarios (~150 linhas)
├── semanal.py            # Relatorios semanais (~150 linhas)
├── medicos.py            # Relatorios de medicos (~100 linhas)
└── formatters.py         # Formatacao comum (~100 linhas)
```

**Tarefas:**

1. Identificar e categorizar funcoes existentes:
   ```
   Diarios:
   - gerar_relatorio_diario()
   - resumo_dia()

   Semanais:
   - gerar_relatorio_semanal()
   - comparativo_semanas()

   Medicos:
   - relatorio_medico()
   - top_medicos_engajados()

   Formatters:
   - formatar_tabela()
   - formatar_grafico_texto()
   ```

2. Criar `diario.py`:
   ```python
   # app/services/relatorios/diario.py
   """Relatorios diarios."""

   from datetime import date, datetime, timedelta
   from typing import Optional
   from app.services.supabase import contar_interacoes_periodo

   async def gerar_relatorio_diario(data: Optional[date] = None) -> dict:
       """Gera relatorio do dia.

       Args:
           data: Data do relatorio (default: hoje)

       Returns:
           Dict com metricas do dia
       """
       data = data or date.today()
       inicio = datetime.combine(data, datetime.min.time())
       fim = datetime.combine(data, datetime.max.time())

       return {
           "data": data.isoformat(),
           "mensagens_enviadas": await contar_interacoes_periodo(
               inicio, fim, direcao="saida"
           ),
           "mensagens_recebidas": await contar_interacoes_periodo(
               inicio, fim, direcao="entrada"
           ),
           "taxa_resposta": await _calcular_taxa_resposta(inicio, fim),
           "handoffs": await _contar_handoffs(inicio, fim),
           "optouts": await _contar_optouts(inicio, fim),
       }
   ```

3. Criar `formatters.py` com formatacao comum:
   ```python
   # app/services/relatorios/formatters.py
   """Formatadores de relatorio."""

   def formatar_como_tabela(dados: list[dict], colunas: list[str]) -> str:
       """Formata dados como tabela texto."""
       if not dados:
           return "Sem dados"

       # Calcular larguras
       larguras = {col: len(col) for col in colunas}
       for row in dados:
           for col in colunas:
               larguras[col] = max(larguras[col], len(str(row.get(col, ""))))

       # Header
       header = " | ".join(col.ljust(larguras[col]) for col in colunas)
       separador = "-+-".join("-" * larguras[col] for col in colunas)

       # Rows
       rows = []
       for row in dados:
           rows.append(" | ".join(
               str(row.get(col, "")).ljust(larguras[col])
               for col in colunas
           ))

       return f"{header}\n{separador}\n" + "\n".join(rows)
   ```

4. Atualizar imports em arquivos que usam relatorio

**Como Testar:**
```bash
uv run pytest tests/ -v -k "relatorio"
```

**DoD:**
- [x] `services/relatorios/` criado com 3 arquivos (diario, semanal, periodo)
- [x] `diario.py` = 136 linhas
- [x] `semanal.py` = 134 linhas
- [x] `periodo.py` = 191 linhas
- [x] Deprecated wrapper mantido para compatibilidade (41 linhas)
- [x] Todos os testes passando (411 passed)
- [x] Commit: `refactor(relatorios): separa diario, semanal e periodo`

**Status:** 🟢 Concluida

---

### S10.E3.4: Refatorar services/handoff.py

**Objetivo:** Separar fluxo de handoff, notificacoes e persistencia.

**Problema:** Arquivo mistura logica de transicao IA<->Humano com notificacoes e queries.

**Nova Estrutura:**

```
services/handoff/
├── __init__.py           # Re-exports
├── flow.py               # Fluxo de transicao (~150 linhas)
├── detector.py           # Deteccao de triggers (~100 linhas)
├── notifier.py           # Notificacoes (~100 linhas)
└── repository.py         # Persistencia (~100 linhas)
```

**Tarefas:**

1. Criar `detector.py` com logica de deteccao:
   ```python
   # app/services/handoff/detector.py
   """Deteccao de triggers de handoff."""

   from dataclasses import dataclass
   from typing import Optional

   @dataclass
   class TriggerHandoff:
       detectado: bool
       motivo: Optional[str] = None
       confianca: float = 0.0

   PALAVRAS_HUMANO = [
       "falar com humano",
       "falar com pessoa",
       "atendente",
       "suporte",
       "gerente",
       "supervisor",
   ]

   PALAVRAS_IRRITACAO = [
       "ridiculo",
       "absurdo",
       "pessimo",
       "horrivel",
       "processo",
       "advogado",
   ]

   def detectar_pedido_humano(mensagem: str) -> TriggerHandoff:
       """Detecta pedido explicito de falar com humano."""
       mensagem_lower = mensagem.lower()

       for palavra in PALAVRAS_HUMANO:
           if palavra in mensagem_lower:
               return TriggerHandoff(
                   detectado=True,
                   motivo="pedido_explicito",
                   confianca=0.95
               )

       return TriggerHandoff(detectado=False)

   def detectar_irritacao(mensagem: str) -> TriggerHandoff:
       """Detecta sinais de irritacao que requerem humano."""
       mensagem_lower = mensagem.lower()

       score = sum(1 for p in PALAVRAS_IRRITACAO if p in mensagem_lower)

       if score >= 2:
           return TriggerHandoff(
               detectado=True,
               motivo="irritacao_detectada",
               confianca=min(0.5 + score * 0.15, 0.95)
           )

       return TriggerHandoff(detectado=False)
   ```

2. Criar `flow.py` com orquestracao:
   ```python
   # app/services/handoff/flow.py
   """Fluxo de transicao IA <-> Humano."""

   from typing import Optional
   from . import detector, notifier, repository

   async def iniciar_handoff(
       conversa_id: str,
       motivo: str,
       medico_id: Optional[str] = None
   ) -> bool:
       """Inicia transicao para humano.

       Args:
           conversa_id: ID da conversa
           motivo: Motivo do handoff
           medico_id: ID do medico (opcional)

       Returns:
           True se handoff iniciado com sucesso
       """
       # Criar registro
       handoff = await repository.criar_handoff(
           conversa_id=conversa_id,
           motivo=motivo,
           medico_id=medico_id
       )

       # Atualizar conversa
       await repository.atualizar_controle_conversa(
           conversa_id=conversa_id,
           controlled_by="human"
       )

       # Notificar gestor
       await notifier.notificar_novo_handoff(handoff)

       return True

   async def finalizar_handoff(
       handoff_id: str,
       resolucao: str
   ) -> bool:
       """Finaliza handoff e retorna controle para IA."""
       # Atualizar handoff
       await repository.atualizar_status_handoff(
           handoff_id=handoff_id,
           status="resolvido",
           resolucao=resolucao
       )

       # Buscar conversa
       handoff = await repository.buscar_handoff(handoff_id)

       # Retornar controle para IA
       await repository.atualizar_controle_conversa(
           conversa_id=handoff["conversa_id"],
           controlled_by="ai"
       )

       return True
   ```

3. Criar `notifier.py` e `repository.py`

4. Atualizar imports

**Como Testar:**
```bash
uv run pytest tests/ -v -k "handoff"
```

**DoD:**
- [x] `services/handoff/` criado com 3 arquivos (messages, flow, repository)
- [x] `messages.py` = 45 linhas (MENSAGENS_TRANSICAO e obter_mensagem_transicao)
- [x] `flow.py` = 303 linhas (iniciar_handoff, finalizar_handoff, resolver_handoff)
- [x] `repository.py` = 149 linhas (listar, metricas, verificar)
- [x] Deprecated wrapper mantido para compatibilidade (45 linhas)
- [x] Todos os testes passando (59 handoff tests)
- [x] Commit: `refactor(handoff): separa flow, messages e repository`

**Status:** 🟢 Concluida

---

## Resumo do Epic

| Story | Arquivo Original | Nova Estrutura | Arquivos |
|-------|------------------|----------------|----------|
| S10.E3.1 | `routes/jobs.py` (623) | `services/jobs/` | 4 arquivos |
| S10.E3.2 | `services/vaga.py` (498) | `services/vagas/` | 4 arquivos |
| S10.E3.3 | `services/relatorio.py` (527) | `services/relatorios/` | 4 arquivos |
| S10.E3.4 | `services/handoff.py` (499) | `services/handoff/` | 4 arquivos |

**Resultado Esperado:**
- Antes: 4 arquivos, 2147 linhas, max 623 linhas
- Depois: 16 arquivos, ~2000 linhas, max ~150 linhas
