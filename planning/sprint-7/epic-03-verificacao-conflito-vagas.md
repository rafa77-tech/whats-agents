# Epic 03: Verificação de Conflito de Vagas

## Prioridade: P1 (Importante)

## Objetivo

> **Impedir que Júlia ofereça ou reserve vaga em dia/período que o médico já tem outro plantão.**

Documentado em `docs/FLUXOS.md` na seção "Regras de Múltiplas Vagas".

---

## Referência: FLUXOS.md

```sql
-- Antes de oferecer vaga, verificar se médico já tem plantão no mesmo dia/período
SELECT COUNT(*) FROM vagas
WHERE cliente_id = $medico_id
  AND data_plantao = $data_vaga
  AND periodo_id = $periodo_id
  AND status IN ('reservada', 'confirmada');
-- Se COUNT > 0, não oferecer esta vaga
```

---

## Problema Atual

1. **Busca de vagas:** Não filtra vagas em conflito
2. **Reserva:** Não verifica antes de reservar
3. **Risco:** Médico pode aceitar duas vagas no mesmo horário

---

## Stories

---

# S7.E3.1 - Implementar função verificar_conflito

## Objetivo

> **Criar função que verifica se médico já tem plantão em determinado dia/período.**

## Código Esperado

**Arquivo:** `app/services/vaga.py` (adicionar)

```python
async def verificar_conflito_vaga(
    cliente_id: str,
    data_plantao: str,
    periodo_id: str
) -> dict:
    """
    Verifica se médico já tem vaga reservada/confirmada no mesmo dia e período.

    Args:
        cliente_id: ID do médico
        data_plantao: Data no formato YYYY-MM-DD
        periodo_id: ID do período (diurno, noturno, etc)

    Returns:
        dict com:
        - conflito: bool
        - vaga_conflitante: dict ou None (se houver conflito)
    """
    response = (
        supabase.table("vagas")
        .select("id, hospital_id, data_plantao, periodo_id, status, hospitais(nome)")
        .eq("cliente_id", cliente_id)
        .eq("data_plantao", data_plantao)
        .eq("periodo_id", periodo_id)
        .in_("status", ["reservada", "confirmada"])
        .limit(1)
        .execute()
    )

    if response.data:
        vaga_conflitante = response.data[0]
        return {
            "conflito": True,
            "vaga_conflitante": {
                "id": vaga_conflitante["id"],
                "hospital": vaga_conflitante.get("hospitais", {}).get("nome", "Hospital"),
                "data": vaga_conflitante["data_plantao"],
                "status": vaga_conflitante["status"]
            },
            "mensagem": f"Médico já tem plantão em {vaga_conflitante['data_plantao']} no mesmo período"
        }

    return {
        "conflito": False,
        "vaga_conflitante": None,
        "mensagem": None
    }
```

## Critérios de Aceite

1. **Detecta conflito:** Retorna True se há vaga no mesmo dia/período
2. **Status corretos:** Considera apenas 'reservada' e 'confirmada'
3. **Info do conflito:** Retorna dados da vaga conflitante
4. **Performance:** Query rápida (índice em cliente_id + data + periodo_id)

## DoD

- [x] Função `verificar_conflito_vaga()` implementada
- [x] Testa apenas vagas reservadas/confirmadas
- [x] Retorna dados da vaga conflitante se houver
- [x] Log quando conflito detectado
- [x] Query usa índice existente ou criar novo

**NOTA:** Implementado em `app/services/vaga.py` - função `verificar_conflito_vaga()` retorna dict com detalhes do conflito.

---

# S7.E3.2 - Integrar verificação na busca de vagas

## Objetivo

> **Filtrar vagas em conflito ANTES de retornar ao LLM.**

## Código Esperado

**Arquivo:** `app/tools/vagas.py` (modificar handle_buscar_vagas)

```python
async def handle_buscar_vagas(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
    """Handler da tool buscar_vagas com verificação de conflito."""

    # ... código existente de busca ...

    # Filtrar vagas em conflito
    vagas_sem_conflito = []
    for vaga in vagas_filtradas:
        conflito = await verificar_conflito_vaga(
            cliente_id=medico["id"],
            data_plantao=vaga["data_plantao"],
            periodo_id=vaga["periodo_id"]
        )

        if not conflito["conflito"]:
            vagas_sem_conflito.append(vaga)
        else:
            logger.debug(
                f"Vaga {vaga['id']} filtrada: conflito com {conflito['vaga_conflitante']}"
            )

    # ... continua com vagas_sem_conflito ...
```

## Critérios de Aceite

1. **Filtro aplicado:** Vagas em conflito não aparecem
2. **Log de debug:** Registra vagas filtradas por conflito
3. **Performance:** Verificação não adiciona latência significativa (< 100ms por vaga)

## DoD

- [x] Busca de vagas verifica conflito para cada resultado
- [x] Vagas conflitantes removidas do resultado
- [x] Log indica quantas vagas filtradas
- [x] Teste: médico com vaga dia X não vê outras vagas dia X/período

**NOTA:** Já implementado em `app/tools/vagas.py` linhas 162-180 - `handle_buscar_vagas()` itera pelas vagas e filtra conflitos.

---

# S7.E3.3 - Integrar verificação na reserva

## Objetivo

> **Verificar conflito ANTES de confirmar reserva, como última barreira.**

## Código Esperado

**Arquivo:** `app/tools/vagas.py` (modificar handle_reservar_plantao)

```python
async def handle_reservar_plantao(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
    """Handler da tool reservar_plantao com verificação de conflito."""

    vaga_id = tool_input.get("vaga_id")

    # Buscar dados da vaga
    vaga = await buscar_vaga_por_id(vaga_id)
    if not vaga:
        return {
            "success": False,
            "error": "Vaga não encontrada"
        }

    # VERIFICAÇÃO DE CONFLITO (nova)
    conflito = await verificar_conflito_vaga(
        cliente_id=medico["id"],
        data_plantao=vaga["data_plantao"],
        periodo_id=vaga["periodo_id"]
    )

    if conflito["conflito"]:
        logger.warning(
            f"Tentativa de reservar vaga em conflito: medico={medico['id']}, "
            f"vaga={vaga_id}, conflito_com={conflito['vaga_conflitante']}"
        )
        return {
            "success": False,
            "error": "Conflito de horário",
            "mensagem": f"Você já tem plantão no dia {vaga['data_plantao']} "
                       f"no {conflito['vaga_conflitante']['hospital']}. "
                       f"Não posso reservar essa vaga."
        }

    # ... continua com reserva normal ...
```

## Critérios de Aceite

1. **Bloqueio:** Reserva não prossegue se há conflito
2. **Mensagem clara:** Explica por que não pode reservar
3. **Log de warning:** Registra tentativa de conflito
4. **Última barreira:** Funciona mesmo se busca não filtrou

## DoD

- [x] `handle_reservar_plantao()` verifica conflito antes de reservar
- [x] Retorna mensagem explicando o conflito
- [x] Log de warning com detalhes
- [x] Teste: tentar reservar vaga em conflito → erro claro

**NOTA:** Já implementado em `app/services/vaga.py` - função `reservar_vaga()` chama `verificar_conflito()` antes de reservar e lança ValueError com mensagem explicativa.

---

## Resumo do Epic

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S7.E3.1 | Função verificar_conflito | Baixa |
| S7.E3.2 | Integrar na busca | Média |
| S7.E3.3 | Integrar na reserva | Baixa |

## Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `app/services/vaga.py` | Adicionar verificar_conflito_vaga |
| `app/tools/vagas.py` | Chamar verificação em busca e reserva |

## Validação Final

```python
@pytest.mark.asyncio
async def test_conflito_bloqueia_busca():
    """Vaga em conflito não aparece nos resultados."""
    # Setup: médico tem vaga dia 15/12 diurno
    # Buscar vagas
    # Assert: nenhuma vaga dia 15/12 diurno aparece

@pytest.mark.asyncio
async def test_conflito_bloqueia_reserva():
    """Reserva em conflito é bloqueada."""
    # Setup: médico tem vaga dia 15/12 diurno
    # Tentar reservar outra vaga dia 15/12 diurno
    # Assert: erro de conflito retornado
```
