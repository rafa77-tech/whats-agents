# E02: Capabilities Gate

**Status:** Pendente
**Estimativa:** 4h
**Dependencia:** E01 (Schema)
**Responsavel:** Dev

---

## Objetivo

Implementar um **gate** que filtra quais tools estão disponíveis para o LLM baseado no modo atual da conversa.

---

## GUARDRAIL CRÍTICO: Julia é Intermediária

**A Julia NÃO é dona das vagas.** As vagas vêm de scraping de grupos de WhatsApp.

### Proibições GLOBAIS (Todos os Modos)

| Forbidden Claim | Descrição | Motivo |
|-----------------|-----------|--------|
| `negotiate_price` | Negociar valores de plantão | Não tem autoridade |
| `confirm_booking_directly` | Confirmar reserva sozinha | Não é dona da vaga |
| `guarantee_availability` | Garantir que vaga está disponível | Pode ter mudado |
| `promise_conditions` | Prometer condições específicas | Não controla a vaga |

### Tools de Intermediação (Corretas)

| Tool | Função | Substitui |
|------|--------|-----------|
| `criar_handoff_externo` | Coloca médico em contato com dono da vaga | ~~`reservar_plantao`~~ |
| `registrar_status_intermediacao` | Status: interessado/contatado/fechado/sem_resposta | (novo) |
| `buscar_vagas` | Mostra vagas disponíveis (somente leitura) | (mantém) |
| `agendar_followup` | Agenda próximo contato | (mantém) |

### Tools OBSOLETAS (NUNCA usar)

| Tool | Motivo |
|------|--------|
| ~~`reservar_plantao`~~ | Julia não é dona da vaga |
| ~~`calcular_valor`~~ | Julia não negocia valores |
| ~~`solicitar_documentos`~~ | Bloqueado por enquanto (responsável pede docs) |

### Fluxo de Oferta Correto

```
Julia mostra vaga → Médico interessado → Julia conecta com responsável
                                      → Responsável negocia/fecha
                                      → Julia faz follow-up da conversão
```

---

## Conceito

```
┌─────────────────────────────────────────────────────────────────┐
│                     CAPABILITIES GATE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ENTRADA: conversation_mode + todas as tools                   │
│                     │                                            │
│                     ▼                                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │               MAPA DE CAPABILITIES                       │   │
│   │                                                          │   │
│   │   discovery: [salvar_memoria, perguntar_interesse, ...]  │   │
│   │   oferta:    [buscar_vagas, reservar_plantao, ...]       │   │
│   │   followup:  [buscar_vagas, agendar_followup, ...]       │   │
│   │   reativacao:[salvar_memoria, perguntar_interesse, ...]  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                     │                                            │
│                     ▼                                            │
│   SAÍDA: tools FILTRADAS (apenas permitidas no modo)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Mapa de Capabilities (3 Camadas)

O gate controla **três camadas de proteção**:
1. **Tools** - Ações no sistema (backend bloqueia)
2. **Claims** - Promessas verbais (prompt proíbe)
3. **Behavior** - Comportamento requerido (prompt exige)

### Definição Completa

```python
# =============================================================================
# PROIBIÇÕES GLOBAIS (Aplicam a TODOS os modos)
# Julia é INTERMEDIÁRIA - não pode negociar nem confirmar reservas
# =============================================================================
GLOBAL_FORBIDDEN_CLAIMS = [
    "negotiate_price",           # NUNCA negociar valores
    "confirm_booking_directly",  # NUNCA confirmar reserva sozinha
    "guarantee_availability",    # NUNCA garantir disponibilidade
    "promise_conditions",        # NUNCA prometer condições
]

GLOBAL_FORBIDDEN_TOOLS = [
    "reservar_plantao",          # Tool OBSOLETA - substituída por conectar_com_responsavel
]


# =============================================================================
# CAPABILITIES POR MODO
# =============================================================================
CAPABILITIES_BY_MODE = {
    ConversationMode.DISCOVERY: {
        # CAMADA 1: Tools
        "allowed_tools": [
            "salvar_memoria",           # Sempre pode salvar info
            "perguntar_interesse",      # Sondar interesse
            "perguntar_especialidade",  # Conhecer perfil
            "verificar_perfil",         # Checar dados existentes
        ],
        "forbidden_tools": [
            "buscar_vagas",             # NÃO oferecer ainda
            "conectar_com_responsavel", # NÃO conectar ainda
            "registrar_interesse",      # NÃO registrar ainda
            "solicitar_documentos",     # NÃO pedir docs ainda
        ],
        # CAMADA 2: Claims proibidos (além dos globais)
        "forbidden_claims": [
            "offer_specific_shift",     # "Tenho plantão dia X"
            "quote_price",              # "Paga R$ 2.500"
            "promise_availability",     # "Garanto que tem vaga"
        ],
        # CAMADA 3: Comportamento requerido
        "required_behavior": (
            "Você está em DISCOVERY: conheça o médico.\n"
            "- Pergunte 1 coisa de qualificação antes de propor transição\n"
            "- NÃO ofereça vaga nem valores específicos\n"
            "- Se ele pedir plantão, faça micro-confirmação antes de transicionar\n"
            "- Se perguntarem sobre VALORES: explique de forma genérica (faixa/depende), "
            "sem mencionar vaga específica, e puxe 1 pergunta de qualificação"
        ),
        "tone": "leve",
        "description": "Conhecer o médico, entender perfil e interesse",
    },

    ConversationMode.OFERTA: {
        # OFERTA = INTERMEDIAÇÃO (Julia NÃO é dona da vaga)
        "allowed_tools": [
            "buscar_vagas",                    # Somente leitura / apresentar opções
            "criar_handoff_externo",           # Coloca em contato com o dono da vaga
            "registrar_status_intermediacao",  # Status: interessado/contatado/fechado/sem_resposta
            "agendar_followup",                # Agendar acompanhamento
            "salvar_memoria",                  # Sempre
        ],
        "forbidden_tools": [
            "reservar_plantao",         # NUNCA (Julia não é dona da vaga)
            "calcular_valor",           # NUNCA (não negocia)
            "solicitar_documentos",     # Bloqueado (responsável pede docs)
            "perguntar_especialidade",  # Já deveria saber
        ],
        "forbidden_claims": [
            "confirm_booking",          # "fechado", "confirmado", "tá reservado"
            "quote_price",              # "paga X", "consigo X", "valor mínimo"
            "promise_availability",     # "garanto que ainda tem"
            "negotiate_terms",          # "consigo melhorar", "dá pra subir"
        ],
        "required_behavior": (
            "Você está em OFERTA (INTERMEDIAÇÃO): apresente a vaga e conecte o médico ao responsável.\n"
            "- Você NÃO é dona da vaga e NÃO confirma plantão\n"
            "- Você NÃO negocia valores/condições\n"
            "- Seu objetivo é: (1) confirmar interesse, (2) fazer ponte com o responsável, (3) acompanhar até desfecho\n"
            "- Se perguntarem valores, responda que quem confirma é o responsável e ofereça fazer a ponte agora"
        ),
        "tone": "objetiva",
        "description": "Ofertar vaga e intermediar contato com o responsável",
    },

    ConversationMode.FOLLOWUP: {
        # FOLLOWUP = Acompanhar desfecho da intermediação
        "allowed_tools": [
            "buscar_vagas",                    # Pode oferecer novas opções
            "criar_handoff_externo",           # Pode reconectar com outro responsável
            "registrar_status_intermediacao",  # Atualizar status: fechou/não fechou/sem resposta
            "salvar_memoria",                  # Sempre
            "agendar_followup",                # Pode remarcar
            "perguntar_interesse",             # Re-sondar
        ],
        "forbidden_tools": [
            "reservar_plantao",         # NUNCA
            "calcular_valor",           # NUNCA
            "perguntar_especialidade",  # Já deveria saber
        ],
        "forbidden_claims": [
            "pressure_decision",         # "Preciso de resposta hoje"
            "create_urgency",            # "Vai acabar!"
            "confirm_booking",           # NUNCA confirmar
            "negotiate_terms",           # NUNCA negociar
        ],
        "required_behavior": (
            "Você está em FOLLOWUP: acompanhe o desfecho da intermediação.\n"
            "- Pergunte se conseguiu falar com o responsável da vaga\n"
            "- Se fechou COM O RESPONSÁVEL, registre como conversão\n"
            "- Se não fechou, entenda o motivo e ofereça novas opções\n"
            "- Você continua sendo INTERMEDIÁRIA - não negocie nem confirme"
        ),
        "tone": "leve",
        "description": "Acompanhar desfecho da intermediação, manter relacionamento",
    },

    ConversationMode.REATIVACAO: {
        "allowed_tools": [
            "salvar_memoria",           # Sempre
            "perguntar_interesse",      # Re-sondar
            "buscar_vagas",             # Pode mostrar novidades
            "agendar_followup",         # Pode agendar
        ],
        "forbidden_tools": [
            "criar_handoff_externo",           # NÃO conectar direto (ainda não reengajou)
            "registrar_status_intermediacao",  # NÃO registrar ainda
            "reservar_plantao",                # NUNCA
            "calcular_valor",                  # NUNCA
            "solicitar_documentos",            # NÃO cobrar
        ],
        "forbidden_claims": [
            "offer_specific_shift",     # Não oferecer direto
            "quote_price",              # Não falar de valor
            "pressure_return",          # "Sumiu!" "Cadê você?"
            "confirm_booking",          # NUNCA confirmar
            "negotiate_terms",          # NUNCA negociar
        ],
        "required_behavior": (
            "Você está em REATIVAÇÃO: seja gentil.\n"
            "- Não cobre resposta\n"
            "- Ofereça algo novo/diferente\n"
            "- Lembre: você é INTERMEDIÁRIA - não negocie nem confirme"
        ),
        "tone": "cauteloso",
        "description": "Reativar contato de forma gentil, sem pressão",
    },
}
```

---

## Implementação

### Arquivo: `app/services/conversation_mode/capabilities.py`

```python
"""
Capabilities Gate - Filtra tools E controla claims por modo de conversa.

3 CAMADAS DE PROTEÇÃO:
1. Tools - Backend bloqueia chamadas
2. Claims - Prompt proíbe promessas
3. Behavior - Prompt exige comportamento

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Não pode negociar valores
- Não pode confirmar reservas
- Conecta médico com responsável da vaga
"""
import logging
from typing import Any

from .types import ConversationMode

logger = logging.getLogger(__name__)


# =============================================================================
# PROIBIÇÕES GLOBAIS (Aplicam a TODOS os modos)
# Julia é INTERMEDIÁRIA - não pode negociar nem confirmar reservas
# =============================================================================
GLOBAL_FORBIDDEN_CLAIMS = [
    "negotiate_price",           # NUNCA negociar valores
    "confirm_booking_directly",  # NUNCA confirmar reserva sozinha
    "guarantee_availability",    # NUNCA garantir disponibilidade
    "promise_conditions",        # NUNCA prometer condições
]

GLOBAL_FORBIDDEN_TOOLS = [
    "reservar_plantao",          # Tool OBSOLETA - substituída por conectar_com_responsavel
]


# Mapa completo de capabilities por modo (3 camadas)
CAPABILITIES_BY_MODE: dict[ConversationMode, dict] = {
    ConversationMode.DISCOVERY: {
        "allowed_tools": [
            "salvar_memoria",
            "perguntar_interesse",
            "perguntar_especialidade",
            "verificar_perfil",
        ],
        "forbidden_tools": [
            "buscar_vagas",
            "conectar_com_responsavel",
            "registrar_interesse",
            "solicitar_documentos",
        ],
        "forbidden_claims": [
            "offer_specific_shift",
            "quote_price",
            "promise_availability",
        ],
        "required_behavior": (
            "Você está em DISCOVERY: conheça o médico.\n"
            "- Pergunte 1 coisa de qualificação antes de propor transição\n"
            "- NÃO ofereça vaga nem valores específicos\n"
            "- Se ele pedir plantão, faça micro-confirmação antes de transicionar\n"
            "- Se perguntarem sobre VALORES: explique de forma genérica (faixa/depende), "
            "sem mencionar vaga específica, e puxe 1 pergunta de qualificação"
        ),
        "tone": "leve",
    },
    ConversationMode.OFERTA: {
        "allowed_tools": [
            "buscar_vagas",
            "conectar_com_responsavel",  # Conecta médico com dono da vaga
            "registrar_interesse",       # Registra interesse para follow-up
            "salvar_memoria",
            "agendar_followup",
        ],
        "forbidden_tools": [
            "perguntar_especialidade",
        ],
        # Claims proibidos MESMO em oferta (Julia é intermediária)
        "forbidden_claims": [
            "negotiate_price",           # NUNCA negociar
            "confirm_booking_directly",  # NUNCA confirmar sozinha
        ],
        "required_behavior": (
            "Você está em OFERTA: seja objetiva.\n"
            "- Apresente opções de vagas com informações básicas\n"
            "- Se o médico tiver interesse, CONECTE com o responsável pela vaga\n"
            "- NÃO negocie valores - você não tem autoridade\n"
            "- NÃO confirme reservas - o responsável da vaga faz isso\n"
            "- Informe que vai passar o contato do responsável ou os dados do médico"
        ),
        "tone": "direto",
    },
    ConversationMode.FOLLOWUP: {
        "allowed_tools": [
            "buscar_vagas",
            "conectar_com_responsavel",
            "registrar_interesse",
            "salvar_memoria",
            "fazer_followup_conexao",
            "agendar_followup",
            "perguntar_interesse",
        ],
        "forbidden_tools": [
            "perguntar_especialidade",
        ],
        "forbidden_claims": [
            "pressure_decision",
            "create_urgency",
            "negotiate_price",
        ],
        "required_behavior": (
            "Você está em FOLLOWUP: acompanhe a conversão.\n"
            "- Pergunte se conseguiu falar com o responsável da vaga\n"
            "- Se fechou, registre a conversão\n"
            "- Se não fechou, entenda o motivo e ofereça alternativas\n"
            "- NÃO pressione por decisão"
        ),
        "tone": "leve",
    },
    ConversationMode.REATIVACAO: {
        "allowed_tools": [
            "salvar_memoria",
            "perguntar_interesse",
            "buscar_vagas",
            "agendar_followup",
        ],
        "forbidden_tools": [
            "conectar_com_responsavel",
            "registrar_interesse",
            "solicitar_documentos",
        ],
        "forbidden_claims": [
            "offer_specific_shift",
            "quote_price",
            "pressure_return",
            "negotiate_price",
        ],
        "required_behavior": (
            "Você está em REATIVAÇÃO: seja gentil.\n"
            "- Não cobre resposta\n"
            "- Ofereça algo novo/diferente"
        ),
        "tone": "cauteloso",
    },
}


class CapabilitiesGate:
    """
    Gate que filtra tools E controla claims por modo de conversa.

    3 CAMADAS DE PROTEÇÃO:
    1. filter_tools() - Backend bloqueia tools proibidas
    2. get_forbidden_claims() - Para injetar no prompt
    3. get_required_behavior() - Para injetar no prompt

    GUARDRAIL CRÍTICO: Proibições globais aplicam a TODOS os modos.
    """

    def __init__(self, mode: ConversationMode):
        """
        Inicializa o gate para um modo específico.

        Args:
            mode: Modo atual da conversa
        """
        self.mode = mode
        self.config = CAPABILITIES_BY_MODE.get(
            mode, CAPABILITIES_BY_MODE[ConversationMode.DISCOVERY]
        )

    # === CAMADA 1: Tools ===

    def get_allowed_tools(self) -> list[str]:
        """Retorna lista de tools permitidas no modo atual."""
        return self.config.get("allowed_tools", [])

    def get_forbidden_tools(self) -> list[str]:
        """Retorna lista de tools proibidas no modo atual + globais."""
        mode_forbidden = self.config.get("forbidden_tools", [])
        # Adiciona proibições globais
        return list(set(mode_forbidden) | set(GLOBAL_FORBIDDEN_TOOLS))

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Verifica se uma tool específica é permitida."""
        # Verifica proibições globais primeiro
        if tool_name in GLOBAL_FORBIDDEN_TOOLS:
            return False
        # Depois verifica proibições do modo
        forbidden = self.config.get("forbidden_tools", [])
        if tool_name in forbidden:
            return False
        return True

    def filter_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Filtra lista de tools, removendo as proibidas.

        Args:
            tools: Lista de definições de tools (formato Claude)

        Returns:
            Lista filtrada apenas com tools permitidas
        """
        # Combina proibições do modo + globais
        forbidden = set(self.config.get("forbidden_tools", [])) | set(GLOBAL_FORBIDDEN_TOOLS)

        filtered = [
            tool for tool in tools
            if tool.get("name") not in forbidden
        ]

        removed = len(tools) - len(filtered)
        if removed:
            logger.debug(
                f"CapabilitiesGate [{self.mode.value}]: "
                f"removidas {removed} tools de {len(tools)}"
            )

        return filtered

    # === CAMADA 2: Claims (promessas verbais) ===

    def get_forbidden_claims(self) -> list[str]:
        """Retorna lista de claims proibidos no modo atual + globais."""
        mode_claims = self.config.get("forbidden_claims", [])
        # Adiciona proibições globais
        return list(set(mode_claims) | set(GLOBAL_FORBIDDEN_CLAIMS))

    # === CAMADA 3: Comportamento requerido ===

    def get_required_behavior(self) -> str:
        """Retorna comportamento requerido no modo atual."""
        return self.config.get("required_behavior", "")

    def get_tone(self) -> str:
        """Retorna tom recomendado para o modo."""
        return self.config.get("tone", "leve")

    # === GERAÇÃO DE CONSTRAINTS PARA PROMPT ===

    def get_constraints_text(self) -> str:
        """
        Gera texto completo de constraints para injetar no prompt.

        Inclui:
        - GUARDRAIL de intermediação (SEMPRE)
        - Modo atual
        - Comportamento requerido
        - Claims proibidos (modo + globais)
        - Tools proibidas

        Returns:
            Texto formatado para o prompt
        """
        parts = []

        # GUARDRAIL CRÍTICO (SEMPRE)
        parts.append("## REGRA ABSOLUTA: VOCÊ É INTERMEDIÁRIA")
        parts.append("- NUNCA negocie valores de plantão")
        parts.append("- NUNCA confirme reservas diretamente")
        parts.append("- Seu papel é CONECTAR o médico com o responsável da vaga")
        parts.append("")

        # Header do modo
        parts.append(f"## MODO DE CONVERSA: {self.mode.value.upper()}")
        parts.append("")

        # Comportamento requerido (CAMADA 3)
        required = self.get_required_behavior()
        if required:
            parts.append(required)
            parts.append("")

        # Claims proibidos (CAMADA 2) - modo + globais
        claims = self.get_forbidden_claims()
        if claims:
            claims_map = {
                "offer_specific_shift": "oferecer plantão específico",
                "quote_price": "citar valores exatos",
                "confirm_booking": "confirmar reserva",
                "confirm_booking_directly": "confirmar reserva sozinha",
                "promise_availability": "prometer disponibilidade",
                "pressure_decision": "pressionar por decisão",
                "create_urgency": "criar urgência falsa",
                "pressure_return": "cobrar retorno",
                "negotiate_price": "negociar valores",
                "guarantee_availability": "garantir disponibilidade",
                "promise_conditions": "prometer condições",
            }
            claims_text = ", ".join(claims_map.get(c, c) for c in claims)
            parts.append(f"**NÃO PODE:** {claims_text}")
            parts.append("")

        # Tools proibidas (para referência, já bloqueado no backend)
        tools = self.get_forbidden_tools()
        if tools:
            parts.append(f"**Tools bloqueadas:** {', '.join(tools)}")

        return "\n".join(parts)


def get_capabilities_gate(mode: ConversationMode) -> CapabilitiesGate:
    """Factory function para criar CapabilitiesGate."""
    return CapabilitiesGate(mode)
```

---

## DoD (Definition of Done)

### Implementação

- [ ] Arquivo `app/services/conversation_mode/capabilities.py` criado
- [ ] `CAPABILITIES_BY_MODE` define todos os 4 modos
- [ ] Classe `CapabilitiesGate` implementada com métodos:
  - [ ] `get_allowed_tools()` - lista de permitidas
  - [ ] `get_forbidden_tools()` - lista de proibidas
  - [ ] `is_tool_allowed(name)` - verifica uma tool
  - [ ] `filter_tools(tools)` - filtra lista de tools
  - [ ] `get_constraints_text()` - texto para prompt
- [ ] Exportado no `__init__.py`

### Testes Unitários

- [ ] Teste: discovery bloqueia `buscar_vagas`
  ```python
  def test_discovery_blocks_buscar_vagas():
      gate = CapabilitiesGate(ConversationMode.DISCOVERY)
      assert gate.is_tool_allowed("buscar_vagas") is False
      assert "buscar_vagas" in gate.get_forbidden_tools()
  ```

- [ ] Teste: oferta permite `buscar_vagas`
  ```python
  def test_oferta_allows_buscar_vagas():
      gate = CapabilitiesGate(ConversationMode.OFERTA)
      assert gate.is_tool_allowed("buscar_vagas") is True
  ```

- [ ] Teste: reativacao bloqueia `reservar_plantao`
  ```python
  def test_reativacao_blocks_reservar():
      gate = CapabilitiesGate(ConversationMode.REATIVACAO)
      assert gate.is_tool_allowed("reservar_plantao") is False
  ```

- [ ] Teste: filter_tools remove corretamente
  ```python
  def test_filter_tools():
      tools = [
          {"name": "buscar_vagas"},
          {"name": "salvar_memoria"},
      ]
      gate = CapabilitiesGate(ConversationMode.DISCOVERY)
      filtered = gate.filter_tools(tools)
      assert len(filtered) == 1
      assert filtered[0]["name"] == "salvar_memoria"
  ```

### Validação

- [ ] `get_constraints_text()` gera texto legível
- [ ] Log de debug mostra tools removidas
- [ ] Modos desconhecidos usam default (discovery)

### Não fazer neste epic

- [ ] NÃO integrar no agente (E04)
- [ ] NÃO implementar Mode Router (E03)
- [ ] NÃO modificar fluxo existente

---

## Exemplo de Uso

```python
from app.services.conversation_mode import (
    ConversationMode,
    CapabilitiesGate,
)

# Criar gate para modo discovery
gate = CapabilitiesGate(ConversationMode.DISCOVERY)

# Verificar tool específica
if gate.is_tool_allowed("buscar_vagas"):
    # usar tool
    pass

# Filtrar lista de tools antes de enviar ao LLM
all_tools = get_all_julia_tools()
filtered_tools = gate.filter_tools(all_tools)

# Gerar constraints para prompt
constraints = gate.get_constraints_text()
```

---

## Próximo

Após E02 concluído: [E03: Mode Router](./epic-03-router.md)
