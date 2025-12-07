# Epic 1: Sistema de Vagas

## Objetivo

> **Júlia consegue buscar, oferecer e reservar vagas para médicos.**

---

## Stories

---

# S2.E1.1 - Tool buscar_vagas_compativeis

## Objetivo

> **Criar função que busca vagas compatíveis com o perfil do médico.**

**Resultado esperado:** Função retorna vagas filtradas por especialidade, região, preferências.

## Contexto

- Vagas estão na tabela `vagas` com FK para hospitais, períodos, setores
- Médico pode ter preferências em `preferencias_detectadas`
- Ordenar por: prioridade (urgente primeiro), depois data

## Tarefas

### 1. Criar serviço de vagas

```python
# app/services/vaga.py

async def buscar_vagas_compativeis(
    especialidade_id: str,
    cliente_id: str = None,
    limite: int = 5
) -> list[dict]:
    """
    Busca vagas compatíveis com o médico.

    Filtros:
    - Especialidade do médico
    - Status = aberta
    - Data >= hoje
    - Não oferece vaga já reservada pelo mesmo médico
    - Respeita hospitais_bloqueados do médico

    Ordenação:
    - Prioridade (urgente > alta > normal)
    - Data mais próxima primeiro
    """
    query = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*)")
        .eq("especialidade_id", especialidade_id)
        .eq("status", "aberta")
        .gte("data_plantao", date.today().isoformat())
        .order("prioridade", desc=True)
        .order("data_plantao")
        .limit(limite)
    )

    response = query.execute()
    return response.data
```

### 2. Aplicar filtros de preferências

```python
def filtrar_por_preferencias(vagas: list, preferencias: dict) -> list:
    """Remove vagas incompatíveis com preferências do médico."""
    resultado = []

    hospitais_bloqueados = preferencias.get("hospitais_bloqueados", [])
    setores_bloqueados = preferencias.get("setores_bloqueados", [])
    valor_minimo = preferencias.get("valor_minimo", 0)
    turnos = preferencias.get("turnos", [])

    for v in vagas:
        # Pular hospital bloqueado
        if v["hospital_id"] in hospitais_bloqueados:
            continue

        # Pular setor bloqueado
        if v.get("setor_id") in setores_bloqueados:
            continue

        # Pular se valor abaixo do mínimo
        if v["valor_min"] < valor_minimo:
            continue

        resultado.append(v)

    return resultado
```

## DoD

- [x] Função `buscar_vagas_compativeis()` implementada
- [x] Filtro por especialidade funciona
- [x] Filtro por preferências funciona
- [x] Ordenação por prioridade e data funciona
- [x] Retorna dados completos (hospital, período, setor)

---

# S2.E1.2 - Tool reservar_plantao

## Objetivo

> **Criar função que reserva vaga para um médico.**

**Resultado esperado:** Vaga marcada como reservada, médico associado.

## Tarefas

### 1. Implementar reserva

```python
async def reservar_vaga(vaga_id: str, cliente_id: str) -> dict:
    """
    Reserva vaga para o médico.

    1. Verificar se vaga ainda está aberta
    2. Atualizar status para 'reservada'
    3. Associar cliente_id
    4. Retornar vaga atualizada
    """
    # Verificar disponibilidade
    vaga = await buscar_vaga_por_id(vaga_id)
    if vaga["status"] != "aberta":
        raise ValueError("Vaga não está mais disponível")

    # Reservar
    response = (
        supabase.table("vagas")
        .update({
            "status": "reservada",
            "cliente_id": cliente_id,
            "reservada_em": datetime.utcnow().isoformat()
        })
        .eq("id", vaga_id)
        .execute()
    )

    return response.data[0]
```

## DoD

- [x] Função `reservar_vaga()` implementada
- [x] Verifica se vaga está disponível antes
- [x] Atualiza status para "reservada"
- [x] Associa médico à vaga
- [x] Retorna erro se vaga não disponível

---

# S2.E1.3 - Verificar conflito dia/período

## Objetivo

> **Impedir que médico aceite duas vagas no mesmo dia e período.**

## Tarefas

```python
async def verificar_conflito(
    cliente_id: str,
    data: str,
    periodo_id: str
) -> bool:
    """
    Verifica se médico já tem plantão no mesmo dia/período.

    Returns:
        True se há conflito, False se pode agendar
    """
    response = (
        supabase.table("vagas")
        .select("id")
        .eq("cliente_id", cliente_id)
        .eq("data_plantao", data)
        .eq("periodo_id", periodo_id)
        .in_("status", ["reservada", "confirmada"])
        .execute()
    )

    return len(response.data) > 0
```

## DoD

- [x] Função `verificar_conflito()` implementada
- [x] Retorna True se há conflito
- [x] Considera apenas vagas reservadas/confirmadas

---

# S2.E1.4 - Notificar gestor pós-reserva

## Objetivo

> **Enviar notificação no Slack quando plantão for reservado.**

## Tarefas

```python
async def notificar_plantao_fechado(
    medico: dict,
    vaga: dict
):
    """Notifica gestor via Slack sobre plantão reservado."""
    mensagem = {
        "text": "🎉 Plantão reservado!",
        "attachments": [{
            "color": "#00ff00",
            "fields": [
                {"title": "Médico", "value": medico["primeiro_nome"], "short": True},
                {"title": "Hospital", "value": vaga["hospitais"]["nome"], "short": True},
                {"title": "Data", "value": vaga["data_plantao"], "short": True},
                {"title": "Valor", "value": f"R$ {vaga['valor_min']}", "short": True},
            ]
        }]
    }

    await enviar_slack(mensagem)
```

## DoD

- [x] Notificação enviada ao Slack após reserva
- [x] Inclui dados do médico e vaga
- [x] Formato legível e com cor verde

---

# S2.E1.5 - Integrar vagas no fluxo do agente

## Objetivo

> **Fazer Júlia oferecer vagas naturalmente na conversa.**

## Tarefas

### 1. Atualizar contexto do agente

No serviço de contexto, adicionar busca de vagas:

```python
async def montar_contexto_completo(medico, conversa, incluir_vagas=True):
    # ... código existente ...

    vagas = []
    if incluir_vagas and medico.get("especialidade_id"):
        vagas = await buscar_vagas_compativeis(
            medico["especialidade_id"],
            cliente_id=medico["id"]
        )

    return {
        # ... outros campos ...
        "vagas": formatar_contexto_vagas(vagas),
        "vagas_raw": vagas,
    }
```

### 2. Atualizar prompt para oferecer vagas

Adicionar no system prompt:

```
Se o médico mostrar interesse em plantão:
1. Olhe as vagas disponíveis no contexto
2. Escolha UMA vaga para oferecer (a mais relevante)
3. Apresente de forma natural, não como lista
4. Exemplo: "Achei uma vaga boa no Hospital Brasil, sábado, diurno, R$ 2.300. O que acha?"
```

### 3. Detectar aceite do médico

Júlia deve reconhecer quando médico aceita:
- "Pode reservar"
- "Quero essa"
- "Fechado"
- "Aceito"

E então chamar a função de reserva.

## DoD

- [x] Vagas aparecem no contexto do agente
- [x] Júlia oferece vaga quando médico mostra interesse
- [x] Oferta é natural (não lista)
- [x] Médico pode aceitar verbalmente
- [x] Aceite gera reserva no banco

---

# S2.E1.6 - Tool agendar_lembrete

## Objetivo

> **Permitir que Júlia agende lembretes quando médico pedir para falar depois.**

**Resultado esperado:** Quando médico diz "me manda msg amanhã às 10h", Júlia agenda automaticamente e retoma no horário.

## Contexto

Médicos frequentemente pedem para ser contactados em outro momento:
- "To em cirurgia, me manda msg às 19h"
- "Amanhã de manhã falo contigo"
- "Segunda-feira me liga"
- "Depois do almoço"

Sem esse recurso, perdemos oportunidades de venda. Uma escalista real anotaria na agenda.

**Abordagem:** Usar tool calling da LLM. A própria IA detecta o pedido e extrai data/hora, sem necessidade de regex ou parser externo.

## Tarefas

### 1. Definir a tool

```python
# app/tools/lembrete.py

TOOL_AGENDAR_LEMBRETE = {
    "name": "agendar_lembrete",
    "description": """Agenda lembrete para entrar em contato com o médico em data/hora específica.

Use quando o médico pedir para falar depois, amanhã, em outro horário, etc.
Exemplos de quando usar:
- "me manda msg amanhã às 10h"
- "fala comigo à noite"
- "segunda-feira de manhã"
- "depois das 18h"
- "semana que vem"

IMPORTANTE: Converta a solicitação para data/hora ISO considerando a data atual.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_hora": {
                "type": "string",
                "description": "Data e hora para o lembrete no formato ISO (YYYY-MM-DDTHH:MM). Considere a data/hora atual para calcular datas relativas como 'amanhã' ou 'segunda-feira'."
            },
            "contexto": {
                "type": "string",
                "description": "Breve descrição do que estava sendo discutido (ex: 'vaga no Hospital Brasil', 'interesse em plantão noturno')"
            },
            "mensagem_retorno": {
                "type": "string",
                "description": "Mensagem personalizada para enviar no momento do lembrete. Deve ser natural e retomar o contexto."
            }
        },
        "required": ["data_hora", "contexto"]
    }
}
```

### 2. Implementar handler da tool

```python
# app/services/tools.py

from app.services.fila import fila_service
from datetime import datetime

async def handle_agendar_lembrete(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
    """
    Processa chamada da tool agendar_lembrete.

    1. Valida data/hora (não pode ser no passado)
    2. Gera mensagem de retorno se não fornecida
    3. Enfileira na fila de mensagens
    """
    data_hora_str = tool_input["data_hora"]
    contexto = tool_input["contexto"]

    # Parsear data/hora
    try:
        data_hora = datetime.fromisoformat(data_hora_str)
    except ValueError:
        return {"success": False, "error": "Data/hora inválida"}

    # Validar que não é no passado
    if data_hora < datetime.now():
        return {"success": False, "error": "Data/hora no passado"}

    # Mensagem de retorno
    mensagem = tool_input.get("mensagem_retorno")
    if not mensagem:
        mensagem = (
            f"Oi {medico['primeiro_nome']}! Conforme combinamos, "
            f"to passando pra gente continuar sobre {contexto}. "
            f"Agora tá melhor pra vc?"
        )

    # Enfileirar
    await fila_service.enfileirar(
        cliente_id=medico["id"],
        conversa_id=conversa["id"],
        conteudo=mensagem,
        tipo="lembrete_solicitado",
        prioridade=7,  # Prioridade alta (médico pediu!)
        agendar_para=data_hora,
        metadata={
            "contexto": contexto,
            "solicitado_em": datetime.now().isoformat()
        }
    )

    return {
        "success": True,
        "agendado_para": data_hora.strftime("%d/%m às %H:%M")
    }
```

### 3. Registrar tool no agente

```python
# app/services/agente.py (adicionar)

from app.tools.lembrete import TOOL_AGENDAR_LEMBRETE

TOOLS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_AGENDAR_LEMBRETE,  # ← Nova tool
]

async def processar_tool_call(tool_name: str, tool_input: dict, contexto: dict):
    """Processa chamadas de tools."""

    if tool_name == "agendar_lembrete":
        return await handle_agendar_lembrete(
            tool_input,
            medico=contexto["medico"],
            conversa=contexto["conversa"]
        )

    # ... outras tools ...
```

### 4. Adicionar data atual no contexto

```python
# app/services/contexto.py (adicionar)

from datetime import datetime

def montar_contexto_completo(medico, conversa):
    return {
        # ... outros campos ...

        # Data atual para a LLM calcular "amanhã", "segunda", etc.
        "data_hora_atual": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dia_semana_atual": datetime.now().strftime("%A"),  # "Monday", "Tuesday"...
    }
```

### 5. Atualizar system prompt

Adicionar no prompt:

```
## Lembretes

Se o médico pedir para falar em outro momento (amanhã, mais tarde, segunda-feira, etc):
1. Use a tool `agendar_lembrete` para agendar
2. Confirme o agendamento de forma natural
3. Exemplo: "Fechado! Te mando msg amanhã às 10h então 👍"

Data/hora atual: {data_hora_atual} ({dia_semana_atual})
```

## Exemplos de Uso

```
Médico: "To em cirurgia, me manda msg às 19h"
Júlia: [tool_call: agendar_lembrete("2025-12-06T19:00", "retomar conversa sobre vagas")]
Júlia: "Tranquilo! Te mando msg às 19h então, boa cirurgia! 👍"

---

Médico: "Amanhã de manhã a gente fala"
Júlia: [tool_call: agendar_lembrete("2025-12-07T09:00", "continuar sobre vaga Hospital Brasil")]
Júlia: "Fechado! Amanhã de manhã te mando msg 😊"

---

Médico: "Segunda me liga"
Júlia: [tool_call: agendar_lembrete("2025-12-09T10:00", "interesse em plantões")]
Júlia: "Combinado! Segunda de manhã te chamo!"
```

## DoD

- [x] Tool `agendar_lembrete` definida
- [x] Handler processa e enfileira corretamente
- [x] Data atual disponível no contexto da LLM
- [x] System prompt orienta uso da tool
- [x] Validação de data no passado
- [x] Mensagem de retorno personalizada ou padrão
- [x] Lembrete executado no horário agendado
