# Epic 01: Tool buscar_vagas para LLM

## Prioridade: P0 (Crítico)

## Objetivo

> **Criar tool `buscar_vagas` que permite ao LLM buscar vagas compatíveis com o perfil do médico durante a conversa.**

Atualmente, o agente só tem as tools `reservar_plantao` e `agendar_lembrete`. Falta a tool para **buscar** vagas, essencial para o Fluxo 5 (Oferta de Vaga) documentado em `docs/FLUXOS.md`.

---

## Problema

Sem a tool `buscar_vagas`, a Júlia:
1. Não consegue buscar vagas proativamente quando médico demonstra interesse
2. Depende apenas do contexto estático carregado no início da conversa
3. Não pode filtrar por preferências mencionadas pelo médico durante a conversa

---

## Referência: FLUXOS.md - Fluxo 5

```
JÚLIA                         BANCO                    MÉDICO
  │                            │                          │
  │  1. Detecta interesse      │                          │
  │     "tô procurando         │                          │
  │      plantão"              │                          │
  │                            │                          │
  │  2. Tool: buscar_vagas     │                          │
  │─────────────────────────▶│                          │
  │     • especialidade        │                          │
  │     • região (se souber)   │                          │
  │     • período preferido    │                          │
```

---

## Stories

---

# S7.E1.1 - Definir schema da tool buscar_vagas

## Objetivo

> **Criar definição da tool buscar_vagas seguindo padrão Anthropic tool_use.**

## Contexto Técnico

A tool deve permitir que o LLM:
- Busque vagas por especialidade do médico (obrigatório)
- Filtre por região se conhecida
- Filtre por período preferido (diurno/noturno)
- Filtre por valor mínimo se médico mencionou
- Limite quantidade de resultados

## Código Esperado

**Arquivo:** `app/tools/vagas.py`

```python
TOOL_BUSCAR_VAGAS = {
    "name": "buscar_vagas",
    "description": """Busca vagas de plantão compatíveis com o perfil do médico.

Use esta tool quando:
- Médico pergunta sobre vagas disponíveis
- Médico demonstra interesse em fazer plantões
- Médico especifica preferências (região, período, valor)
- Precisa verificar se há vagas antes de oferecer

A busca já considera a especialidade do médico automaticamente.
Retorna até 5 vagas ordenadas por prioridade e data.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "regiao": {
                "type": "string",
                "description": "Região/cidade para filtrar. Ex: 'ABC', 'São Paulo', 'Zona Sul'. Deixe vazio para buscar todas as regiões."
            },
            "periodo": {
                "type": "string",
                "enum": ["diurno", "noturno", "12h", "24h", "qualquer"],
                "description": "Período preferido do plantão. Use 'qualquer' se não especificado."
            },
            "valor_minimo": {
                "type": "number",
                "description": "Valor mínimo em reais se médico mencionou. Ex: 2000"
            },
            "dias_semana": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dias da semana preferidos. Ex: ['sabado', 'domingo'] ou ['semana']"
            },
            "limite": {
                "type": "integer",
                "default": 5,
                "description": "Quantidade máxima de vagas para retornar (1-10)"
            }
        },
        "required": []
    }
}
```

## Critérios de Aceite

1. **Definição válida:** Schema segue formato Anthropic tool_use
2. **Documentação clara:** Description explica quando usar
3. **Parâmetros opcionais:** Todos os filtros são opcionais
4. **Tipos corretos:** `periodo` é enum, `valor_minimo` é number
5. **Limite padrão:** Default de 5 vagas se não especificado

## DoD

- [x] Constante `TOOL_BUSCAR_VAGAS` definida em `app/tools/vagas.py`
- [x] Schema validado contra especificação Anthropic
- [x] Description inclui exemplos de quando usar
- [x] Todos os parâmetros documentados
- [x] Enum `periodo` inclui opções realistas do negócio

## Testes de Validação

```python
def test_tool_schema_valido():
    from app.tools.vagas import TOOL_BUSCAR_VAGAS

    assert "name" in TOOL_BUSCAR_VAGAS
    assert TOOL_BUSCAR_VAGAS["name"] == "buscar_vagas"
    assert "input_schema" in TOOL_BUSCAR_VAGAS
    assert "properties" in TOOL_BUSCAR_VAGAS["input_schema"]

def test_tool_tem_descricao():
    from app.tools.vagas import TOOL_BUSCAR_VAGAS

    desc = TOOL_BUSCAR_VAGAS["description"]
    assert len(desc) > 50
    assert "vaga" in desc.lower()
```

---

# S7.E1.2 - Implementar handler buscar_vagas

## Objetivo

> **Criar função que executa a busca no banco quando LLM chama a tool.**

## Contexto Técnico

O handler deve:
1. Receber parâmetros da tool
2. Buscar vagas no Supabase com filtros
3. Aplicar preferências do médico (hospitais bloqueados, etc)
4. Formatar resultado para retorno ao LLM
5. Tratar casos de nenhuma vaga encontrada

## Código Esperado

**Arquivo:** `app/tools/vagas.py`

```python
from datetime import date, timedelta
from app.services.supabase import supabase
from app.services.vaga import buscar_vagas_compativeis
import logging

logger = logging.getLogger(__name__)

async def handle_buscar_vagas(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
    """
    Executa busca de vagas quando LLM chama a tool.

    Args:
        tool_input: Parâmetros da tool (regiao, periodo, valor_minimo, etc)
        medico: Dados do médico da conversa
        conversa: Dados da conversa atual

    Returns:
        dict com:
        - success: bool
        - vagas: list[dict] com vagas encontradas
        - mensagem: str para o LLM contextualizar
    """
    try:
        especialidade_id = medico.get("especialidade_id")
        if not especialidade_id:
            return {
                "success": False,
                "vagas": [],
                "mensagem": "Médico não tem especialidade cadastrada. Pergunte a especialidade primeiro."
            }

        # Extrair filtros do input
        regiao = tool_input.get("regiao")
        periodo = tool_input.get("periodo", "qualquer")
        valor_minimo = tool_input.get("valor_minimo")
        dias_semana = tool_input.get("dias_semana", [])
        limite = min(tool_input.get("limite", 5), 10)

        # Buscar vagas base
        vagas = await buscar_vagas_compativeis(
            especialidade_id=especialidade_id,
            cliente_id=medico.get("id"),
            limite=limite * 2  # Busca mais para compensar filtros
        )

        # Aplicar filtros adicionais
        vagas_filtradas = []
        for vaga in vagas:
            # Filtro por região
            if regiao and not _match_regiao(vaga, regiao):
                continue

            # Filtro por período
            if periodo != "qualquer" and not _match_periodo(vaga, periodo):
                continue

            # Filtro por valor mínimo
            if valor_minimo and vaga.get("valor_max", 0) < valor_minimo:
                continue

            # Filtro por dia da semana
            if dias_semana and not _match_dia_semana(vaga, dias_semana):
                continue

            vagas_filtradas.append(vaga)

            if len(vagas_filtradas) >= limite:
                break

        # Formatar para o LLM
        vagas_formatadas = [_formatar_vaga_para_llm(v) for v in vagas_filtradas]

        if not vagas_formatadas:
            return {
                "success": True,
                "vagas": [],
                "mensagem": "Não encontrei vagas com esses critérios no momento. Posso buscar com outros filtros?"
            }

        return {
            "success": True,
            "vagas": vagas_formatadas,
            "mensagem": f"Encontrei {len(vagas_formatadas)} vaga(s) que podem interessar."
        }

    except Exception as e:
        logger.error(f"Erro ao buscar vagas: {e}", exc_info=True)
        return {
            "success": False,
            "vagas": [],
            "mensagem": "Erro ao buscar vagas. Tente novamente."
        }


def _match_regiao(vaga: dict, regiao: str) -> bool:
    """Verifica se vaga é da região especificada."""
    regiao_lower = regiao.lower()
    hospital = vaga.get("hospitais", {})

    # Checa cidade
    cidade = hospital.get("cidade", "").lower()
    if regiao_lower in cidade:
        return True

    # Checa região cadastrada
    regiao_hospital = hospital.get("regiao", "").lower()
    if regiao_lower in regiao_hospital:
        return True

    # Checa nome do hospital
    nome = hospital.get("nome", "").lower()
    if regiao_lower in nome:
        return True

    return False


def _match_periodo(vaga: dict, periodo: str) -> bool:
    """Verifica se vaga corresponde ao período desejado."""
    periodo_vaga = vaga.get("periodos", {}).get("nome", "").lower()

    if periodo == "diurno":
        return "diurno" in periodo_vaga or "12h dia" in periodo_vaga
    elif periodo == "noturno":
        return "noturno" in periodo_vaga or "12h noite" in periodo_vaga
    elif periodo == "12h":
        return "12h" in periodo_vaga
    elif periodo == "24h":
        return "24h" in periodo_vaga

    return True


def _match_dia_semana(vaga: dict, dias: list) -> bool:
    """Verifica se data da vaga cai nos dias da semana desejados."""
    data_str = vaga.get("data_plantao")
    if not data_str:
        return True

    data = date.fromisoformat(data_str)
    dia_semana = data.strftime("%A").lower()

    # Mapear português
    mapa_dias = {
        "monday": "segunda",
        "tuesday": "terca",
        "wednesday": "quarta",
        "thursday": "quinta",
        "friday": "sexta",
        "saturday": "sabado",
        "sunday": "domingo"
    }
    dia_pt = mapa_dias.get(dia_semana, dia_semana)

    # Checar se é fim de semana
    if "fds" in dias or "fim de semana" in dias:
        if dia_pt in ["sabado", "domingo"]:
            return True

    # Checar se é semana
    if "semana" in dias:
        if dia_pt not in ["sabado", "domingo"]:
            return True

    # Checar dia específico
    return dia_pt in [d.lower() for d in dias]


def _formatar_vaga_para_llm(vaga: dict) -> dict:
    """Formata vaga para retorno ao LLM de forma legível."""
    hospital = vaga.get("hospitais", {})
    periodo = vaga.get("periodos", {})

    return {
        "id": vaga["id"],
        "hospital": hospital.get("nome", "Hospital"),
        "cidade": hospital.get("cidade", ""),
        "data": vaga.get("data_plantao"),
        "periodo": periodo.get("nome", ""),
        "valor_min": vaga.get("valor_min"),
        "valor_max": vaga.get("valor_max"),
        "prioridade": vaga.get("prioridade", "normal"),
        "descricao_curta": f"{hospital.get('nome')} - {vaga.get('data_plantao')} - {periodo.get('nome')} - R${vaga.get('valor_min')}-{vaga.get('valor_max')}"
    }
```

## Critérios de Aceite

1. **Filtros funcionais:** Todos os filtros (região, período, valor, dia) aplicados
2. **Limite respeitado:** Nunca retorna mais que o limite
3. **Tratamento de erro:** Erros logados e mensagem amigável retornada
4. **Sem especialidade:** Retorna mensagem pedindo especialidade
5. **Sem vagas:** Retorna mensagem sugerindo outros filtros
6. **Performance:** Busca completa em < 500ms

## DoD

- [x] Função `handle_buscar_vagas()` implementada
- [x] Filtro por região funciona com cidade/região/nome hospital
- [x] Filtro por período funciona (diurno/noturno/12h/24h)
- [x] Filtro por valor mínimo funciona
- [x] Filtro por dia da semana funciona (inclui "fds" e "semana")
- [x] Formatação retorna dados essenciais para LLM
- [x] Logs de erro incluem contexto
- [x] Médico sem especialidade tratado gracefully

## Testes

```python
@pytest.mark.asyncio
async def test_buscar_vagas_sem_filtros():
    medico = {"id": "123", "especialidade_id": "esp_1"}
    result = await handle_buscar_vagas({}, medico, {})
    assert result["success"] == True
    assert "vagas" in result

@pytest.mark.asyncio
async def test_buscar_vagas_filtro_regiao():
    medico = {"id": "123", "especialidade_id": "esp_1"}
    result = await handle_buscar_vagas({"regiao": "ABC"}, medico, {})
    # Todas vagas devem ser da região ABC
    for vaga in result["vagas"]:
        assert "abc" in vaga["cidade"].lower() or "abc" in vaga["hospital"].lower()

@pytest.mark.asyncio
async def test_buscar_vagas_medico_sem_especialidade():
    medico = {"id": "123"}  # Sem especialidade_id
    result = await handle_buscar_vagas({}, medico, {})
    assert result["success"] == False
    assert "especialidade" in result["mensagem"].lower()
```

---

# S7.E1.3 - Registrar tool no agente

## Objetivo

> **Adicionar tool `buscar_vagas` na lista de tools disponíveis para o LLM.**

## Contexto Técnico

O LLM precisa:
1. Receber a definição da tool no `tools` parameter da API
2. Ter o handler configurado para processar quando chamar
3. Receber o resultado formatado como tool_result

## Código Esperado

**Arquivo:** `app/services/llm.py` (modificar)

```python
from app.tools.vagas import TOOL_BUSCAR_VAGAS, TOOL_RESERVAR_PLANTAO, handle_buscar_vagas, handle_reservar_plantao
from app.tools.lembrete import TOOL_AGENDAR_LEMBRETE, handle_agendar_lembrete

# Lista de tools disponíveis para o agente
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,      # Nova tool
    TOOL_RESERVAR_PLANTAO,
    TOOL_AGENDAR_LEMBRETE,
]

# Mapa de handlers
TOOL_HANDLERS = {
    "buscar_vagas": handle_buscar_vagas,
    "reservar_plantao": handle_reservar_plantao,
    "agendar_lembrete": handle_agendar_lembrete,
}
```

**Arquivo:** `app/services/agente.py` (modificar)

```python
async def processar_tool_call(
    tool_name: str,
    tool_input: dict,
    contexto: dict
) -> dict:
    """Processa chamada de tool do LLM."""

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        logger.warning(f"Tool desconhecida: {tool_name}")
        return {"error": f"Tool '{tool_name}' não encontrada"}

    return await handler(
        tool_input=tool_input,
        medico=contexto["medico"],
        conversa=contexto["conversa"]
    )
```

## Critérios de Aceite

1. **Tool listada:** `TOOL_BUSCAR_VAGAS` aparece em JULIA_TOOLS
2. **Handler mapeado:** `buscar_vagas` mapeia para `handle_buscar_vagas`
3. **Ordem correta:** `buscar_vagas` antes de `reservar_plantao` (ordem lógica)
4. **Import funciona:** Sem erros de import circular

## DoD

- [x] `TOOL_BUSCAR_VAGAS` importada em `app/services/agente.py`
- [x] Tool adicionada em `JULIA_TOOLS`
- [x] Handler adicionado em `processar_tool_call()`
- [x] `processar_tool_call()` chama handler correto
- [x] Import testado sem erros circulares
- [x] LLM recebe tool na chamada API

## Teste de Integração

```python
def test_tool_registrada():
    from app.services.llm import JULIA_TOOLS, TOOL_HANDLERS

    tool_names = [t["name"] for t in JULIA_TOOLS]
    assert "buscar_vagas" in tool_names
    assert "buscar_vagas" in TOOL_HANDLERS

@pytest.mark.asyncio
async def test_llm_recebe_tools():
    from app.services.llm import chamar_llm

    # Mock do cliente anthropic
    # Verificar que tools é passado na chamada
    pass
```

---

# S7.E1.4 - Atualizar system prompt para usar tool

## Objetivo

> **Atualizar prompt da Júlia para instruí-la a usar a tool `buscar_vagas` quando apropriado.**

## Contexto Técnico

O LLM precisa saber:
1. Quando usar a tool (médico demonstra interesse)
2. Como interpretar os resultados
3. Como apresentar as vagas de forma natural (não lista!)

## Código Esperado

**Arquivo:** `app/core/prompts.py` (adicionar seção)

```python
INSTRUCOES_TOOLS = """
## Uso de Tools

Você tem acesso às seguintes ferramentas:

### buscar_vagas
Use quando:
- Médico pergunta "tem vaga?", "o que tem de plantão?"
- Médico demonstra interesse: "to procurando", "preciso de plantão"
- Médico especifica preferências: "quero noturno", "tem no ABC?"
- Precisa verificar disponibilidade antes de oferecer

Parâmetros opcionais:
- regiao: se médico mencionou ("ABC", "zona sul", "São Paulo")
- periodo: se médico especificou ("noturno", "diurno", "12h")
- valor_minimo: se médico mencionou valor mínimo
- dias_semana: se médico especificou dias ("sabado", "fds", "semana")

IMPORTANTE: Após receber os resultados:
1. Escolha UMA vaga para apresentar (a mais relevante)
2. Apresente de forma NATURAL, nunca como lista
3. Mencione detalhes gradualmente, não tudo de uma vez

Exemplo CORRETO:
"Achei uma vaga boa pra vc! Hospital Brasil, sábado que vem, 12h diurno.
Paga R$ 2.300. O que acha?"

Exemplo ERRADO (não faça isso):
"Encontrei 3 vagas:
- Hospital Brasil: sáb 12h R$2.300
- Hospital São Luiz: dom 12h R$2.500
- Hospital ABC: seg 24h R$4.000"

### reservar_plantao
Use quando médico ACEITA a vaga:
- "Pode reservar"
- "Quero essa"
- "Fechado"
- "Aceito"

IMPORTANTE: Só reserve após confirmação CLARA do médico.

### agendar_lembrete
Use quando médico pede para falar depois:
- "Me manda msg amanhã"
- "Fala comigo às 19h"
- "Segunda a gente conversa"
"""
```

## Critérios de Aceite

1. **Instruções claras:** LLM entende quando usar cada tool
2. **Exemplos concretos:** Frases reais que ativam cada tool
3. **Anti-padrões:** Mostra o que NÃO fazer (listas)
4. **Fluxo natural:** Instrui a oferecer UMA vaga por vez
5. **Gradual:** Instrui a revelar detalhes aos poucos

## DoD

- [x] Seção de instruções para `buscar_vagas` atualizada em prompts.py
- [x] Instruções para `buscar_vagas` incluem:
  - Triggers (quando usar)
  - Parâmetros (quando passar cada um)
  - Formato de apresentação (natural, não lista)
  - Exemplo correto e incorreto
- [x] Instruções para `reservar_plantao` incluem triggers de aceite
- [x] Seção integrada no system prompt principal
- [ ] Testado com LLM - resposta segue instruções (pendente teste manual)

## Teste Manual

```
Input: "Oi Júlia, tem alguma vaga de plantão pra mim?"
Expected: Júlia chama buscar_vagas e apresenta UMA vaga naturalmente

Input: "Quero plantão noturno no ABC"
Expected: Júlia chama buscar_vagas com regiao="ABC", periodo="noturno"

Input: "Pode reservar essa"
Expected: Júlia chama reservar_plantao com a vaga oferecida
```

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E1.1 | Definir schema da tool | Baixa |
| S7.E1.2 | Implementar handler | Alta |
| S7.E1.3 | Registrar no agente | Baixa |
| S7.E1.4 | Atualizar system prompt | Média |

## Ordem de Implementação

1. S7.E1.1 - Schema (base para tudo)
2. S7.E1.2 - Handler (lógica principal)
3. S7.E1.3 - Registro (conecta ao agente)
4. S7.E1.4 - Prompt (ensina LLM a usar)

## Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `app/tools/vagas.py` | Adicionar TOOL_BUSCAR_VAGAS e handler |
| `app/services/llm.py` | Importar e registrar tool |
| `app/services/agente.py` | Garantir processamento de tool_call |
| `app/core/prompts.py` | Adicionar instruções de uso |

## Validação Final

```python
@pytest.mark.integration
async def test_fluxo_completo_buscar_vagas():
    """
    Simula conversa onde médico pede vagas.

    1. Médico: "tem plantão pra mim?"
    2. Júlia: chama buscar_vagas
    3. Júlia: apresenta UMA vaga naturalmente
    4. Médico: "pode reservar"
    5. Júlia: chama reservar_plantao
    6. Júlia: confirma reserva
    """
    pass
```
