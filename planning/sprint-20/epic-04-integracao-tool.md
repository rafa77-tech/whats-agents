# Epic 04: Integracao com Tool reservar_plantao

## Objetivo

Modificar a tool `reservar_plantao` para disparar automaticamente a ponte externa quando a vaga tem origem de grupo (divulgador externo).

## Contexto

Atualmente `reservar_plantao` apenas:
1. Busca vaga por data/especialidade
2. Marca vaga como `reservada`
3. Notifica gestor no Slack

Precisamos adicionar:
1. Detectar se vaga tem `source='grupo'`
2. Se sim, chamar `criar_ponte_externa()`
3. Retornar instrucoes atualizadas para Julia

---

## Story 4.1: Detectar Origem da Vaga

### Objetivo
Verificar se a vaga aceita veio de um grupo de divulgacao.

### Arquivo: `app/tools/vagas.py`

```python
# Adicionar ao handle_reservar_plantao, apos reservar_vaga():

async def handle_reservar_plantao(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict[str, Any]:
    # ... codigo existente ate reservar_vaga() ...

    try:
        # Reservar vaga
        vaga_atualizada = await reservar_vaga(
            vaga_id=vaga_id,
            cliente_id=medico["id"],
            medico=medico,
            notificar_gestor=True
        )

        # NOVO: Verificar se vaga tem origem externa (grupo)
        ponte_externa = None
        if vaga.get("source") == "grupo" and vaga.get("source_id"):
            logger.info(f"Vaga {vaga_id} tem origem de grupo, iniciando ponte externa")

            from app.services.external_handoff.service import criar_ponte_externa

            try:
                ponte_externa = await criar_ponte_externa(
                    vaga_id=vaga_id,
                    cliente_id=medico["id"],
                    medico=medico,
                    vaga=vaga,
                )
            except Exception as e:
                logger.error(f"Erro ao criar ponte externa: {e}")
                # Nao falhar a reserva, apenas logar
                ponte_externa = {"error": str(e)}

        # ... resto do codigo ...
```

### DoD

- [ ] Verificacao de `source='grupo'` implementada
- [ ] Import condicional do service
- [ ] Erro nao bloqueia reserva principal

---

## Story 4.2: Adaptar Resposta da Tool

### Objetivo
Incluir informacoes da ponte externa na resposta da tool.

### Arquivo: `app/tools/vagas.py`

```python
# Continuar em handle_reservar_plantao:

        # Construir resposta
        resultado = {
            "success": True,
            "message": f"Plantao reservado com sucesso: {vaga_formatada}",
            "vaga": {
                "id": vaga_atualizada["id"],
                "hospital": hospital_data.get("nome"),
                "endereco": hospital_data.get("endereco_formatado"),
                "bairro": hospital_data.get("bairro"),
                "cidade": hospital_data.get("cidade"),
                "data": vaga_atualizada.get("data"),
                "periodo": vaga.get("periodos", {}).get("nome"),
                "valor": vaga.get("valor"),
                "valor_minimo": vaga.get("valor_minimo"),
                "valor_maximo": vaga.get("valor_maximo"),
                "valor_tipo": vaga.get("valor_tipo", "fixo"),
                "valor_display": _formatar_valor_display(vaga),
                "status": vaga_atualizada.get("status")
            },
        }

        # NOVO: Se teve ponte externa, adaptar instrucoes
        if ponte_externa and not ponte_externa.get("error"):
            divulgador = ponte_externa.get("divulgador", {})
            resultado["ponte_externa"] = {
                "handoff_id": ponte_externa.get("handoff_id"),
                "divulgador_nome": divulgador.get("nome"),
                "divulgador_telefone": divulgador.get("telefone"),
                "divulgador_empresa": divulgador.get("empresa"),
                "msg_enviada": ponte_externa.get("msg_enviada", False),
            }

            # Instrucao especifica para vaga de grupo
            resultado["instrucao"] = _construir_instrucao_ponte_externa(
                vaga, hospital_data, ponte_externa
            )
        else:
            # Instrucao normal (vaga interna)
            resultado["instrucao"] = _construir_instrucao_confirmacao(vaga, hospital_data)

        return resultado
```

### DoD

- [ ] Ponte externa incluida na resposta
- [ ] Instrucao adaptada para vaga externa
- [ ] Resposta compativel com fluxo existente

---

## Story 4.3: Nova Funcao de Instrucao

### Objetivo
Criar funcao que gera instrucao especifica para ponte externa.

### Arquivo: `app/tools/vagas.py`

```python
def _construir_instrucao_ponte_externa(
    vaga: dict,
    hospital_data: dict,
    ponte_externa: dict,
) -> str:
    """
    Constroi instrucao de confirmacao para vaga com ponte externa.

    Args:
        vaga: Dados da vaga
        hospital_data: Dados do hospital
        ponte_externa: Resultado da criacao da ponte

    Returns:
        Instrucao para o LLM
    """
    divulgador = ponte_externa.get("divulgador", {})
    divulgador_nome = divulgador.get("nome", "o divulgador")
    divulgador_tel = divulgador.get("telefone", "")
    divulgador_empresa = divulgador.get("empresa", "")

    # Montar info do divulgador
    info_divulgador = divulgador_nome
    if divulgador_empresa:
        info_divulgador += f" ({divulgador_empresa})"

    instrucao = (
        f"IMPORTANTE: Esta vaga e de um divulgador externo ({info_divulgador}). "
        f"Informe ao medico que voce JA ENTROU EM CONTATO com o divulgador "
        f"e passou os dados dele (Dr(a). {medico.get('nome')}).\n\n"
        f"O medico pode contatar diretamente: {divulgador_nome}"
    )

    if divulgador_tel:
        instrucao += f" - {divulgador_tel}"

    instrucao += (
        "\n\nPeca para o medico confirmar aqui quando fechar o plantao. "
        "Fale de forma natural, como se voce tivesse acabado de fazer a ponte entre eles."
    )

    # Adicionar info de valor se aplicavel
    valor_tipo = vaga.get("valor_tipo", "fixo")
    if valor_tipo == "a_combinar":
        instrucao += (
            "\n\nComo o valor e 'a combinar', mencione que o medico deve "
            "negociar diretamente com o divulgador."
        )

    return instrucao
```

### DoD

- [ ] Funcao `_construir_instrucao_ponte_externa` criada
- [ ] Menciona divulgador por nome
- [ ] Orienta sobre confirmacao

---

## Story 4.4: Incluir source na Query de Vaga

### Objetivo
Garantir que campos `source` e `source_id` vem na busca de vaga.

### Arquivo: `app/tools/vagas.py`

```python
# Em _buscar_vaga_por_data, adicionar campos:

async def _buscar_vaga_por_data(data: str, especialidade_id: str) -> dict | None:
    """
    Busca vaga pela data e especialidade.
    """
    try:
        response = (
            supabase.table("vagas")
            .select(
                "*, hospitais(*), periodos(*), setores(*), "
                "source, source_id"  # NOVO: incluir origem
            )
            .eq("data", data)
            .eq("especialidade_id", especialidade_id)
            .eq("status", "aberta")
            .limit(1)
            .execute()
        )
        # ...
```

### DoD

- [ ] Campos `source` e `source_id` na query
- [ ] Query existente nao quebra

---

## Checklist do Epico

- [ ] **S20.E04.1** - Deteccao de origem implementada
- [ ] **S20.E04.2** - Resposta adaptada com ponte externa
- [ ] **S20.E04.3** - Instrucao para ponte criada
- [ ] **S20.E04.4** - Query atualizada com source
- [ ] Tool reservar_plantao dispara ponte automaticamente
- [ ] Instrucoes da Julia adaptadas para medico
- [ ] Erro na ponte nao bloqueia reserva

---

## Fluxo Completo

```
1. Medico diz "quero essa vaga"
2. Julia chama reservar_plantao(data)
3. Tool busca vaga com source/source_id
4. Vaga marcada como reservada
5. IF source='grupo':
   a. Chama criar_ponte_externa()
   b. Msg enviada ao divulgador
   c. Evento HANDOFF_CREATED emitido
   d. Slack notificado
6. Retorna resultado com instrucoes
7. Julia confirma ao medico e passa contato do divulgador
```

---

## Teste Manual

```python
# Simular vaga de grupo
vaga = {
    "id": "...",
    "source": "grupo",
    "source_id": "uuid-vagas-grupo",
    "data": "2025-01-15",
    # ...
}

# Chamar tool
result = await handle_reservar_plantao(
    {"data_plantao": "2025-01-15", "confirmacao": "pode reservar"},
    medico={"id": "...", "nome": "Dr. Teste"},
    conversa={"id": "..."}
)

# Verificar
assert result["ponte_externa"]["handoff_id"] is not None
assert "divulgador" in result["instrucao"]
```
