# EPIC 06: Campaign Integration

## Status: Implementado

## Contexto

Campanhas sao outbound (cold outreach) → sempre fora da janela 24h → DEVEM usar templates Meta. Quando `meta_template_name` esta definido na campanha, o executor busca o template aprovado, mapeia variaveis, e propaga `template_info` pelo pipeline ate o sender.

## Escopo

- **Incluido**: Campaign executor template integration, types update, outbound multi_chip propagation
- **Excluido**: Dashboard UI para selecao de template (sprint 69), template analytics (sprint 67)

---

## Tarefa 06.1: Campaign Types Update

### Arquivo: `app/services/campanhas/types.py`

Adicionados 2 campos ao `CampanhaData`:

```python
meta_template_name: Optional[str] = None
meta_template_language: str = "pt_BR"
```

---

## Tarefa 06.2: Campaign Executor — Template Integration

### Arquivo: `app/services/campanhas/executor.py`

Adicionado metodo `_adicionar_meta_template_info()`:

1. Verifica se `campanha.meta_template_name` esta definido
2. Busca template: `template_service.buscar_template_por_nome(name)`
3. Valida status APPROVED
4. Mapeia variaveis: `template_mapper.mapear_variaveis(template, destinatario, campanha)`
5. Inclui na metadata do envio: `metadata["meta_template"] = {"name":..., "language":..., "components":...}`

### Fallback

Se template nao encontrado ou nao aprovado:
- Log warning
- Campanha continua com mensagem texto (funciona para chips Evolution/Z-API)
- Chips Meta vao falhar com "meta_fora_janela_sem_template" (correto — sem template aprovado nao da pra enviar)

### Status validation update

Executor agora aceita status `AGENDADA` e `ATIVA` (antes era so AGENDADA). Dashboard define status como ATIVA antes de chamar o executor, causando race condition.

### Testes faltando

0 testes para `_adicionar_meta_template_info()`. Precisa de 5 testes:

1. Campanha com meta_template_name → metadata inclui meta_template
2. Campanha com template nao aprovado → fallback para texto
3. Campanha sem meta_template_name → comportamento inalterado
4. Variable mapping correto para cada tipo de campanha
5. Anti-spam checks continuam funcionando

---

## Tarefa 06.3: Outbound Multi-Chip — Template Info Propagation

### Arquivo: `app/services/outbound/multi_chip.py`

Modificado `_enviar_via_multi_chip()`:
- Extrai `template_info` de `ctx.metadata.get("meta_template")` quando disponivel
- Passa para `enviar_via_chip(chip, telefone, texto, template_info=template_info)`

### Pipeline completo

```
executor._criar_envio()
  → _adicionar_meta_template_info()    [busca template, mapeia variaveis]
  → metadata["meta_template"] = {...}  [salva na metadata do envio]
  → fila de envio
  → outbound/multi_chip
  → extrai template_info da metadata   [multi_chip.py]
  → sender.enviar_via_chip(template_info=...)
  → _enviar_meta_smart()              [sender.py]
  → provider.send_template(...)       [meta_cloud.py]
```

### Testes faltando

0 testes para template_info propagation. Precisa de 2 testes:

1. template_info extraido da metadata e passado ao sender
2. Sem template_info na metadata → None passado (default)

---

## Definition of Done

- [x] CampanhaData com meta_template_name e meta_template_language
- [x] Executor busca template, valida status, mapeia variaveis
- [x] Fallback gracioso quando template indisponivel
- [x] multi_chip extrai e propaga template_info
- [x] Pipeline completo: executor → fila → outbound → sender → provider
- [x] Status validation aceita AGENDADA e ATIVA

## Gaps Identificados

- [ ] 5 testes faltando para _adicionar_meta_template_info
- [ ] 2 testes faltando para multi_chip template_info propagation
- [ ] Dashboard UI para selecao de template na campanha (sprint 69)
- [ ] Template analytics por campanha nao implementado (sprint 67)
