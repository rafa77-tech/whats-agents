# Epic 02: Consolidacao Slack

## Objetivo

Consolidar e reorganizar os 5 arquivos relacionados ao Slack, eliminando redundancia e criando estrutura clara.

## Problema Atual

### Arquivos Slack Existentes

| Arquivo | Linhas | Responsabilidade |
|---------|--------|------------------|
| `slack.py` | 299 | Envio basico de mensagens |
| `slack_formatter.py` | 543 | Formatacao (26 funcoes!) |
| `slack_comandos.py` | 180 | Parsing de comandos |
| `agente_slack.py` | 572 | Agente conversacional |
| `tools/slack_tools.py` | 1196 | 14 tools de gestao |

**Total:** 2790 linhas em 5 arquivos

### Problemas Identificados

1. **Formatacao duplicada:** `slack.py` reimplementa `formatar_data()` que existe em `slack_formatter.py`

2. **`slack_formatter.py` eh um "utility dump":** 26 funcoes sem organizacao
   - Primitivos: `bold()`, `code()`, `lista()`
   - Templates: `template_metricas()`, `template_medico()`
   - Conversoes: `formatar_telefone()`, `formatar_valor()`

3. **`agente_slack.py` monolitico:** Classe com 13 metodos, system prompt hardcoded

4. **`slack_tools.py` gigante:** 1196 linhas, 14 tools, impossivel navegar

---

## Stories

### S10.E2.1: Reorganizar slack_formatter.py

**Objetivo:** Quebrar `slack_formatter.py` (543 linhas) em modulos menores e organizados.

**Nova Estrutura:**

```
app/services/slack/
├── __init__.py           # Re-exports publicos
├── client.py             # Cliente Slack (antigo slack.py)
├── formatter/
│   ├── __init__.py       # Re-exports
│   ├── primitives.py     # bold, code, lista, quote (~50 linhas)
│   ├── converters.py     # formatar_telefone, formatar_data, formatar_valor (~80 linhas)
│   └── templates.py      # template_metricas, template_medico, etc (~300 linhas)
├── agent.py              # Agente conversacional (antigo agente_slack.py)
└── commands.py           # Parser de comandos (antigo slack_comandos.py)
```

**Tarefas:**

1. Criar estrutura de diretorios:
   ```bash
   mkdir -p app/services/slack/formatter
   ```

2. Criar `primitives.py` com funcoes basicas:
   ```python
   # app/services/slack/formatter/primitives.py
   """Primitivos de formatacao Slack."""

   def bold(texto: str) -> str:
       """Formata texto em negrito."""
       return f"*{texto}*"

   def italic(texto: str) -> str:
       """Formata texto em italico."""
       return f"_{texto}_"

   def code(texto: str) -> str:
       """Formata texto como codigo inline."""
       return f"`{texto}`"

   def code_block(texto: str, linguagem: str = "") -> str:
       """Formata texto como bloco de codigo."""
       return f"```{linguagem}\n{texto}\n```"

   def quote(texto: str) -> str:
       """Formata texto como citacao."""
       return f">{texto}"

   def lista(itens: list[str], ordenada: bool = False) -> str:
       """Formata lista de itens."""
       if ordenada:
           return "\n".join(f"{i+1}. {item}" for i, item in enumerate(itens))
       return "\n".join(f"• {item}" for item in itens)

   def link(url: str, texto: str) -> str:
       """Formata link clicavel."""
       return f"<{url}|{texto}>"
   ```

3. Criar `converters.py` com funcoes de conversao:
   ```python
   # app/services/slack/formatter/converters.py
   """Conversores de dados para exibicao no Slack."""

   from datetime import datetime, date
   from typing import Optional

   def formatar_telefone(telefone: str) -> str:
       """Formata telefone para exibicao.

       Args:
           telefone: Numero com ou sem formatacao

       Returns:
           Formato: (11) 99999-9999
       """
       numeros = "".join(filter(str.isdigit, telefone))
       if len(numeros) == 11:
           return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
       elif len(numeros) == 10:
           return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
       return telefone

   def formatar_data(data: datetime | date | str, formato: str = "curto") -> str:
       """Formata data para exibicao.

       Args:
           data: Data em varios formatos
           formato: "curto" (15/12), "longo" (15 de dezembro), "completo" (15/12/2024)

       Returns:
           Data formatada
       """
       if isinstance(data, str):
           data = datetime.fromisoformat(data.replace("Z", "+00:00"))

       if formato == "curto":
           return data.strftime("%d/%m")
       elif formato == "longo":
           meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
                    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
           return f"{data.day} de {meses[data.month - 1]}"
       else:  # completo
           return data.strftime("%d/%m/%Y")

   def formatar_valor(valor: float, moeda: bool = True) -> str:
       """Formata valor monetario.

       Args:
           valor: Valor numerico
           moeda: Incluir simbolo R$

       Returns:
           Valor formatado: R$ 2.500,00
       """
       formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
       return f"R$ {formatado}" if moeda else formatado

   def formatar_porcentagem(valor: float, casas: int = 1) -> str:
       """Formata valor como porcentagem."""
       return f"{valor:.{casas}f}%"
   ```

4. Criar `templates.py` com templates de dados (mover do arquivo original)

5. Atualizar imports em todos os arquivos que usam `slack_formatter`:
   ```python
   # DE:
   from app.services.slack_formatter import bold, formatar_telefone, template_metricas

   # PARA:
   from app.services.slack.formatter import bold, formatar_telefone
   from app.services.slack.formatter.templates import template_metricas
   ```

6. Manter `slack_formatter.py` original com re-exports para backward compatibility:
   ```python
   # app/services/slack_formatter.py (deprecated)
   """DEPRECATED: Use app.services.slack.formatter"""
   import warnings
   warnings.warn(
       "slack_formatter is deprecated. Use app.services.slack.formatter",
       DeprecationWarning
   )
   from app.services.slack.formatter import *
   from app.services.slack.formatter.templates import *
   ```

**Como Testar:**
```bash
# Verificar imports funcionam
python -c "from app.services.slack.formatter import bold, formatar_telefone; print(bold('teste'))"

# Rodar testes
uv run pytest tests/ -v -k "slack"
```

**DoD:**
- [x] Diretorio `app/services/slack/formatter/` criado
- [x] `primitives.py` com 8 funcoes (60 linhas)
- [x] `converters.py` com 6 funcoes (100 linhas)
- [x] `templates.py` com templates movidos (340 linhas)
- [x] `__init__.py` com re-exports
- [x] `slack_formatter.py` original com deprecation warning
- [x] Todos os testes passando (59 slack tests)
- [x] Commit: `refactor(slack): reorganiza formatter em modulos`

**Status:** 🟢 Concluida

---

### S10.E2.2: Refatorar agente_slack.py

**Objetivo:** Quebrar classe monolitica `AgenteSlack` (572 linhas) em componentes menores.

**Problema:** Classe com 13 metodos misturando:
- Gerenciamento de sessao
- Chamadas LLM
- Execucao de tools
- Formatacao de resposta

**Nova Estrutura:**

```python
# app/services/slack/agent.py (~200 linhas)
class AgenteSlack:
    """Orquestrador principal do agente."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.tool_executor = ToolExecutor()
        self.llm_client = LLMClient()

    async def processar_mensagem(self, user_id: str, texto: str) -> str:
        """Processa mensagem do usuario."""
        sessao = await self.session_manager.carregar(user_id)
        contexto = self._preparar_contexto(sessao)
        resposta = await self.llm_client.gerar_resposta(texto, contexto)
        return await self._processar_resposta(resposta, sessao)


# app/services/slack/session.py (~100 linhas)
class SessionManager:
    """Gerencia sessoes de conversa."""

    async def carregar(self, user_id: str) -> dict:
        """Carrega ou cria sessao."""
        pass

    async def salvar(self, user_id: str, sessao: dict) -> None:
        """Salva sessao."""
        pass

    async def adicionar_mensagem(self, sessao: dict, msg: dict) -> None:
        """Adiciona mensagem ao historico."""
        pass


# app/services/slack/tool_executor.py (~150 linhas)
class ToolExecutor:
    """Executa tools do agente."""

    async def executar(self, tool_name: str, params: dict) -> dict:
        """Executa uma tool."""
        pass

    async def validar_params(self, tool_name: str, params: dict) -> bool:
        """Valida parametros da tool."""
        pass
```

**Tarefas:**

1. Criar `app/services/slack/session.py`:
   - Extrair metodos `_carregar_sessao`, `_salvar_sessao`
   - Criar classe `SessionManager`

2. Criar `app/services/slack/tool_executor.py`:
   - Extrair metodos `_executar_tool`, `_processar_resultado_tool`
   - Criar classe `ToolExecutor`

3. Refatorar `agente_slack.py` -> `app/services/slack/agent.py`:
   - Usar composicao com `SessionManager` e `ToolExecutor`
   - Manter apenas orquestracao no `AgenteSlack`

4. Mover system prompt para arquivo separado:
   ```python
   # app/services/slack/prompts.py
   SYSTEM_PROMPT_AGENTE_SLACK = """
   Voce eh a Julia...
   """
   ```

5. Atualizar imports:
   ```python
   # DE:
   from app.services.agente_slack import AgenteSlack

   # PARA:
   from app.services.slack import AgenteSlack
   ```

**Como Testar:**
```bash
# Teste unitario de cada componente
uv run pytest tests/test_slack_session.py -v
uv run pytest tests/test_slack_tool_executor.py -v
uv run pytest tests/test_agente_slack.py -v
```

**DoD:**
- [ ] `session.py` criado com `SessionManager` (~100 linhas)
- [ ] `tool_executor.py` criado com `ToolExecutor` (~150 linhas)
- [ ] `agent.py` refatorado usando composicao (~200 linhas)
- [ ] `prompts.py` com system prompt extraido
- [ ] Nenhum metodo > 50 linhas
- [ ] Testes para cada componente
- [ ] Todos os testes passando
- [ ] Commit: `refactor(slack): quebra AgenteSlack em componentes`

---

### S10.E2.3: Quebrar slack_tools.py

**Objetivo:** Dividir `slack_tools.py` (1196 linhas, 14 tools) em arquivos menores por categoria.

**Nova Estrutura:**

```
app/tools/slack/
├── __init__.py           # Re-exports: ALL_SLACK_TOOLS
├── metricas.py           # TOOL_METRICAS, TOOL_COMPARAR_PERIODOS (~200 linhas)
├── medicos.py            # TOOL_LISTAR_MEDICOS, TOOL_BUSCAR_MEDICO, TOOL_BLOQUEAR (~250 linhas)
├── mensagens.py          # TOOL_ENVIAR_MENSAGEM, TOOL_HISTORICO (~200 linhas)
├── vagas.py              # TOOL_LISTAR_VAGAS, TOOL_RESERVAR (~200 linhas)
├── campanhas.py          # TOOL_CRIAR_CAMPANHA, TOOL_STATUS_CAMPANHA (~200 linhas)
└── sistema.py            # TOOL_STATUS_SISTEMA, TOOL_CONFIGURAR (~150 linhas)
```

**Tarefas:**

1. Criar diretorio:
   ```bash
   mkdir -p app/tools/slack
   ```

2. Identificar e agrupar tools por categoria:
   ```python
   # Metricas
   TOOL_METRICAS
   TOOL_COMPARAR_PERIODOS

   # Medicos
   TOOL_LISTAR_MEDICOS
   TOOL_BUSCAR_MEDICO
   TOOL_BLOQUEAR_MEDICO
   TOOL_DESBLOQUEAR_MEDICO

   # Mensagens
   TOOL_ENVIAR_MENSAGEM
   TOOL_HISTORICO_CONVERSA

   # Vagas
   TOOL_LISTAR_VAGAS
   TOOL_RESERVAR_VAGA

   # Campanhas
   TOOL_CRIAR_CAMPANHA
   TOOL_STATUS_CAMPANHA

   # Sistema
   TOOL_STATUS_SISTEMA
   TOOL_CONFIGURAR
   ```

3. Criar cada arquivo com suas tools

4. Criar `__init__.py` com agregacao:
   ```python
   # app/tools/slack/__init__.py
   from .metricas import TOOL_METRICAS, TOOL_COMPARAR_PERIODOS
   from .medicos import TOOL_LISTAR_MEDICOS, TOOL_BUSCAR_MEDICO, TOOL_BLOQUEAR_MEDICO
   from .mensagens import TOOL_ENVIAR_MENSAGEM, TOOL_HISTORICO_CONVERSA
   from .vagas import TOOL_LISTAR_VAGAS, TOOL_RESERVAR_VAGA
   from .campanhas import TOOL_CRIAR_CAMPANHA, TOOL_STATUS_CAMPANHA
   from .sistema import TOOL_STATUS_SISTEMA, TOOL_CONFIGURAR

   ALL_SLACK_TOOLS = [
       TOOL_METRICAS,
       TOOL_COMPARAR_PERIODOS,
       TOOL_LISTAR_MEDICOS,
       # ... todas as tools
   ]
   ```

5. Atualizar imports em `agente_slack.py`:
   ```python
   # DE:
   from app.tools.slack_tools import SLACK_TOOLS

   # PARA:
   from app.tools.slack import ALL_SLACK_TOOLS
   ```

6. Manter arquivo original com deprecation:
   ```python
   # app/tools/slack_tools.py (deprecated)
   import warnings
   warnings.warn("Use app.tools.slack", DeprecationWarning)
   from app.tools.slack import *
   ```

**Como Testar:**
```bash
# Verificar que todas as tools estao acessiveis
python -c "from app.tools.slack import ALL_SLACK_TOOLS; print(len(ALL_SLACK_TOOLS))"

# Rodar testes
uv run pytest tests/ -v -k "slack_tools"
```

**DoD:**
- [ ] Diretorio `app/tools/slack/` criado
- [ ] 6 arquivos de tools criados
- [ ] Cada arquivo < 300 linhas
- [ ] `__init__.py` com `ALL_SLACK_TOOLS`
- [ ] Arquivo original com deprecation warning
- [ ] Todos os testes passando
- [ ] Commit: `refactor(tools): quebra slack_tools em modulos por categoria`

---

## Resumo do Epic

| Story | Objetivo | De | Para | Complexidade |
|-------|----------|-----|------|--------------|
| S10.E2.1 | Reorganizar formatter | 543 linhas | 4 arquivos (~430 linhas) | Media |
| S10.E2.2 | Refatorar agente | 572 linhas | 4 arquivos (~450 linhas) | Alta |
| S10.E2.3 | Quebrar tools | 1196 linhas | 6 arquivos (~1200 linhas) | Media |

**Ordem de Execucao:** S10.E2.1 -> S10.E2.2 -> S10.E2.3

**Resultado Esperado:**
- Antes: 5 arquivos, 2790 linhas, maximo 1196 linhas
- Depois: ~14 arquivos, ~2080 linhas, maximo ~300 linhas
