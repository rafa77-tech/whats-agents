# E02: PromptBuilder com Contexto de Campanha

**Fase:** 1 - Foundation
**Estimativa:** 4h
**Prioridade:** Alta
**Dependências:** E01 (Prompts por Tipo)

---

## Objetivo

Refatorar o `PromptBuilder` para receber e injetar contexto de campanha nos prompts, permitindo que Julia saiba o tipo de campanha e suas regras específicas.

## Problema Atual

```python
# Atual - PromptBuilder não recebe contexto de campanha
async def construir_prompt_julia(
    primeira_msg: bool = False,
    diretrizes: str = "",
    contexto_conversa: str = "",
    ...
)
```

O PromptBuilder atual:
- Não sabe o tipo de campanha
- Não injeta escopo de vagas
- Não injeta margem de negociação
- Usa o mesmo prompt para todos os tipos

---

## Solução

Adicionar parâmetros de contexto de campanha ao PromptBuilder:

```python
async def construir_prompt_julia(
    # Novos parâmetros de campanha
    campaign_type: str = None,        # discovery | oferta | followup | feedback | reativacao
    campaign_objective: str = None,   # Objetivo em linguagem natural
    campaign_rules: list[str] = None, # Regras específicas
    offer_scope: dict = None,         # Escopo de vagas (se tipo=oferta)
    negotiation_margin: dict = None,  # Margem de negociação
    # Parâmetros existentes
    primeira_msg: bool = False,
    diretrizes: str = "",
    ...
)
```

---

## Tarefas

### T1: Mapear estrutura atual do PromptBuilder (30min)

**Arquivo:** `app/prompts/builder.py`

**Ação:** Ler e entender a estrutura atual antes de modificar.

**Checklist:**
- [ ] Identificar função principal `construir_prompt_julia()`
- [ ] Listar todos os parâmetros atuais
- [ ] Identificar onde os prompts são buscados do banco
- [ ] Identificar onde as injeções acontecem (diretrizes, contexto, etc.)
- [ ] Documentar fluxo atual em comentário

### T2: Adicionar parâmetros de campanha à função (30min)

**Arquivo:** `app/prompts/builder.py`

**Modificação:**

```python
from typing import Optional, Literal

CampaignType = Literal["discovery", "oferta", "followup", "feedback", "reativacao"]

async def construir_prompt_julia(
    # === NOVOS: Contexto de Campanha ===
    campaign_type: Optional[CampaignType] = None,
    campaign_objective: Optional[str] = None,
    campaign_rules: Optional[list[str]] = None,
    offer_scope: Optional[dict] = None,
    negotiation_margin: Optional[dict] = None,

    # === EXISTENTES (manter compatibilidade) ===
    primeira_msg: bool = False,
    diretrizes: str = "",
    contexto_conversa: str = "",
    memoria_medico: str = "",
    conhecimento_relevante: str = "",
    tools_disponiveis: list[str] = None,
) -> str:
```

**Regra:** Manter todos os parâmetros existentes com valores default para não quebrar chamadas atuais.

### T3: Implementar seleção de prompt por tipo (45min)

**Arquivo:** `app/prompts/builder.py`

**Lógica:**

```python
async def _selecionar_prompt_base(
    campaign_type: Optional[str],
    primeira_msg: bool
) -> str:
    """
    Seleciona o prompt base correto.

    Prioridade:
    1. Se campaign_type definido → usa julia_{campaign_type}
    2. Se primeira_msg=True → usa julia_primeira_msg (legado)
    3. Senão → usa julia_base
    """
    if campaign_type:
        prompt = await buscar_prompt_por_tipo_campanha(campaign_type)
        if prompt:
            return prompt
        logger.warning(f"Prompt julia_{campaign_type} não encontrado, usando fallback")

    # Fallback para comportamento legado
    if primeira_msg:
        return await buscar_prompt("julia_primeira_msg")

    return await buscar_prompt("julia_base")
```

### T4: Implementar injeção de escopo de vagas (45min)

**Arquivo:** `app/prompts/builder.py`

**Lógica:**

```python
def _formatar_escopo_vagas(offer_scope: Optional[dict]) -> str:
    """
    Formata escopo de vagas para injeção no prompt.

    Args:
        offer_scope: Dict com filtros de vagas

    Returns:
        String formatada para o prompt

    Exemplo de input:
        {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31",
            "hospital_id": None,
            "regiao": "grande_sp"
        }

    Exemplo de output:
        "ESCOPO PERMITIDO:
        - Especialidade: Cardiologia
        - Período: 01/03/2026 a 31/03/2026
        - Região: Grande SP
        - Hospital: Qualquer hospital disponível"
    """
    if not offer_scope:
        return "ESCOPO: Nenhum escopo definido - NÃO oferte vagas."

    linhas = ["ESCOPO PERMITIDO:"]

    if offer_scope.get("especialidade"):
        linhas.append(f"- Especialidade: {offer_scope['especialidade'].title()}")

    if offer_scope.get("periodo_inicio") and offer_scope.get("periodo_fim"):
        inicio = _formatar_data(offer_scope["periodo_inicio"])
        fim = _formatar_data(offer_scope["periodo_fim"])
        linhas.append(f"- Período: {inicio} a {fim}")

    if offer_scope.get("hospital_id"):
        # Buscar nome do hospital
        hospital_nome = await _buscar_nome_hospital(offer_scope["hospital_id"])
        linhas.append(f"- Hospital: {hospital_nome}")
    else:
        linhas.append("- Hospital: Qualquer hospital disponível")

    if offer_scope.get("regiao"):
        linhas.append(f"- Região: {offer_scope['regiao']}")

    linhas.append("")
    linhas.append("IMPORTANTE: Só apresente vagas que estejam DENTRO deste escopo.")

    return "\n".join(linhas)


def _formatar_data(data_iso: str) -> str:
    """Converte 2026-03-01 para 01/03/2026."""
    from datetime import datetime
    dt = datetime.fromisoformat(data_iso)
    return dt.strftime("%d/%m/%Y")
```

### T5: Implementar injeção de margem de negociação (30min)

**Arquivo:** `app/prompts/builder.py`

**Lógica:**

```python
def _formatar_margem_negociacao(negotiation_margin: Optional[dict]) -> str:
    """
    Formata margem de negociação para injeção no prompt.

    Args:
        negotiation_margin: Dict com regras de negociação

    Exemplo de input:
        {
            "tipo": "percentual",
            "valor": 15,
            "escopo": "vaga",
            "vaga_id": 123
        }
        ou
        {
            "tipo": "valor_maximo",
            "valor": 3000,
            "escopo": "medico",
            "cliente_id": "uuid"
        }

    Exemplo de output:
        "MARGEM DE NEGOCIAÇÃO:
        Você pode negociar até 15% acima do valor base.
        Se o médico pedir desconto ou aumento, pode oferecer até esse limite.
        Acima disso, diga que precisa confirmar com a supervisão."
    """
    if not negotiation_margin:
        return (
            "MARGEM DE NEGOCIAÇÃO: Não definida.\n"
            "Se o médico pedir negociação de valor, diga que o valor é fechado.\n"
            "Se ele insistir muito, acione o canal de ajuda."
        )

    tipo = negotiation_margin.get("tipo")
    valor = negotiation_margin.get("valor")

    if tipo == "percentual":
        return (
            f"MARGEM DE NEGOCIAÇÃO:\n"
            f"Você pode negociar até {valor}% acima do valor base.\n"
            f"Se o médico pedir aumento, pode oferecer até esse limite.\n"
            f"Acima disso, diga que precisa confirmar com a supervisão."
        )
    elif tipo == "valor_maximo":
        return (
            f"MARGEM DE NEGOCIAÇÃO:\n"
            f"Você pode negociar até R$ {valor:,.2f}.\n"
            f"Se o médico pedir mais que isso, diga que precisa confirmar."
        )
    else:
        return "MARGEM DE NEGOCIAÇÃO: Formato não reconhecido. Não negocie valores."
```

### T6: Integrar injeções no prompt final (45min)

**Arquivo:** `app/prompts/builder.py`

**Lógica de montagem:**

```python
async def construir_prompt_julia(
    campaign_type: Optional[CampaignType] = None,
    campaign_objective: Optional[str] = None,
    campaign_rules: Optional[list[str]] = None,
    offer_scope: Optional[dict] = None,
    negotiation_margin: Optional[dict] = None,
    primeira_msg: bool = False,
    diretrizes: str = "",
    contexto_conversa: str = "",
    memoria_medico: str = "",
    conhecimento_relevante: str = "",
    tools_disponiveis: list[str] = None,
) -> str:
    """
    Constrói prompt completo para Julia.

    Ordem de montagem:
    1. Prompt base (por tipo de campanha ou legado)
    2. Objetivo da campanha (se definido)
    3. Escopo de vagas (se tipo=oferta)
    4. Margem de negociação (se definida)
    5. Regras específicas (se definidas)
    6. Diretrizes do gestor
    7. Memória do médico
    8. Conhecimento relevante
    9. Contexto da conversa
    10. Tools disponíveis
    """

    partes = []

    # 1. Prompt base
    prompt_base = await _selecionar_prompt_base(campaign_type, primeira_msg)
    partes.append(prompt_base)

    # 2. Objetivo da campanha
    if campaign_objective:
        partes.append(f"\n## OBJETIVO DESTA CONVERSA\n{campaign_objective}")

    # 3. Escopo de vagas (só para ofertas)
    if campaign_type == "oferta" and offer_scope:
        partes.append(f"\n## {_formatar_escopo_vagas(offer_scope)}")

    # 4. Margem de negociação
    if negotiation_margin:
        partes.append(f"\n## {_formatar_margem_negociacao(negotiation_margin)}")

    # 5. Regras específicas da campanha
    if campaign_rules:
        regras_formatadas = "\n".join(f"- {r}" for r in campaign_rules)
        partes.append(f"\n## REGRAS ESPECÍFICAS\n{regras_formatadas}")

    # 6-10. Injeções existentes (manter comportamento atual)
    if diretrizes:
        partes.append(f"\n## DIRETRIZES DO GESTOR\n{diretrizes}")

    if memoria_medico:
        partes.append(f"\n## MEMÓRIA SOBRE ESTE MÉDICO\n{memoria_medico}")

    if conhecimento_relevante:
        partes.append(f"\n## CONHECIMENTO RELEVANTE\n{conhecimento_relevante}")

    if contexto_conversa:
        partes.append(f"\n## CONTEXTO DA CONVERSA\n{contexto_conversa}")

    if tools_disponiveis:
        tools_str = ", ".join(tools_disponiveis)
        partes.append(f"\n## TOOLS DISPONÍVEIS\n{tools_str}")

    return "\n".join(partes)
```

### T7: Criar testes unitários (45min)

**Arquivo:** `tests/unit/test_promptbuilder_campanha.py`

```python
import pytest
from app.prompts.builder import (
    construir_prompt_julia,
    _formatar_escopo_vagas,
    _formatar_margem_negociacao,
)

class TestPromptBuilderCampanha:
    """Testes para PromptBuilder com contexto de campanha."""

    @pytest.mark.asyncio
    async def test_prompt_com_campaign_type_discovery(self):
        """Deve usar prompt de discovery quando tipo definido."""
        prompt = await construir_prompt_julia(campaign_type="discovery")
        assert "NÃO mencione vagas" in prompt

    @pytest.mark.asyncio
    async def test_prompt_com_campaign_type_oferta(self):
        """Deve usar prompt de oferta quando tipo definido."""
        prompt = await construir_prompt_julia(campaign_type="oferta")
        assert "buscar_vagas()" in prompt

    @pytest.mark.asyncio
    async def test_prompt_sem_campaign_type_usa_legado(self):
        """Sem campaign_type, deve usar comportamento legado."""
        prompt = await construir_prompt_julia(primeira_msg=True)
        # Deve usar julia_primeira_msg
        assert prompt is not None

    @pytest.mark.asyncio
    async def test_escopo_vagas_injetado_em_oferta(self):
        """Escopo de vagas deve ser injetado em campanhas de oferta."""
        escopo = {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31",
        }
        prompt = await construir_prompt_julia(
            campaign_type="oferta",
            offer_scope=escopo
        )
        assert "Cardiologia" in prompt
        assert "01/03/2026" in prompt
        assert "31/03/2026" in prompt

    @pytest.mark.asyncio
    async def test_margem_negociacao_percentual(self):
        """Margem percentual deve ser formatada corretamente."""
        margem = {"tipo": "percentual", "valor": 15}
        prompt = await construir_prompt_julia(
            campaign_type="oferta",
            negotiation_margin=margem
        )
        assert "15%" in prompt

    @pytest.mark.asyncio
    async def test_margem_negociacao_valor_maximo(self):
        """Margem com valor máximo deve ser formatada corretamente."""
        margem = {"tipo": "valor_maximo", "valor": 3000}
        prompt = await construir_prompt_julia(
            campaign_type="oferta",
            negotiation_margin=margem
        )
        assert "R$ 3" in prompt or "3.000" in prompt

    @pytest.mark.asyncio
    async def test_sem_margem_nao_negocia(self):
        """Sem margem definida, prompt deve dizer para não negociar."""
        prompt = await construir_prompt_julia(campaign_type="oferta")
        assert "valor é fechado" in prompt.lower() or "não definida" in prompt.lower()

    @pytest.mark.asyncio
    async def test_regras_especificas_injetadas(self):
        """Regras específicas devem aparecer no prompt."""
        regras = [
            "Só ofertar vagas acima de R$ 2.000",
            "Priorizar plantões noturnos"
        ]
        prompt = await construir_prompt_julia(
            campaign_type="oferta",
            campaign_rules=regras
        )
        assert "R$ 2.000" in prompt
        assert "noturnos" in prompt

    @pytest.mark.asyncio
    async def test_objetivo_campanha_injetado(self):
        """Objetivo da campanha deve aparecer no prompt."""
        prompt = await construir_prompt_julia(
            campaign_type="oferta",
            campaign_objective="Apresentar vagas de cardiologia para março"
        )
        assert "cardiologia" in prompt.lower()
        assert "março" in prompt.lower()


class TestFormatadores:
    """Testes para funções de formatação."""

    def test_formatar_escopo_vagas_completo(self):
        """Deve formatar escopo com todos os campos."""
        escopo = {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31",
            "regiao": "grande_sp"
        }
        resultado = _formatar_escopo_vagas(escopo)
        assert "Cardiologia" in resultado
        assert "Grande_sp" in resultado or "grande_sp" in resultado

    def test_formatar_escopo_vagas_vazio(self):
        """Escopo vazio deve retornar mensagem de bloqueio."""
        resultado = _formatar_escopo_vagas(None)
        assert "NÃO oferte" in resultado

    def test_formatar_margem_percentual(self):
        """Deve formatar margem percentual."""
        margem = {"tipo": "percentual", "valor": 10}
        resultado = _formatar_margem_negociacao(margem)
        assert "10%" in resultado

    def test_formatar_margem_valor(self):
        """Deve formatar margem com valor máximo."""
        margem = {"tipo": "valor_maximo", "valor": 2500}
        resultado = _formatar_margem_negociacao(margem)
        assert "2.500" in resultado or "2500" in resultado

    def test_formatar_margem_nula(self):
        """Margem nula deve retornar instrução de não negociar."""
        resultado = _formatar_margem_negociacao(None)
        assert "fechado" in resultado.lower() or "não definida" in resultado.lower()
```

### T8: Atualizar docstrings e tipagem (30min)

**Arquivo:** `app/prompts/builder.py`

**Ações:**
- Adicionar docstrings completas em todas as funções novas
- Adicionar type hints em todos os parâmetros
- Documentar exemplos de uso nos docstrings

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Função `construir_prompt_julia()` aceita novos parâmetros**
  - [ ] `campaign_type` funciona e seleciona prompt correto
  - [ ] `campaign_objective` é injetado no prompt
  - [ ] `campaign_rules` são injetadas como lista
  - [ ] `offer_scope` é formatado e injetado (só em ofertas)
  - [ ] `negotiation_margin` é formatado e injetado

- [ ] **Compatibilidade mantida**
  - [ ] Chamadas sem novos parâmetros continuam funcionando
  - [ ] `primeira_msg=True` ainda usa `julia_primeira_msg`
  - [ ] Nenhum teste existente quebrou

- [ ] **Formatadores funcionam**
  - [ ] `_formatar_escopo_vagas()` formata corretamente
  - [ ] `_formatar_margem_negociacao()` formata percentual e valor
  - [ ] Valores None retornam mensagens de fallback

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_promptbuilder_campanha.py -v` = OK
  - [ ] Testes existentes do builder continuam passando

- [ ] **Tipagem e documentação**
  - [ ] Type hints em todos os parâmetros novos
  - [ ] Docstrings com exemplos

### Verificação Manual

```python
# Testar no console
from app.prompts.builder import construir_prompt_julia

# Teste 1: Discovery
prompt = await construir_prompt_julia(campaign_type="discovery")
print("=== DISCOVERY ===")
print(prompt[:500])

# Teste 2: Oferta com escopo
prompt = await construir_prompt_julia(
    campaign_type="oferta",
    offer_scope={"especialidade": "cardiologia", "regiao": "sp"},
    negotiation_margin={"tipo": "percentual", "valor": 15}
)
print("=== OFERTA ===")
print(prompt[:500])
```

---

## Notas para o Desenvolvedor

1. **Compatibilidade é crítica:**
   - Não remova nenhum parâmetro existente
   - Todos os novos parâmetros devem ter valor default
   - Teste chamadas existentes do codebase

2. **Ordem das injeções importa:**
   - O prompt base vem primeiro
   - Contexto de campanha logo após
   - Diretrizes do gestor podem sobrescrever regras

3. **Cuidados com formatação:**
   - Não usar markdown complexo nos prompts
   - Quebras de linha claras entre seções
   - Médico vê texto puro no WhatsApp

4. **Performance:**
   - `buscar_prompt_por_tipo_campanha()` faz query no banco
   - Considerar cache se necessário (mas prompts têm cache de 5min)
