# Epic 02: Decomposição do gerar_resposta_julia

## Severidade: P0 - CRÍTICO

## Objetivo

Quebrar a função `gerar_resposta_julia()` de ~350 linhas em funções menores, single-responsibility, testáveis individualmente.

---

## Problema Atual

### A "God Function"

`gerar_resposta_julia()` em `app/services/agente.py:168-513` faz **tudo**:

```
Linha 196-217:  Detectar situação e buscar conhecimento dinâmico
Linha 219-248:  Montar constraints (Policy Engine + Conversation Mode)
Linha 250-265:  Montar system prompt
Linha 267-273:  Montar histórico como messages
Linha 276-286:  Filtrar tools pelo modo
Linha 288-296:  Chamar LLM com tools
Linha 298-316:  Processar tool calls
Linha 318-396:  Loop de tool calls sequenciais (até 3x)
Linha 399-413:  Failsafe se tool sem resposta
Linha 427-509:  Detectar resposta incompleta e forçar retry
```

### Problemas Identificados

| Problema | Impacto |
|----------|---------|
| 350+ linhas em uma função | Difícil de entender e modificar |
| Múltiplas responsabilidades | Impossível testar partes isoladas |
| Duplicação de código | Loop de tools repetido 2x (linhas 351-396 e 462-506) |
| Variáveis locais complexas | `resultado`, `resultado_final`, `resultado_retry`, etc. |
| Nested ifs profundos | Difícil seguir o fluxo |

---

## Solução: Decomposição em Módulos

### Arquitetura Proposta

```
app/services/julia/
├── __init__.py              # Exports
├── orchestrator.py          # Orquestrador principal (< 100 linhas)
├── context_builder.py       # Monta contexto e prompt
├── tool_executor.py         # Executa tools e processa resultados
├── response_handler.py      # Processa e valida respostas
└── models.py                # Dataclasses internas
```

### Fluxo Simplificado

```
┌─────────────────────┐
│  orchestrator.py    │  ← Função principal < 100 linhas
│  gerar_resposta()   │
└─────────┬───────────┘
          │
    ┌─────┴─────┬─────────────┬────────────────┐
    ▼           ▼             ▼                ▼
┌────────┐ ┌─────────┐ ┌────────────┐ ┌─────────────┐
│Context │ │  LLM    │ │   Tool     │ │  Response   │
│Builder │ │Provider │ │ Executor   │ │  Handler    │
└────────┘ └─────────┘ └────────────┘ └─────────────┘
```

---

## Stories

### S31.E2.1: Criar Estrutura do Módulo Julia

**Objetivo:** Criar o módulo `app/services/julia/` com estrutura básica.

**ATENÇÃO:** Esta é uma refatoração crítica. Manter o código antigo funcionando até migração completa.

#### Tarefas Passo a Passo

1. **Criar diretório:**
   ```bash
   mkdir -p app/services/julia
   ```

2. **Criar `app/services/julia/__init__.py`:**

```python
"""
Julia Agent Module - Core do agente conversacional.

Sprint 31 - Decomposição do agente

Este módulo contém a lógica core da Julia, decomposta em
componentes menores e testáveis.

Uso:
    from app.services.julia import gerar_resposta_julia

    resposta = await gerar_resposta_julia(
        mensagem="Oi",
        contexto={...},
        medico={...},
        conversa={...},
    )
"""

# Re-exportar função principal (backward compatibility)
# Por enquanto aponta para o agente.py original
from app.services.agente import gerar_resposta_julia

__all__ = ["gerar_resposta_julia"]
```

3. **Criar `app/services/julia/models.py`:**

```python
"""
Modelos de dados internos do agente Julia.

Sprint 31 - S31.E2.1
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


@dataclass
class JuliaContext:
    """
    Contexto completo para geração de resposta.

    Agrupa todos os dados necessários para gerar uma resposta.
    """
    mensagem: str
    medico: Dict[str, Any]
    conversa: Dict[str, Any]

    # Contexto montado
    contexto_medico: str = ""
    contexto_vagas: str = ""
    contexto_historico: str = ""
    contexto_memorias: str = ""
    contexto_diretrizes: str = ""

    # Flags
    primeira_mensagem: bool = False
    incluir_historico: bool = True
    usar_tools: bool = True

    # Histórico raw (para converter em messages)
    historico_raw: List[Dict] = field(default_factory=list)

    # Metadata
    data_hora: str = ""
    dia_semana: str = ""
    trace_id: Optional[str] = None


@dataclass
class PolicyContext:
    """Contexto de políticas e constraints."""
    policy_constraints: str = ""
    capabilities_gate: Any = None  # CapabilitiesGate
    mode_info: Any = None  # ModeInfo
    tools_filtradas: List[Dict] = field(default_factory=list)


@dataclass
class ToolExecutionResult:
    """Resultado da execução de uma tool."""
    tool_call_id: str
    tool_name: str
    result: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


@dataclass
class GenerationResult:
    """Resultado de uma geração do LLM."""
    text: str
    tool_calls: List[Dict] = field(default_factory=list)
    stop_reason: str = "end_turn"
    needs_retry: bool = False

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class JuliaResponse:
    """
    Resposta final da Julia.

    Inclui a resposta e metadata para logging/debugging.
    """
    texto: str
    tool_calls_executadas: int = 0
    retry_necessario: bool = False
    conhecimento_usado: bool = False
    trace_id: Optional[str] = None

    @property
    def sucesso(self) -> bool:
        return bool(self.texto)
```

4. **Verificar estrutura:**
   ```bash
   ls -la app/services/julia/
   python -c "from app.services.julia.models import JuliaContext, JuliaResponse; print('OK')"
   ```

#### Definition of Done (DoD)

- [ ] Diretório `app/services/julia/` criado
- [ ] `__init__.py` com re-export de `gerar_resposta_julia` (backward compat)
- [ ] `models.py` com dataclasses: `JuliaContext`, `PolicyContext`, `ToolExecutionResult`, `GenerationResult`, `JuliaResponse`
- [ ] Imports funcionam sem erros
- [ ] Código existente continua funcionando (não quebrou nada)
- [ ] Commit: `feat(julia): cria estrutura do módulo julia`

---

### S31.E2.2: Extrair Context Builder

**Objetivo:** Extrair lógica de construção de contexto para módulo separado.

**Código a extrair:** Linhas 196-273 de `gerar_resposta_julia()`

#### Tarefas Passo a Passo

1. **Criar `app/services/julia/context_builder.py`:**

```python
"""
Context Builder - Monta contexto para geração de resposta.

Sprint 31 - S31.E2.2

Responsabilidades:
- Buscar conhecimento dinâmico
- Montar constraints (Policy Engine + Conversation Mode)
- Montar system prompt
- Converter histórico para formato de messages
"""
import logging
from typing import Optional, List, Dict, Any

from app.services.conhecimento.orquestrador import OrquestradorConhecimento
from app.services.conversation_mode.capabilities import CapabilitiesGate
from app.services.conversation_mode.models import ModeInfo
from app.services.conversation_mode.prompts import get_micro_confirmation_prompt
from app.services.policy.models import PolicyDecision
from app.prompts.builder import montar_prompt_julia
from app.services.agente import converter_historico_para_messages

from .models import JuliaContext, PolicyContext

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Constrói o contexto completo para geração de resposta.

    Uso:
        builder = ContextBuilder()
        system_prompt = await builder.build_system_prompt(context, policy_context)
        messages = builder.build_messages(context)
    """

    def __init__(self):
        self._orquestrador = OrquestradorConhecimento()

    async def buscar_conhecimento_dinamico(
        self,
        mensagem: str,
        historico_raw: List[Dict],
        medico: Dict,
    ) -> str:
        """
        Busca conhecimento dinâmico baseado na situação.

        Args:
            mensagem: Mensagem atual do médico
            historico_raw: Histórico de mensagens
            medico: Dados do médico

        Returns:
            Resumo do conhecimento relevante (string)
        """
        try:
            # Extrair últimas 5 mensagens recebidas
            historico_msgs = []
            if historico_raw:
                historico_msgs = [
                    m.get("conteudo", "")
                    for m in historico_raw
                    if m.get("tipo") == "recebida"
                ][-5:]

            situacao = await self._orquestrador.analisar_situacao(
                mensagem=mensagem,
                historico=historico_msgs,
                dados_cliente=medico,
                stage=medico.get("stage_jornada", "novo"),
            )

            logger.debug(
                f"Situação detectada: objecao={situacao.objecao.tipo}, "
                f"perfil={situacao.perfil.perfil}, objetivo={situacao.objetivo.objetivo}"
            )

            return situacao.resumo

        except Exception as e:
            logger.warning(f"Erro ao buscar conhecimento dinâmico: {e}")
            return ""

    def montar_constraints(
        self,
        policy_decision: Optional[PolicyDecision],
        capabilities_gate: Optional[CapabilitiesGate],
        mode_info: Optional[ModeInfo],
    ) -> str:
        """
        Monta constraints combinados de Policy Engine e Conversation Mode.

        Args:
            policy_decision: Decisão da Policy Engine
            capabilities_gate: Gate de capabilities por modo
            mode_info: Info do modo atual

        Returns:
            String com todos os constraints combinados
        """
        constraints_parts = []

        # Constraints da Policy Engine (Sprint 15)
        if policy_decision and policy_decision.constraints_text:
            constraints_parts.append(policy_decision.constraints_text)

        # Constraints do Conversation Mode (Sprint 29)
        if capabilities_gate:
            mode_constraints = capabilities_gate.get_constraints_text()
            if mode_constraints:
                constraints_parts.append(mode_constraints)
            logger.debug(
                f"Capabilities Gate aplicado: modo={capabilities_gate.mode.value}, "
                f"claims_proibidos={len(capabilities_gate.get_forbidden_claims())}"
            )

        # Prompt de micro-confirmação se há pending_transition
        if mode_info and mode_info.pending_transition:
            micro_prompt = get_micro_confirmation_prompt(
                mode_info.mode, mode_info.pending_transition
            )
            if micro_prompt:
                constraints_parts.append(micro_prompt)
                logger.debug(
                    f"Micro-confirmação injetada: "
                    f"{mode_info.mode.value} → {mode_info.pending_transition.value}"
                )

        return "\n\n---\n\n".join(constraints_parts) if constraints_parts else ""

    async def build_system_prompt(
        self,
        context: JuliaContext,
        policy_context: PolicyContext,
        conhecimento_dinamico: str = "",
    ) -> str:
        """
        Monta o system prompt completo.

        Args:
            context: Contexto da Julia
            policy_context: Contexto de políticas
            conhecimento_dinamico: Conhecimento buscado

        Returns:
            System prompt completo
        """
        return await montar_prompt_julia(
            contexto_medico=context.contexto_medico,
            contexto_vagas=context.contexto_vagas,
            historico=context.contexto_historico,
            primeira_msg=context.primeira_mensagem,
            data_hora_atual=context.data_hora,
            dia_semana=context.dia_semana,
            contexto_especialidade=context.medico.get("especialidade", ""),
            contexto_handoff=context.medico.get("handoff_recente", ""),
            contexto_memorias=context.contexto_memorias,
            especialidade_id=context.medico.get("especialidade_id"),
            diretrizes=context.contexto_diretrizes,
            conhecimento=conhecimento_dinamico,
            policy_constraints=policy_context.policy_constraints,
        )

    def build_history_messages(
        self,
        historico_raw: List[Dict],
    ) -> List[Dict]:
        """
        Converte histórico raw para formato de messages do LLM.

        Args:
            historico_raw: Lista de interações do banco

        Returns:
            Lista de messages no formato {"role": ..., "content": ...}
        """
        if not historico_raw:
            return []

        return converter_historico_para_messages(historico_raw)


# Singleton para uso em outras partes do código
_context_builder: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    """Retorna instância do ContextBuilder."""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder()
    return _context_builder
```

2. **Verificar import:**
   ```bash
   python -c "from app.services.julia.context_builder import ContextBuilder, get_context_builder; print('OK')"
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `context_builder.py` criado
- [ ] `buscar_conhecimento_dinamico()` extraído e funcionando
- [ ] `montar_constraints()` extraído e funcionando
- [ ] `build_system_prompt()` extraído e funcionando
- [ ] `build_history_messages()` extraído e funcionando
- [ ] Imports funcionam sem erros
- [ ] Commit: `refactor(julia): extrai ContextBuilder`

---

### S31.E2.3: Extrair Tool Executor

**Objetivo:** Extrair lógica de execução de tools para módulo separado.

**Código a extrair:** Linhas 298-396 e 462-506 (código duplicado!)

#### Tarefas Passo a Passo

1. **Criar `app/services/julia/tool_executor.py`:**

```python
"""
Tool Executor - Executa tools e processa resultados.

Sprint 31 - S31.E2.3

Responsabilidades:
- Executar tool calls retornadas pelo LLM
- Montar histórico com tool results
- Loop de tool calls sequenciais (máx 3)
"""
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.services.agente import processar_tool_call
from .models import ToolExecutionResult

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executa tools chamadas pelo LLM.

    Uso:
        executor = ToolExecutor()
        results = await executor.execute_tool_calls(tool_calls, medico, conversa)
    """

    MAX_SEQUENTIAL_CALLS = 3

    async def execute_tool_calls(
        self,
        tool_calls: List[Dict],
        medico: Dict,
        conversa: Dict,
    ) -> List[ToolExecutionResult]:
        """
        Executa uma lista de tool calls.

        Args:
            tool_calls: Lista de tool calls do LLM
            medico: Dados do médico
            conversa: Dados da conversa

        Returns:
            Lista de resultados de execução
        """
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_input = tool_call.get("input", {})
            tool_id = tool_call.get("id", "")

            logger.debug(f"Executando tool: {tool_name}")

            try:
                result = await processar_tool_call(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    medico=medico,
                    conversa=conversa,
                )

                results.append(ToolExecutionResult(
                    tool_call_id=tool_id,
                    tool_name=tool_name,
                    result=result,
                    success=True,
                ))

            except Exception as e:
                logger.error(f"Erro ao executar tool {tool_name}: {e}")
                results.append(ToolExecutionResult(
                    tool_call_id=tool_id,
                    tool_name=tool_name,
                    result={"error": str(e)},
                    success=False,
                    error=str(e),
                ))

        return results

    def format_tool_results_for_llm(
        self,
        results: List[ToolExecutionResult],
    ) -> List[Dict]:
        """
        Formata resultados para enviar de volta ao LLM.

        Args:
            results: Lista de resultados de execução

        Returns:
            Lista no formato esperado pelo LLM
        """
        return [
            {
                "type": "tool_result",
                "tool_use_id": result.tool_call_id,
                "content": str(result.result),
            }
            for result in results
        ]

    def build_assistant_content_with_tools(
        self,
        text: str,
        tool_calls: List[Dict],
    ) -> List[Dict]:
        """
        Monta conteúdo do assistant incluindo tool calls.

        Args:
            text: Texto gerado pelo LLM
            tool_calls: Tool calls feitas

        Returns:
            Lista de content blocks
        """
        content = []

        if text:
            content.append({"type": "text", "text": text})

        for tool_call in tool_calls:
            content.append({
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": tool_call["input"],
            })

        return content

    def append_tool_exchange_to_history(
        self,
        history: List[Dict],
        assistant_content: List[Dict],
        tool_results: List[Dict],
    ) -> List[Dict]:
        """
        Adiciona troca de tool ao histórico.

        Args:
            history: Histórico atual
            assistant_content: Conteúdo do assistant com tool calls
            tool_results: Resultados das tools

        Returns:
            Novo histórico com a troca adicionada
        """
        return history + [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": tool_results},
        ]


async def execute_tool_loop(
    initial_result: Dict,
    history: List[Dict],
    system_prompt: str,
    tools: List[Dict],
    medico: Dict,
    conversa: Dict,
    continue_fn,  # Função para continuar após tool
    max_iterations: int = 3,
) -> Tuple[str, int]:
    """
    Executa loop de tool calls sequenciais.

    Args:
        initial_result: Resultado inicial do LLM
        history: Histórico de mensagens
        system_prompt: System prompt
        tools: Tools disponíveis
        medico: Dados do médico
        conversa: Dados da conversa
        continue_fn: Função async para continuar após tool
        max_iterations: Máximo de iterações

    Returns:
        Tuple (resposta_final, num_tool_calls)
    """
    executor = ToolExecutor()
    current_result = initial_result
    current_history = history
    iteration = 0
    total_tool_calls = 0

    while current_result.get("tool_use") and iteration < max_iterations:
        iteration += 1
        tool_calls = current_result["tool_use"]
        total_tool_calls += len(tool_calls)

        logger.info(f"Tool call iteração {iteration}: {[t['name'] for t in tool_calls]}")

        # Executar tools
        execution_results = await executor.execute_tool_calls(
            tool_calls, medico, conversa
        )

        # Formatar resultados
        tool_results = executor.format_tool_results_for_llm(execution_results)

        # Montar conteúdo do assistant
        assistant_content = executor.build_assistant_content_with_tools(
            current_result.get("text", ""),
            tool_calls,
        )

        # Atualizar histórico
        current_history = executor.append_tool_exchange_to_history(
            current_history,
            assistant_content,
            tool_results,
        )

        # Continuar geração
        current_result = await continue_fn(
            historico=current_history,
            tool_results=tool_results,
            system_prompt=system_prompt,
            tools=tools,
            max_tokens=300,
        )

    final_text = current_result.get("text", "")
    return final_text, total_tool_calls


# Singleton
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Retorna instância do ToolExecutor."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
```

2. **Verificar import:**
   ```bash
   python -c "from app.services.julia.tool_executor import ToolExecutor, execute_tool_loop; print('OK')"
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `tool_executor.py` criado
- [ ] `ToolExecutor` classe com métodos:
  - [ ] `execute_tool_calls()` - executa lista de tools
  - [ ] `format_tool_results_for_llm()` - formata resultados
  - [ ] `build_assistant_content_with_tools()` - monta content blocks
  - [ ] `append_tool_exchange_to_history()` - atualiza histórico
- [ ] `execute_tool_loop()` - função para loop de tools (elimina duplicação!)
- [ ] Imports funcionam sem erros
- [ ] Commit: `refactor(julia): extrai ToolExecutor`

---

### S31.E2.4: Extrair Response Handler

**Objetivo:** Extrair lógica de validação e retry de respostas.

**Código a extrair:** Linhas 427-509 (detecção de resposta incompleta)

#### Tarefas Passo a Passo

1. **Criar `app/services/julia/response_handler.py`:**

```python
"""
Response Handler - Valida e processa respostas.

Sprint 31 - S31.E2.4

Responsabilidades:
- Detectar respostas incompletas
- Forçar uso de tool quando necessário
- Failsafe quando tool não gera resposta
"""
import logging
import re
from typing import Optional, Tuple, List, Dict, Callable, Awaitable

logger = logging.getLogger(__name__)


class ResponseHandler:
    """
    Processa e valida respostas do LLM.

    Detecta problemas e tenta recuperar automaticamente.
    """

    # Padrões que indicam resposta incompleta
    INCOMPLETE_PATTERNS = [
        r"vou\s+verificar",
        r"deixa\s+eu\s+ver",
        r"tenho\s+algumas?\s+vagas?",
        r"tenho\s+ótimas?\s+opções?",
        r"achei\s+algumas?",
        r"encontrei\s+algumas?",
        r"olha\s+só",
        r"temos\s+(sim|algumas?)",
        r"posso\s+te\s+mostrar",
    ]

    # Respostas muito curtas são suspeitas
    MIN_RESPONSE_LENGTH = 20

    def __init__(self):
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.INCOMPLETE_PATTERNS
        ]

    def resposta_parece_incompleta(
        self,
        resposta: str,
        stop_reason: Optional[str] = None,
    ) -> bool:
        """
        Verifica se a resposta parece incompleta.

        Uma resposta é considerada incompleta se:
        1. Menciona que vai mostrar vagas mas não mostra
        2. É muito curta
        3. Parou por max_tokens

        Args:
            resposta: Texto da resposta
            stop_reason: Motivo de parada do LLM

        Returns:
            True se parece incompleta
        """
        if not resposta:
            return True

        # Parou por limite de tokens
        if stop_reason == "max_tokens":
            logger.debug("Resposta incompleta: max_tokens atingido")
            return True

        # Muito curta
        if len(resposta.strip()) < self.MIN_RESPONSE_LENGTH:
            logger.debug(f"Resposta incompleta: muito curta ({len(resposta)} chars)")
            return True

        # Verifica padrões de promessa sem entrega
        resposta_lower = resposta.lower()
        for pattern in self._compiled_patterns:
            if pattern.search(resposta_lower):
                # Verifica se tem dados concretos (valores, datas)
                if not self._tem_dados_concretos(resposta):
                    logger.debug(f"Resposta incompleta: pattern '{pattern.pattern}' sem dados")
                    return True

        return False

    def _tem_dados_concretos(self, resposta: str) -> bool:
        """
        Verifica se a resposta contém dados concretos.

        Dados concretos incluem: valores monetários, datas, horários.
        """
        # Valor monetário (R$ X.XXX ou R$X.XXX)
        if re.search(r"R\$\s*[\d.,]+", resposta):
            return True

        # Data (DD/MM ou dia X)
        if re.search(r"\d{1,2}/\d{1,2}|\bdia\s+\d{1,2}\b", resposta):
            return True

        # Horário (XXh ou XX:XX)
        if re.search(r"\d{1,2}h|\d{1,2}:\d{2}", resposta):
            return True

        return False

    async def tentar_recuperar_resposta_incompleta(
        self,
        resposta_original: str,
        history: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        generate_fn: Callable,
        continue_fn: Callable,
        medico: Dict,
        conversa: Dict,
    ) -> Tuple[str, bool]:
        """
        Tenta recuperar uma resposta incompleta forçando uso de tool.

        Args:
            resposta_original: Resposta incompleta
            history: Histórico de mensagens
            system_prompt: System prompt
            tools: Tools disponíveis
            generate_fn: Função para gerar com tools
            continue_fn: Função para continuar após tool
            medico: Dados do médico
            conversa: Dados da conversa

        Returns:
            Tuple (nova_resposta, recuperou)
        """
        logger.warning(f"Tentando recuperar resposta incompleta: '{resposta_original[-50:]}'")

        # Montar histórico com instrução de usar tool
        historico_retry = history + [
            {"role": "assistant", "content": resposta_original},
            {
                "role": "user",
                "content": (
                    "Use a ferramenta buscar_vagas para encontrar as vagas disponíveis "
                    "e depois responda ao médico com as opções."
                )
            },
        ]

        # Forçar geração com tools
        resultado_retry = await generate_fn(
            mensagem="",
            historico=historico_retry,
            system_prompt=system_prompt,
            tools=tools,
            max_tokens=300,
        )

        # Se gerou tool call, processar
        if resultado_retry.get("tool_use"):
            from .tool_executor import execute_tool_loop

            resposta_final, _ = await execute_tool_loop(
                initial_result=resultado_retry,
                history=historico_retry,
                system_prompt=system_prompt,
                tools=tools,
                medico=medico,
                conversa=conversa,
                continue_fn=continue_fn,
                max_iterations=1,  # Só 1 iteração no retry
            )

            if resposta_final:
                logger.info(f"Resposta recuperada: '{resposta_final[:50]}...'")
                return resposta_final, True

        # Se gerou texto sem tool
        if resultado_retry.get("text"):
            return resultado_retry["text"], True

        # Não conseguiu recuperar
        logger.warning("Não foi possível recuperar resposta incompleta")
        return resposta_original, False

    async def garantir_resposta_apos_tool(
        self,
        tool_results: List[Dict],
        history: List[Dict],
        system_prompt: str,
        generate_fn: Callable,
    ) -> str:
        """
        Garante que há uma resposta após execução de tools.

        Failsafe para quando tool é executada mas LLM não gera texto.

        Args:
            tool_results: Resultados das tools
            history: Histórico com tools
            system_prompt: System prompt
            generate_fn: Função para gerar resposta

        Returns:
            Resposta garantida
        """
        logger.warning("Tool executada mas sem resposta, forçando geração")

        historico_forcar = history + [
            {"role": "user", "content": tool_results},
            {"role": "user", "content": "Agora responda ao médico de forma natural e curta."},
        ]

        resultado = await generate_fn(
            mensagem="",
            historico=historico_forcar,
            system_prompt=system_prompt,
            max_tokens=150,
        )

        return resultado or ""


# Singleton
_response_handler: Optional[ResponseHandler] = None


def get_response_handler() -> ResponseHandler:
    """Retorna instância do ResponseHandler."""
    global _response_handler
    if _response_handler is None:
        _response_handler = ResponseHandler()
    return _response_handler
```

2. **Verificar import:**
   ```bash
   python -c "from app.services.julia.response_handler import ResponseHandler; print('OK')"
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `response_handler.py` criado
- [ ] `ResponseHandler` classe com métodos:
  - [ ] `resposta_parece_incompleta()` - detecta respostas incompletas
  - [ ] `_tem_dados_concretos()` - verifica se tem valores/datas
  - [ ] `tentar_recuperar_resposta_incompleta()` - força tool e recupera
  - [ ] `garantir_resposta_apos_tool()` - failsafe
- [ ] Padrões de detecção extraídos como constantes
- [ ] Imports funcionam sem erros
- [ ] Commit: `refactor(julia): extrai ResponseHandler`

---

### S31.E2.5: Criar Orchestrator

**Objetivo:** Criar orquestrador principal que usa os componentes extraídos.

**Arquivo:** `app/services/julia/orchestrator.py`

**META:** Esta função deve ter < 100 linhas.

#### Tarefas Passo a Passo

1. **Criar `app/services/julia/orchestrator.py`:**

```python
"""
Julia Orchestrator - Orquestra geração de resposta.

Sprint 31 - S31.E2.5

Esta é a função principal, agora com < 100 linhas.
Delega para componentes especializados.
"""
import logging
from typing import Optional, Dict, Any, List

from app.services.llm import LLMProvider, get_llm_provider
from app.services.agente import JULIA_TOOLS, gerar_resposta_com_tools, continuar_apos_tool, gerar_resposta
from app.services.policy.models import PolicyDecision
from app.services.conversation_mode.capabilities import CapabilitiesGate
from app.services.conversation_mode.models import ModeInfo

from .context_builder import ContextBuilder, get_context_builder
from .tool_executor import ToolExecutor, execute_tool_loop, get_tool_executor
from .response_handler import ResponseHandler, get_response_handler
from .models import JuliaContext, PolicyContext, JuliaResponse

logger = logging.getLogger(__name__)


async def gerar_resposta_julia_v2(
    mensagem: str,
    contexto: Dict[str, Any],
    medico: Dict[str, Any],
    conversa: Dict[str, Any],
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: Optional[PolicyDecision] = None,
    capabilities_gate: Optional[CapabilitiesGate] = None,
    mode_info: Optional[ModeInfo] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> str:
    """
    Gera resposta da Julia para uma mensagem (versão refatorada).

    Args:
        mensagem: Mensagem do médico
        contexto: Contexto montado
        medico: Dados do médico
        conversa: Dados da conversa
        incluir_historico: Se deve passar histórico
        usar_tools: Se deve usar tools
        policy_decision: Decisão da Policy Engine
        capabilities_gate: Gate de capabilities
        mode_info: Info do modo atual
        llm_provider: Provider de LLM (injetável para testes)

    Returns:
        Texto da resposta gerada
    """
    # Componentes
    context_builder = get_context_builder()
    tool_executor = get_tool_executor()
    response_handler = get_response_handler()

    # 1. Buscar conhecimento dinâmico
    conhecimento = await context_builder.buscar_conhecimento_dinamico(
        mensagem=mensagem,
        historico_raw=contexto.get("historico_raw", []),
        medico=medico,
    )

    # 2. Montar constraints
    policy_constraints = context_builder.montar_constraints(
        policy_decision, capabilities_gate, mode_info
    )

    # 3. Montar contexto e policy context
    julia_context = JuliaContext(
        mensagem=mensagem,
        medico=medico,
        conversa=conversa,
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        contexto_historico=contexto.get("historico", ""),
        contexto_memorias=contexto.get("memorias", ""),
        contexto_diretrizes=contexto.get("diretrizes", ""),
        primeira_mensagem=contexto.get("primeira_msg", False),
        incluir_historico=incluir_historico,
        usar_tools=usar_tools,
        historico_raw=contexto.get("historico_raw", []),
        data_hora=contexto.get("data_hora_atual", ""),
        dia_semana=contexto.get("dia_semana", ""),
    )

    policy_context = PolicyContext(
        policy_constraints=policy_constraints,
        capabilities_gate=capabilities_gate,
        mode_info=mode_info,
    )

    # 4. Montar system prompt
    system_prompt = await context_builder.build_system_prompt(
        julia_context, policy_context, conhecimento
    )

    # 5. Montar histórico
    history = []
    if incluir_historico:
        history = context_builder.build_history_messages(
            contexto.get("historico_raw", [])
        )

    # 6. Filtrar tools pelo modo
    tools = JULIA_TOOLS
    if capabilities_gate:
        tools = capabilities_gate.filter_tools(JULIA_TOOLS)

    logger.info(f"Gerando resposta para: {mensagem[:50]}...")

    # 7. Gerar resposta
    if not usar_tools:
        return await gerar_resposta(
            mensagem=mensagem,
            historico=history,
            system_prompt=system_prompt,
            max_tokens=300,
        )

    # 8. Gerar com tools
    resultado = await gerar_resposta_com_tools(
        mensagem=mensagem,
        historico=history,
        system_prompt=system_prompt,
        tools=tools,
        max_tokens=300,
    )

    # 9. Processar tool calls se houver
    if resultado.get("tool_use"):
        history_with_msg = history + [{"role": "user", "content": mensagem}]

        resposta, _ = await execute_tool_loop(
            initial_result=resultado,
            history=history_with_msg,
            system_prompt=system_prompt,
            tools=tools,
            medico=medico,
            conversa=conversa,
            continue_fn=continuar_apos_tool,
        )

        # Failsafe
        if not resposta:
            resposta = await response_handler.garantir_resposta_apos_tool(
                tool_results=[],
                history=history_with_msg,
                system_prompt=system_prompt,
                generate_fn=gerar_resposta,
            )
    else:
        resposta = resultado.get("text", "")

    # 10. Verificar resposta incompleta
    if (
        usar_tools
        and not resultado.get("tool_use")
        and response_handler.resposta_parece_incompleta(resposta, resultado.get("stop_reason"))
    ):
        resposta, _ = await response_handler.tentar_recuperar_resposta_incompleta(
            resposta_original=resposta,
            history=history + [{"role": "user", "content": mensagem}],
            system_prompt=system_prompt,
            tools=tools,
            generate_fn=gerar_resposta_com_tools,
            continue_fn=continuar_apos_tool,
            medico=medico,
            conversa=conversa,
        )

    logger.info(f"Resposta gerada: {resposta[:50]}...")
    return resposta
```

2. **Contar linhas:**
   ```bash
   wc -l app/services/julia/orchestrator.py
   # Deve ser < 150 linhas (incluindo docstrings)
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `orchestrator.py` criado
- [ ] Função `gerar_resposta_julia_v2()` com < 100 linhas de código (excluindo docstrings)
- [ ] Usa `ContextBuilder` para contexto
- [ ] Usa `ToolExecutor` via `execute_tool_loop()` para tools
- [ ] Usa `ResponseHandler` para validação
- [ ] Aceita `llm_provider` opcional para DI
- [ ] Imports funcionam sem erros
- [ ] Commit: `refactor(julia): cria orchestrator`

---

### S31.E2.6: Migrar para Novo Orchestrator

**Objetivo:** Substituir `gerar_resposta_julia()` original pelo novo orchestrator.

**ATENÇÃO:** Esta é a migração crítica. Fazer com cuidado.

#### Tarefas Passo a Passo

1. **Atualizar `app/services/julia/__init__.py`:**

```python
"""
Julia Agent Module - Core do agente conversacional.

Sprint 31 - Versão refatorada
"""
# Exportar nova versão como função principal
from .orchestrator import gerar_resposta_julia_v2 as gerar_resposta_julia

# Componentes (para testes e extensão)
from .context_builder import ContextBuilder, get_context_builder
from .tool_executor import ToolExecutor, get_tool_executor
from .response_handler import ResponseHandler, get_response_handler
from .models import JuliaContext, PolicyContext, JuliaResponse

__all__ = [
    # Função principal
    "gerar_resposta_julia",
    # Componentes
    "ContextBuilder",
    "get_context_builder",
    "ToolExecutor",
    "get_tool_executor",
    "ResponseHandler",
    "get_response_handler",
    # Models
    "JuliaContext",
    "PolicyContext",
    "JuliaResponse",
]
```

2. **Atualizar imports nos consumidores:**

   Buscar onde `gerar_resposta_julia` é importada:
   ```bash
   grep -rn "from app.services.agente import.*gerar_resposta_julia" app/
   ```

   Para cada arquivo encontrado, atualizar:
   ```python
   # ANTES
   from app.services.agente import gerar_resposta_julia

   # DEPOIS (opção 1 - usar módulo julia)
   from app.services.julia import gerar_resposta_julia

   # DEPOIS (opção 2 - manter agente.py como facade)
   # Não precisa mudar, agente.py vai re-exportar
   ```

3. **Atualizar `app/services/agente.py` como facade (recomendado):**

   No final do arquivo `agente.py`:
   ```python
   # Sprint 31: Re-exportar do novo módulo
   # Mantém backward compatibility
   try:
       from app.services.julia.orchestrator import gerar_resposta_julia_v2

       # Substituir a função original
       gerar_resposta_julia = gerar_resposta_julia_v2
   except ImportError:
       # Fallback para função original se módulo não existir
       pass
   ```

4. **Rodar testes:**
   ```bash
   uv run pytest tests/services/test_agente.py -v
   uv run pytest tests/ -k "julia" -v
   ```

5. **Teste manual:**
   - Enviar mensagem de teste via WhatsApp
   - Verificar que resposta é gerada corretamente
   - Verificar logs para erros

#### Definition of Done (DoD)

- [ ] `app/services/julia/__init__.py` exporta `gerar_resposta_julia`
- [ ] Consumidores atualizados OU agente.py atua como facade
- [ ] Todos os testes existentes passando
- [ ] Teste manual de conversa funcionando
- [ ] Nenhuma regressão
- [ ] Commit: `refactor(julia): migra para novo orchestrator`

---

### S31.E2.7: Criar Testes para Componentes

**Objetivo:** Garantir que cada componente funciona isoladamente.

**Arquivos:** `tests/services/julia/`

#### Tarefas Passo a Passo

1. **Criar estrutura:**
   ```bash
   mkdir -p tests/services/julia
   touch tests/services/julia/__init__.py
   ```

2. **Criar `tests/services/julia/test_context_builder.py`:**

```python
"""
Testes do ContextBuilder.

Sprint 31 - S31.E2.7
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.julia.context_builder import ContextBuilder
from app.services.julia.models import JuliaContext, PolicyContext


class TestContextBuilder:
    """Testes do ContextBuilder."""

    @pytest.fixture
    def builder(self):
        return ContextBuilder()

    @pytest.mark.asyncio
    async def test_buscar_conhecimento_dinamico_sucesso(self, builder):
        """Deve buscar conhecimento com sucesso."""
        with patch.object(builder, '_orquestrador') as mock_orq:
            mock_situacao = MagicMock()
            mock_situacao.resumo = "Conhecimento relevante"
            mock_orq.analisar_situacao = AsyncMock(return_value=mock_situacao)

            resultado = await builder.buscar_conhecimento_dinamico(
                mensagem="Quero vagas",
                historico_raw=[],
                medico={"stage_jornada": "novo"},
            )

            assert resultado == "Conhecimento relevante"

    @pytest.mark.asyncio
    async def test_buscar_conhecimento_dinamico_erro(self, builder):
        """Deve retornar string vazia em caso de erro."""
        with patch.object(builder, '_orquestrador') as mock_orq:
            mock_orq.analisar_situacao = AsyncMock(side_effect=Exception("Erro"))

            resultado = await builder.buscar_conhecimento_dinamico(
                mensagem="Teste",
                historico_raw=[],
                medico={},
            )

            assert resultado == ""

    def test_montar_constraints_vazio(self, builder):
        """Deve retornar vazio se não há constraints."""
        resultado = builder.montar_constraints(
            policy_decision=None,
            capabilities_gate=None,
            mode_info=None,
        )
        assert resultado == ""

    def test_montar_constraints_com_policy(self, builder):
        """Deve incluir constraints da policy."""
        mock_policy = MagicMock()
        mock_policy.constraints_text = "Policy constraint"

        resultado = builder.montar_constraints(
            policy_decision=mock_policy,
            capabilities_gate=None,
            mode_info=None,
        )

        assert "Policy constraint" in resultado

    def test_build_history_messages_vazio(self, builder):
        """Deve retornar lista vazia se histórico vazio."""
        resultado = builder.build_history_messages([])
        assert resultado == []


class TestContextBuilderIntegration:
    """Testes de integração do ContextBuilder."""

    @pytest.mark.asyncio
    async def test_build_system_prompt(self):
        """Deve montar system prompt completo."""
        builder = ContextBuilder()

        context = JuliaContext(
            mensagem="Oi",
            medico={"id": "123"},
            conversa={"id": "456"},
        )
        policy_context = PolicyContext()

        with patch('app.services.julia.context_builder.montar_prompt_julia') as mock_prompt:
            mock_prompt.return_value = "System prompt montado"

            resultado = await builder.build_system_prompt(
                context, policy_context, "conhecimento"
            )

            assert resultado == "System prompt montado"
            mock_prompt.assert_called_once()
```

3. **Criar `tests/services/julia/test_tool_executor.py`:**

```python
"""
Testes do ToolExecutor.

Sprint 31 - S31.E2.7
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.julia.tool_executor import ToolExecutor, execute_tool_loop
from app.services.julia.models import ToolExecutionResult


class TestToolExecutor:
    """Testes do ToolExecutor."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    @pytest.mark.asyncio
    async def test_execute_tool_calls_sucesso(self, executor):
        """Deve executar tool calls com sucesso."""
        tool_calls = [
            {"id": "1", "name": "buscar_vagas", "input": {"regiao": "SP"}}
        ]

        with patch('app.services.julia.tool_executor.processar_tool_call') as mock:
            mock.return_value = {"vagas": []}

            results = await executor.execute_tool_calls(
                tool_calls,
                medico={"id": "123"},
                conversa={"id": "456"},
            )

            assert len(results) == 1
            assert results[0].success is True
            assert results[0].tool_name == "buscar_vagas"

    @pytest.mark.asyncio
    async def test_execute_tool_calls_erro(self, executor):
        """Deve capturar erro e continuar."""
        tool_calls = [
            {"id": "1", "name": "tool_que_falha", "input": {}}
        ]

        with patch('app.services.julia.tool_executor.processar_tool_call') as mock:
            mock.side_effect = Exception("Erro na tool")

            results = await executor.execute_tool_calls(
                tool_calls,
                medico={},
                conversa={},
            )

            assert len(results) == 1
            assert results[0].success is False
            assert "Erro" in results[0].error

    def test_format_tool_results_for_llm(self, executor):
        """Deve formatar resultados corretamente."""
        results = [
            ToolExecutionResult(
                tool_call_id="1",
                tool_name="test",
                result={"data": "value"},
            )
        ]

        formatted = executor.format_tool_results_for_llm(results)

        assert len(formatted) == 1
        assert formatted[0]["type"] == "tool_result"
        assert formatted[0]["tool_use_id"] == "1"

    def test_build_assistant_content_with_tools(self, executor):
        """Deve montar content com tool calls."""
        tool_calls = [
            {"id": "1", "name": "test_tool", "input": {"a": 1}}
        ]

        content = executor.build_assistant_content_with_tools(
            text="Texto",
            tool_calls=tool_calls,
        )

        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "tool_use"


class TestExecuteToolLoop:
    """Testes da função execute_tool_loop."""

    @pytest.mark.asyncio
    async def test_loop_sem_tools(self):
        """Deve retornar imediatamente se não há tool calls."""
        resultado = {"text": "Resposta", "tool_use": []}

        resposta, count = await execute_tool_loop(
            initial_result=resultado,
            history=[],
            system_prompt="",
            tools=[],
            medico={},
            conversa={},
            continue_fn=AsyncMock(),
        )

        assert resposta == "Resposta"
        assert count == 0

    @pytest.mark.asyncio
    async def test_loop_max_iterations(self):
        """Deve parar após max_iterations."""
        # Mock que sempre retorna tool_use
        continue_fn = AsyncMock(return_value={
            "text": "",
            "tool_use": [{"id": "1", "name": "loop", "input": {}}]
        })

        resultado_inicial = {
            "text": "",
            "tool_use": [{"id": "0", "name": "start", "input": {}}]
        }

        with patch('app.services.julia.tool_executor.processar_tool_call') as mock:
            mock.return_value = {}

            _, count = await execute_tool_loop(
                initial_result=resultado_inicial,
                history=[],
                system_prompt="",
                tools=[],
                medico={},
                conversa={},
                continue_fn=continue_fn,
                max_iterations=3,
            )

            # Deve parar em 3 iterações
            assert count == 3
```

4. **Criar `tests/services/julia/test_response_handler.py`:**

```python
"""
Testes do ResponseHandler.

Sprint 31 - S31.E2.7
"""
import pytest

from app.services.julia.response_handler import ResponseHandler


class TestResponseHandler:
    """Testes do ResponseHandler."""

    @pytest.fixture
    def handler(self):
        return ResponseHandler()

    def test_resposta_vazia_incompleta(self, handler):
        """Resposta vazia deve ser incompleta."""
        assert handler.resposta_parece_incompleta("") is True
        assert handler.resposta_parece_incompleta("   ") is True

    def test_resposta_max_tokens_incompleta(self, handler):
        """Resposta com stop_reason max_tokens é incompleta."""
        assert handler.resposta_parece_incompleta(
            "Texto qualquer",
            stop_reason="max_tokens"
        ) is True

    def test_resposta_curta_incompleta(self, handler):
        """Resposta muito curta é incompleta."""
        assert handler.resposta_parece_incompleta("Oi") is True

    def test_resposta_promessa_sem_dados_incompleta(self, handler):
        """Resposta com promessa mas sem dados é incompleta."""
        assert handler.resposta_parece_incompleta(
            "Tenho algumas vagas pra você"
        ) is True

        assert handler.resposta_parece_incompleta(
            "Deixa eu ver aqui"
        ) is True

    def test_resposta_com_dados_completa(self, handler):
        """Resposta com dados concretos é completa."""
        resposta = """
        Tenho uma vaga ótima pra você!
        Hospital São Luiz, dia 15/01, das 19h às 7h
        Valor: R$ 2.500,00
        """
        assert handler.resposta_parece_incompleta(resposta) is False

    def test_tem_dados_concretos_valor(self, handler):
        """Deve detectar valores monetários."""
        assert handler._tem_dados_concretos("R$ 2.500") is True
        assert handler._tem_dados_concretos("R$1500,00") is True

    def test_tem_dados_concretos_data(self, handler):
        """Deve detectar datas."""
        assert handler._tem_dados_concretos("dia 15/01") is True
        assert handler._tem_dados_concretos("no dia 20") is True

    def test_tem_dados_concretos_horario(self, handler):
        """Deve detectar horários."""
        assert handler._tem_dados_concretos("19h às 7h") is True
        assert handler._tem_dados_concretos("das 08:00 às 18:00") is True

    def test_resposta_normal_completa(self, handler):
        """Resposta normal sem promessa é completa."""
        assert handler.resposta_parece_incompleta(
            "Olá! Tudo bem? Sou a Julia da Revoluna."
        ) is False
```

5. **Rodar todos os testes:**
   ```bash
   uv run pytest tests/services/julia/ -v
   ```

#### Definition of Done (DoD)

- [ ] `tests/services/julia/test_context_builder.py` criado com 5+ testes
- [ ] `tests/services/julia/test_tool_executor.py` criado com 5+ testes
- [ ] `tests/services/julia/test_response_handler.py` criado com 8+ testes
- [ ] Todos os testes passando
- [ ] Cobertura > 80% nos novos módulos
- [ ] Commit: `test(julia): testes dos componentes decompostos`

---

## Checklist Final do Epic

- [ ] **S31.E2.1** - Estrutura do módulo criada
- [ ] **S31.E2.2** - ContextBuilder extraído
- [ ] **S31.E2.3** - ToolExecutor extraído
- [ ] **S31.E2.4** - ResponseHandler extraído
- [ ] **S31.E2.5** - Orchestrator criado (< 100 linhas)
- [ ] **S31.E2.6** - Migração para novo orchestrator
- [ ] **S31.E2.7** - Testes criados
- [ ] `gerar_resposta_julia()` original tem < 100 linhas (ou removida)
- [ ] Todos os testes passando
- [ ] Nenhuma regressão

---

## Métricas de Sucesso

| Métrica | Antes | Depois |
|---------|-------|--------|
| Linhas em `gerar_resposta_julia()` | ~350 | < 100 |
| Funções > 50 linhas | 3 | 0 |
| Código duplicado (tool loop) | 2x | 1x |
| Testes unitários de componentes | 0 | 15+ |

---

## Arquivos Criados/Modificados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `app/services/julia/__init__.py` | Criar | ~30 |
| `app/services/julia/models.py` | Criar | ~80 |
| `app/services/julia/context_builder.py` | Criar | ~150 |
| `app/services/julia/tool_executor.py` | Criar | ~180 |
| `app/services/julia/response_handler.py` | Criar | ~150 |
| `app/services/julia/orchestrator.py` | Criar | ~130 |
| `app/services/agente.py` | Modificar | Reduzir ~250 linhas |
| `tests/services/julia/*.py` | Criar | ~300 |
| **Total novo** | | **~1020** |
| **Total removido** | | **~250** |
