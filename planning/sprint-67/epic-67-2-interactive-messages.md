# EPIC 67.2: Interactive Messages no Agente Julia

## Contexto

Sprint 66 implementou `MetaCloudProvider.send_interactive()` no nivel do provider — ou seja, o sistema PODE enviar buttons e lists. Mas Julia (o agente LLM) nao tem como DECIDIR enviar interactive. Hoje, todo output de Julia e texto puro que passa por `delivery.py` → `send_outbound_message()` → `enviar_via_chip()`. Precisamos de um caminho end-to-end: Julia decide → tool gera payload → delivery envia → provider executa.

## Escopo

- **Incluido**: 3 novas tools (enviar_opcoes, enviar_lista, enviar_cta), integracao com delivery pipeline, fallback para texto em chips nao-Meta, resposta a interactive replies
- **Excluido**: Carousel (Sprint 70+), WhatsApp Flows (Sprint 68), decisao automatica sem tool call (Julia sempre decide via tool)

## Decisoes Arquiteturais

### Como Julia decide usar interactive?

**Opcao escolhida:** Julia recebe as tools no prompt e DECIDE quando usar. Nao ha logica automatica — o LLM escolhe.

**Motivo:** Manter o padrao existente de tools (buscar_vagas, reservar_plantao). Julia ja sabe usar tools. Adicionar novas tools e natural.

### Como interactive passa pelo pipeline?

**Fluxo:**
```
LLM retorna tool_use "enviar_opcoes"
  → handler gera payload interactive
  → handler chama send_outbound_interactive() [nova funcao]
  → outbound verifica guardrails
  → chips/sender.py detecta interactive
  → se Meta: provider.send_interactive(payload)
  → se Evolution/Z-API: converte para texto + numeracao
```

### Janela 24h

Interactive messages SAO mensagens free-form. Funcionam APENAS dentro da janela 24h. Se fora da janela, fallback para template (se existir) ou erro.

---

## Tarefa 1: Tool Definitions & Handlers

### Objetivo

Criar 3 tools que Julia pode chamar para enviar mensagens interativas.

### Arquivo: `app/tools/interactive_messages.py`

### Implementacao

```python
"""
Tools de mensagens interativas para o agente Julia.

Sprint 67 - Epic 67.2.

Tools:
- enviar_opcoes: Reply buttons (max 3 opcoes)
- enviar_lista: List message (max 10 itens, agrupados em secoes)
- enviar_cta: CTA URL button (link clicavel)
"""

# --- Tool Definitions (para o LLM) ---

TOOL_ENVIAR_OPCOES = {
    "name": "enviar_opcoes",
    "description": """Envia opcoes como BOTOES INTERATIVOS no WhatsApp (max 3 opcoes).

QUANDO USAR:
- Medico precisa escolher entre 2-3 opcoes claras
- Confirmacao simples (sim/nao, aceito/recuso)
- Escolha de vaga quando ha poucas opcoes
- Qualquer decisao binaria ou ternaria

EXEMPLOS:
- Depois de mostrar 1 vaga: [Tenho interesse] [Preciso de detalhes] [Nao posso]
- Confirmacao: [Confirmo] [Preciso remarcar]
- Tipo de plantao: [Diurno] [Noturno] [Tanto faz]

IMPORTANTE:
- Maximo 3 opcoes (limitacao do WhatsApp)
- Cada opcao max 20 caracteres
- Se tiver mais de 3 opcoes, use enviar_lista
- Se chip nao suportar botoes, sera enviado como texto""",
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "Texto da mensagem acima dos botoes (obrigatorio)",
            },
            "opcoes": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
                "description": "Lista de opcoes (max 3, cada max 20 chars)",
            },
        },
        "required": ["texto", "opcoes"],
    },
}

TOOL_ENVIAR_LISTA = {
    "name": "enviar_lista",
    "description": """Envia LISTA INTERATIVA no WhatsApp (max 10 itens com secoes).

QUANDO USAR:
- Medico precisa escolher entre 4+ opcoes
- Mostrar vagas disponiveis (ideal: lista de plantoes)
- Menu de opcoes organizado por categoria
- Quando reply buttons nao cabem (>3 opcoes)

EXEMPLOS:
- Vagas por hospital: Secao "Sao Luiz" com 3 vagas, Secao "Einstein" com 2 vagas
- Especialidades: Lista de 5+ especialidades para escolher
- Horarios: Lista de plantoes disponiveis em um dia

IMPORTANTE:
- Max 10 itens total (somando todas as secoes)
- Cada secao tem titulo e lista de itens
- Cada item tem titulo (max 24 chars) e descricao opcional (max 72 chars)
- Obrigatorio: button_text (texto do botao que abre a lista)
- Se chip nao suportar lista, sera enviado como texto formatado""",
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "Texto da mensagem acima da lista",
            },
            "button_text": {
                "type": "string",
                "description": "Texto do botao que abre a lista (max 20 chars). Ex: 'Ver vagas'",
            },
            "secoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string"},
                        "itens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "titulo": {"type": "string"},
                                    "descricao": {"type": "string"},
                                },
                                "required": ["titulo"],
                            },
                        },
                    },
                    "required": ["titulo", "itens"],
                },
                "description": "Secoes da lista, cada uma com titulo e itens",
            },
        },
        "required": ["texto", "button_text", "secoes"],
    },
}

TOOL_ENVIAR_CTA = {
    "name": "enviar_cta",
    "description": """Envia botao com LINK CLICAVEL no WhatsApp (CTA URL).

QUANDO USAR:
- Compartilhar link de formulario
- Link para mapa/endereco do hospital
- Link para documento/contrato
- Qualquer situacao que precise de um link com botao

IMPORTANTE:
- URL deve ser valida e completa (https://)
- Texto do botao max 20 chars
- So funciona em chips Meta (outros: envia texto com link)
- Funciona apenas dentro da janela 24h""",
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "Texto da mensagem acima do botao",
            },
            "url": {
                "type": "string",
                "description": "URL completa (com https://)",
            },
            "label": {
                "type": "string",
                "description": "Texto do botao (max 20 chars). Ex: 'Ver no mapa'",
            },
        },
        "required": ["texto", "url", "label"],
    },
}
```

### Handlers

Cada tool precisa de:
1. Validacao de input (limites WhatsApp)
2. Geracao do payload Meta interactive format
3. Verificacao se chip e Meta (via contexto da conversa)
4. Se Meta: enviar interactive
5. Se nao-Meta: converter para texto e enviar

### Testes Obrigatorios

**Unitarios (`tests/tools/test_interactive_messages.py`):**

- [ ] `test_enviar_opcoes_2_botoes` — Gera payload com 2 reply buttons
- [ ] `test_enviar_opcoes_3_botoes` — Gera payload com 3 reply buttons
- [ ] `test_enviar_opcoes_valida_maximo` — Rejeita >3 opcoes
- [ ] `test_enviar_opcoes_valida_tamanho` — Trunca opcao >20 chars
- [ ] `test_enviar_opcoes_fallback_texto` — Chip nao-Meta recebe texto numerado
- [ ] `test_enviar_lista_1_secao` — Gera payload com 1 secao
- [ ] `test_enviar_lista_multiplas_secoes` — 3 secoes com itens
- [ ] `test_enviar_lista_valida_maximo_itens` — Rejeita >10 itens total
- [ ] `test_enviar_lista_fallback_texto` — Chip nao-Meta recebe texto formatado
- [ ] `test_enviar_cta_sucesso` — Gera payload CTA URL
- [ ] `test_enviar_cta_url_invalida` — Rejeita URL sem https
- [ ] `test_enviar_cta_fallback_texto` — Chip nao-Meta recebe "link: url"
- [ ] `test_todas_tools_respeitam_janela_24h` — Fora da janela, retorna erro
- [ ] `test_payload_meta_format_buttons` — Payload segue spec Graph API
- [ ] `test_payload_meta_format_list` — Payload segue spec Graph API

### Definition of Done

- [ ] 15 testes passando
- [ ] Tools registradas no registry
- [ ] Fallback texto funcional para todos os tipos

---

## Tarefa 2: Registrar Tools no Registry

### Objetivo

Integrar as 3 novas tools no sistema de tools de Julia.

### Modificacoes

**`app/tools/registry.py` — `register_legacy_tools()`:**

Adicionar imports e registros:
```python
from app.tools.interactive_messages import (
    TOOL_ENVIAR_OPCOES,
    TOOL_ENVIAR_LISTA,
    TOOL_ENVIAR_CTA,
    handle_enviar_opcoes,
    handle_enviar_lista,
    handle_enviar_cta,
)

# Adicionar a legacy_tools:
(TOOL_ENVIAR_OPCOES, handle_enviar_opcoes, "interactive"),
(TOOL_ENVIAR_LISTA, handle_enviar_lista, "interactive"),
(TOOL_ENVIAR_CTA, handle_enviar_cta, "interactive"),
```

**`app/services/agente/generation.py` (ou onde tools sao injetadas no prompt):**

Incluir as 3 novas tools na lista de tools disponíveis para Julia.

### Testes Obrigatorios

- [ ] `test_registry_inclui_interactive_tools` — 3 tools na categoria "interactive"
- [ ] `test_tools_disponiveis_no_prompt` — Julia recebe as tools no system prompt

### Definition of Done

- [ ] Tools aparecem no prompt de Julia
- [ ] Registry retorna todas as tools corretamente

---

## Tarefa 3: Delivery Pipeline — Suporte a Interactive

### Objetivo

O delivery pipeline hoje so envia texto. Precisa suportar envio de payloads interactive.

### Modificacoes

**`app/services/outbound/sender.py`:**

Adicionar funcao `send_outbound_interactive()`:
```python
async def send_outbound_interactive(
    telefone: str,
    interactive_payload: dict,
    ctx: OutboundContext,
    fallback_text: str,
) -> OutboundResult:
    """
    Envia mensagem interativa via outbound.

    Se chip e Meta e esta na janela: envia interactive.
    Se chip nao e Meta: envia fallback_text.
    Se fora da janela: retorna erro.
    """
    pass
```

**`app/services/chips/sender.py`:**

Adicionar `enviar_interactive_via_chip()`:
```python
async def enviar_interactive_via_chip(
    chip_id: str,
    telefone: str,
    interactive_payload: dict,
    fallback_text: str,
) -> dict:
    """
    Envia interactive via chip.

    Meta: provider.send_interactive(payload)
    Outros: provider.send_text(fallback_text)
    """
    pass
```

### Testes Obrigatorios

- [ ] `test_send_outbound_interactive_meta_na_janela` — Envia interactive
- [ ] `test_send_outbound_interactive_meta_fora_janela` — Retorna erro
- [ ] `test_send_outbound_interactive_evolution` — Envia fallback texto
- [ ] `test_enviar_interactive_via_chip_meta` — Chama provider.send_interactive
- [ ] `test_enviar_interactive_via_chip_evolution` — Chama provider.send_text com fallback

### Definition of Done

- [ ] Pipeline end-to-end funcional
- [ ] Guardrails aplicados (dev allowlist, rate limit)
- [ ] Fallback texto funcional
- [ ] Janela 24h respeitada

---

## Tarefa 4: Integracao com buscar_vagas

### Objetivo

Quando Julia busca vagas e o chip e Meta, o resultado pode sugerir formato interativo.

### Modificacoes

**`app/tools/response_formatter.py`:**

Adicionar ao `VagasResponseFormatter`:
```python
def formatar_vagas_interactive_list(self, vagas: list[dict]) -> dict:
    """
    Formata vagas como list message para chips Meta.

    Returns:
        dict com secoes para TOOL_ENVIAR_LISTA
    """
    pass

def formatar_vagas_interactive_buttons(self, vagas: list[dict]) -> dict:
    """
    Formata 1-3 vagas como reply buttons.

    Returns:
        dict com opcoes para TOOL_ENVIAR_OPCOES
    """
    pass
```

**`app/tools/vagas/definitions.py`:**

Atualizar instrucao de `TOOL_BUSCAR_VAGAS` para mencionar:
```
Se voce tem opcoes claras e quer facilitar a escolha do medico,
considere usar enviar_opcoes (ate 3 vagas) ou enviar_lista (4+ vagas)
ao inves de descrever cada vaga em texto.
```

### Testes Obrigatorios

- [ ] `test_formatar_vagas_list_3_vagas` — Gera secoes corretas
- [ ] `test_formatar_vagas_buttons_2_vagas` — Gera opcoes corretas
- [ ] `test_formatar_vagas_trunca_titulos` — Respeita limites WhatsApp

### Definition of Done

- [ ] Formatter gera payloads validos
- [ ] Tool buscar_vagas sugere uso de interactive no prompt
