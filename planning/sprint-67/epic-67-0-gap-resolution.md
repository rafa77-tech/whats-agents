# EPIC 67.0: Resolucao de Gaps do Roadmap

## Contexto

O roadmap original (`roadmap-meta-nivel-twilio.md`) tem 10 gaps identificados na analise pre-sprint. Alguns sao cobertos parcialmente pelos epics 67.1-67.4, mas precisam de tratamento explicito para garantir que nada caia entre as frestas.

Este epic e **pre-requisito** para os demais — deve ser executado primeiro ou em paralelo.

## Escopo

- **Incluido**: Todas as 10 lacunas do roadmap
- **Excluido**: Implementacao dos epics 67.1-67.4 (estao em seus proprios docs)

---

## Gap R1: Interactive tools nao integram com LLM

### Problema

O roadmap descreve `enviar_opcoes()` como funcao Python, mas Julia usa tool calling via Claude API. O fluxo real e:

```
LLM retorna tool_use → processar_tool_call() → handler → resultado → LLM continua
```

O arquivo `app/services/agente/generation.py` tem:
- `JULIA_TOOLS` (linha 49): lista hardcoded de 7 tools
- `processar_tool_call()` (linha 60): dispatch por nome com dict de handlers
- `_gerar_com_tools()` (linha 352): loop de tool calls com max 3 iteracoes

As novas tools interactive precisam ser adicionadas a AMBOS os lugares.

### Tarefa R1: Integrar interactive tools no agente

**Arquivos:**
| Acao | Arquivo | Linha |
|------|---------|-------|
| Modificar | `app/services/agente/generation.py` | 21-36 (imports), 49-57 (JULIA_TOOLS), 60-79 (handlers) |
| Criar | `app/tools/interactive_messages.py` | Novo (definicoes + handlers) |

**Implementacao:**

```python
# Em generation.py — adicionar imports
from app.tools.interactive_messages import (
    TOOL_ENVIAR_OPCOES,
    TOOL_ENVIAR_LISTA,
    TOOL_ENVIAR_CTA,
    handle_enviar_opcoes,
    handle_enviar_lista,
    handle_enviar_cta,
)

# Em JULIA_TOOLS — adicionar
JULIA_TOOLS = [
    # ... tools existentes ...
    TOOL_ENVIAR_OPCOES,
    TOOL_ENVIAR_LISTA,
    TOOL_ENVIAR_CTA,
]

# Em processar_tool_call() — adicionar ao dict handlers
handlers = {
    # ... handlers existentes ...
    "enviar_opcoes": handle_enviar_opcoes,
    "enviar_lista": handle_enviar_lista,
    "enviar_cta": handle_enviar_cta,
}
```

**Detalhe critico:** Os handlers de interactive tools tem comportamento DIFERENTE dos handlers normais. Tools normais retornam dados para o LLM formatar como texto. Tools interactive ENVIAM a mensagem diretamente (porque o payload e estruturado, nao texto). O handler deve:

1. Gerar payload interactive
2. Verificar se chip e Meta (via conversa context)
3. Enviar via `send_outbound_interactive()` ou fallback texto
4. Retornar resultado para o LLM (confirmacao de envio)

O LLM NAO gera texto adicional apos interactive — a mensagem ja foi enviada pelo handler.

### Testes

- [ ] `test_julia_tools_inclui_interactive` — 10 tools no total (7 + 3)
- [ ] `test_processar_tool_call_enviar_opcoes` — Handler chamado corretamente
- [ ] `test_processar_tool_call_enviar_lista` — Handler chamado corretamente
- [ ] `test_processar_tool_call_enviar_cta` — Handler chamado corretamente
- [ ] `test_capabilities_gate_filtra_interactive` — Modo restrito exclui interactive tools

### DoD

- [ ] 5 testes passando
- [ ] Nenhuma regressao nos testes de generation.py existentes

---

## Gap R2: delivery.py so envia texto

### Problema

`enviar_resposta()` em `app/services/agente/delivery.py` recebe `str` e envia via `send_outbound_message()`. Nao ha caminho para payloads interactive.

O `send_outbound_message()` em `app/services/outbound/sender.py` tambem aceita apenas `texto: str`.

### Tarefa R2: Novo caminho de envio interactive

**Arquivos:**
| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/outbound/sender.py` |
| Modificar | `app/services/outbound/__init__.py` |
| Modificar | `app/services/outbound/multi_chip.py` |
| Modificar | `app/services/chips/sender.py` |

**Implementacao:**

Nova funcao em `app/services/outbound/sender.py`:

```python
async def send_outbound_interactive(
    telefone: str,
    interactive_payload: dict,
    fallback_text: str,
    ctx: OutboundContext,
) -> OutboundResult:
    """
    Envia mensagem interativa via outbound.

    Mesmo fluxo do send_outbound_message mas com payload interactive:
    1. DEV allowlist check
    2. Deduplicacao (hash do fallback_text)
    3. Guardrails check
    4. Multi-chip: enviar interactive se Meta, fallback_text se outros
    5. Finalizacao

    Args:
        telefone: Numero destino
        interactive_payload: Payload no formato Meta Graph API
        fallback_text: Texto alternativo para chips nao-Meta
        ctx: Contexto outbound
    """
```

Nova funcao em `app/services/outbound/multi_chip.py`:

```python
async def _enviar_interactive_via_multi_chip(
    telefone: str,
    interactive_payload: dict,
    fallback_text: str,
    ctx: OutboundContext,
) -> dict:
    """
    Envia interactive via chip selecionado.

    Se chip Meta: provider.send_interactive(payload)
    Se chip Evolution/Z-API: provider.send_text(fallback_text)
    """
```

Nova funcao em `app/services/chips/sender.py`:

```python
async def enviar_interactive_via_chip(
    chip_id: str,
    telefone: str,
    interactive_payload: dict,
    fallback_text: str,
) -> dict:
    """
    Envia interactive via chip especifico.

    Verifica janela 24h antes de enviar interactive (Meta only).
    """
```

**Re-export em `app/services/outbound/__init__.py`:**
```python
from app.services.outbound.sender import send_outbound_interactive
```

### Testes

- [ ] `test_send_outbound_interactive_dev_allowlist` — Bloqueado se fora da allowlist
- [ ] `test_send_outbound_interactive_guardrails` — Guardrails aplicados
- [ ] `test_send_outbound_interactive_dedup` — Deduplicacao funciona
- [ ] `test_send_outbound_interactive_meta_sucesso` — Envia interactive
- [ ] `test_send_outbound_interactive_evolution_fallback` — Envia texto
- [ ] `test_send_outbound_interactive_finalizacao` — last_touch atualizado

### DoD

- [ ] 6 testes passando
- [ ] `send_outbound_interactive` exportado no `__init__.py`
- [ ] Guardrails identicos ao `send_outbound_message`

---

## Gap R3: Outbound guardrails nao validam interactive

### Problema

`check_outbound_guardrails()` em `app/services/guardrails/check.py` nao diferencia texto de interactive. As regras (opt-out, cooling_off, quiet_hours, etc) se aplicam igualmente. Mas:

1. **Deduplicacao**: O hash e calculado sobre `texto`. Para interactive, deve usar `fallback_text` (evita hash diferente para mesmo conteudo logico).
2. **Rate limit**: Interactive conta como 1 mensagem (ok, sem mudanca).
3. **Content validation**: `ValidateOutputProcessor` valida texto. Interactive bypassa essa validacao — precisa de validacao propria (limites WhatsApp: 3 buttons max, 20 chars, etc).

### Tarefa R3: Validacao de payloads interactive

**Arquivo:** `app/tools/interactive_messages.py` (validacao no handler, antes de enviar)

**Implementacao:**

```python
def validar_payload_interactive(tipo: str, payload: dict) -> tuple[bool, str]:
    """
    Valida payload interactive contra limites do WhatsApp.

    Limites:
    - Reply buttons: max 3, cada titulo max 20 chars
    - List: max 10 itens, button_text max 20 chars, item titulo max 24 chars, descricao max 72 chars
    - CTA URL: max 2000 chars URL, label max 20 chars

    Returns:
        (valido, mensagem_erro)
    """

def sanitizar_payload_interactive(tipo: str, payload: dict) -> dict:
    """
    Trunca campos que excedem limites ao inves de rejeitar.

    Ex: titulo com 25 chars → trunca para 24 + "..."
    """
```

### Testes

- [ ] `test_validar_buttons_3_ok` — 3 buttons valido
- [ ] `test_validar_buttons_4_erro` — 4 buttons invalido
- [ ] `test_validar_button_titulo_longo` — >20 chars invalido
- [ ] `test_validar_lista_10_itens_ok` — 10 itens valido
- [ ] `test_validar_lista_11_itens_erro` — 11 itens invalido
- [ ] `test_validar_cta_url_sem_https` — URL sem https invalido
- [ ] `test_sanitizar_trunca_titulo` — Titulo truncado com "..."
- [ ] `test_sanitizar_trunca_descricao` — Descricao truncada

### DoD

- [ ] 8 testes passando
- [ ] Validacao aplicada ANTES de enviar
- [ ] Sanitizacao como fallback (trunca ao inves de falhar)

---

## Gap R4: Quality Monitor sem tabela de historico

### Status: ✅ Coberto no Epic 67.1 Tarefa 1

A migration `meta_quality_history` ja esta especificada com schema completo, indices, e FK para julia_chips.

**Nenhuma acao adicional necessaria.**

---

## Gap R5: Template Analytics sem periodicidade definida

### Status: ✅ Coberto no Epic 67.3 Tarefa 4

Definido como worker com cron `0 6 * * *` (diario as 6h), coleta dados do dia anterior.

**Nenhuma acao adicional necessaria.**

---

## Gap R6: Pricing schema desatualizado

### Status: ✅ Coberto no Epic 67.4 Tarefa 1-2

Schema `meta_conversation_costs` com model per-message (Jul/2025+) e pricing table:
- Marketing: $0.0625
- Utility: $0.0350
- Authentication: $0.0315
- Service: GRATUITO

**Acao adicional:** Criar configuracao para atualizar precos sem deploy.

### Tarefa R6: Pricing configuravel

**Arquivo:** `app/core/config.py`

**Implementacao:**

```python
# Meta pricing (USD) - Jul 2025+ per-message model
# Atualizar aqui quando Meta mudar precos
META_PRICING_MARKETING_USD: float = 0.0625
META_PRICING_UTILITY_USD: float = 0.0350
META_PRICING_AUTHENTICATION_USD: float = 0.0315
```

**Modificar `app/services/meta/conversation_analytics.py`:**

Usar `settings.META_PRICING_*` ao inves de constantes hardcoded.

### Testes

- [ ] `test_pricing_usa_settings` — Custo calculado a partir de settings
- [ ] `test_pricing_customizado` — Settings override funciona

### DoD

- [ ] 2 testes passando
- [ ] Precos configuraveis via env vars

---

## Gap R7: response_formatter.py sem formato interactive

### Status: ✅ Coberto no Epic 67.2 Tarefa 4

`VagasResponseFormatter` tera `formatar_vagas_interactive_list()` e `formatar_vagas_interactive_buttons()`.

**Acao adicional:** Garantir que o formato gerado e compativel com os payloads do Meta Graph API.

### Tarefa R7: Compatibilidade de formato

O `formatar_vagas_interactive_list()` deve gerar output que pode ser passado diretamente ao `TOOL_ENVIAR_LISTA`:

```python
# Output esperado do formatter:
{
    "texto": "Dr Carlos, separei as melhores vagas pra vc:",
    "button_text": "Ver vagas",
    "secoes": [
        {
            "titulo": "Sao Luiz",
            "itens": [
                {"titulo": "UTI Cardio 19h-7h", "descricao": "R$ 2.500 - dia 15/03"},
                {"titulo": "PS Geral 7h-19h", "descricao": "R$ 1.800 - dia 16/03"},
            ]
        }
    ]
}
```

Este formato e o input_schema do `TOOL_ENVIAR_LISTA`, nao o formato Graph API. A conversao para Graph API acontece dentro do handler da tool.

### Testes

- [ ] `test_formato_lista_compativel_com_tool` — Output do formatter e input valido da tool
- [ ] `test_formato_buttons_compativel_com_tool` — Idem para buttons

### DoD

- [ ] 2 testes passando
- [ ] Contrato claro: formatter → tool input → Graph API payload

---

## Gap R8: Webhook para interactive responses

### Status: ✅ Ja funciona — nenhuma acao

O `webhook_meta.py` ja trata `button_reply` e `list_reply` (linhas 269-275, 308-314). Quando o medico toca um botao ou item de lista, o webhook extrai o titulo e passa para o pipeline como texto normal.

**Verificacao:**

```python
# Ja implementado em webhook_meta.py:
elif msg_type == "interactive":
    interactive = message.get("interactive", {})
    itype = interactive.get("type")
    if itype == "button_reply":
        return interactive.get("button_reply", {}).get("title", "")
    elif itype == "list_reply":
        return interactive.get("list_reply", {}).get("title", "")
```

**Nenhuma acao necessaria.**

---

## Gap R9: Sem rollback strategy para quality auto-degrade

### Status: ✅ Coberto no Epic 67.1 Tarefa 2

`MetaQualityMonitor` tem `_auto_recovery_chip()`:
- GREEN (vindo de YELLOW): restaura trust_score
- GREEN (vindo de RED): reativa chip mas com trust_score baixo (cautela)

**Acao adicional:** Definir regras de recovery mais detalhadas.

### Tarefa R9: Regras de auto-recovery

**Arquivo:** `app/services/meta/quality_monitor.py`

**Regras:**

| Transicao | Acao | Trust Score |
|-----------|------|-------------|
| RED → YELLOW | Manter desativado (nao confiavel ainda) | 0 |
| RED → GREEN | Reativar com trust baixo | 30 |
| YELLOW → GREEN | Restaurar trust normal | trust anterior * 0.8 |
| GREEN → GREEN | Nada (polling normal) | Sem mudanca |
| Novo chip sem historico | Iniciar como GREEN | 50 (default) |

**Protecao anti-flap:** Se chip oscilou >3 vezes em 24h (ex: GREEN→YELLOW→GREEN→YELLOW), desativar por 6h (cooldown).

### Testes

- [ ] `test_recovery_red_para_green` — Reativa com trust 30
- [ ] `test_recovery_yellow_para_green` — Restaura trust * 0.8
- [ ] `test_red_para_yellow_mantem_desativado` — Nao reativa
- [ ] `test_anti_flap_3_oscilacoes` — Desativa por 6h
- [ ] `test_anti_flap_2_oscilacoes_ok` — Sem cooldown

### DoD

- [ ] 5 testes passando
- [ ] Anti-flap implementado
- [ ] Log de todas as transicoes

---

## Gap R10: CTA URL + janela 24h

### Problema

CTA URL buttons sao mensagens interactive (free-form). So funcionam dentro da janela 24h. Se Julia chamar `enviar_cta` fora da janela, o Meta retorna erro 131026. O roadmap nao menciona essa restricao.

### Tarefa R10: Window check em todas as tools interactive

**Arquivo:** `app/tools/interactive_messages.py`

**Implementacao:**

Todos os handlers devem:

```python
async def handle_enviar_opcoes(input_data: dict, medico: dict, conversa: dict) -> dict:
    telefone = medico.get("telefone")
    chip_id = conversa.get("chip_id")
    provider = conversa.get("provider", "evolution")

    # Se Meta, verificar janela 24h
    if provider == "meta" and chip_id:
        from app.services.meta.window_tracker import window_tracker
        na_janela = await window_tracker.esta_na_janela(chip_id, telefone)
        if not na_janela:
            # Fallback: enviar como texto
            fallback = _gerar_fallback_texto_opcoes(input_data)
            # Tentar enviar como template se disponivel, senao texto
            return {
                "success": False,
                "error": "fora_janela_24h",
                "fallback_sugerido": fallback,
                "instrucao": "Voce esta fora da janela de 24h. Envie a mensagem como texto normal ao inves de botoes.",
            }

    # ... resto do handler
```

**Detalhe:** O retorno com `instrucao` faz o LLM gerar texto normal ao inves de falhar silenciosamente.

### Testes

- [ ] `test_enviar_opcoes_meta_fora_janela` — Retorna fallback + instrucao
- [ ] `test_enviar_lista_meta_fora_janela` — Retorna fallback + instrucao
- [ ] `test_enviar_cta_meta_fora_janela` — Retorna fallback + instrucao
- [ ] `test_enviar_opcoes_evolution_ignora_janela` — Evolution nao checa janela
- [ ] `test_fallback_texto_opcoes_formatado` — "1. Opcao A\n2. Opcao B"
- [ ] `test_fallback_texto_lista_formatado` — Secoes com itens numerados
- [ ] `test_instrucao_faz_llm_gerar_texto` — LLM recebe instrucao e gera texto

### DoD

- [ ] 7 testes passando
- [ ] Nenhum interactive enviado fora da janela
- [ ] Fallback graceful com instrucao para LLM

---

## Resumo de Testes por Gap

| Gap | Testes | Arquivo |
|-----|--------|---------|
| R1 | 5 | `tests/services/agente/test_generation_interactive.py` |
| R2 | 6 | `tests/services/outbound/test_interactive_outbound.py` |
| R3 | 8 | `tests/tools/test_interactive_validation.py` |
| R4 | 0 | ✅ Coberto em 67.1 |
| R5 | 0 | ✅ Coberto em 67.3 |
| R6 | 2 | `tests/services/meta/test_pricing_config.py` |
| R7 | 2 | `tests/tools/test_interactive_formatter_compat.py` |
| R8 | 0 | ✅ Ja funciona |
| R9 | 5 | `tests/services/meta/test_quality_recovery.py` |
| R10 | 7 | `tests/tools/test_interactive_window.py` |
| **Total** | **35** | |

---

## Dependencias

```
R3 (validacao) ──┐
R10 (janela) ────┤
R1 (LLM) ───────┼──→ Epic 67.2 (Interactive Messages)
R2 (delivery) ───┤
R7 (formatter) ──┘

R6 (pricing) ────→ Epic 67.4 (Conversation Analytics)
R9 (recovery) ───→ Epic 67.1 (Quality Monitor)

R4, R5, R8 ──────→ Nenhuma acao
```

## Ordem de Execucao

1. **R6** (pricing config) — Rapido, sem dependencias
2. **R9** (auto-recovery) — Independente, completa Epic 67.1
3. **R3** (validacao interactive) — Pre-requisito para R1/R2/R10
4. **R10** (window check) — Depende de R3 (validacao)
5. **R1** (LLM integration) — Depende de R3/R10 (handlers prontos)
6. **R2** (delivery pipeline) — Depende de R1 (handlers chamam delivery)
7. **R7** (formatter compat) — Depende de R1 (formato definido)
