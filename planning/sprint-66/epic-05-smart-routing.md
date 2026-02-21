# EPIC 05: Smart Routing + 24h Window

## Status: Implementado

## Contexto

Decisao arquitetural central: dentro da janela 24h Julia fala naturalmente (free-form), fora da janela usa templates aprovados. A logica fica no sender (orquestracao), nao no provider.

Meta impoe janela de 24h: apos ultima mensagem do usuario, a empresa pode enviar mensagens livres. Fora da janela, apenas templates aprovados. Violacao = erro 131026.

## Escopo

- **Incluido**: Window tracker, smart send no sender.py, chip selector Meta eligibility
- **Excluido**: Campaign integration (epic 06), orchestrator changes (epic 07)

---

## Tarefa 05.1: Conversation Window Tracker

### Arquivo: `app/services/meta/window_tracker.py` (122 linhas)

`MetaWindowTracker` (singleton `window_tracker`):

| Metodo | Descricao |
|--------|-----------|
| `esta_na_janela(chip_id, telefone)` | SELECT com `window_expires_at > NOW()`. True/False |
| `abrir_janela(chip_id, telefone, tipo)` | UPSERT com expiracao baseada no tipo |
| `limpar_janelas_expiradas()` | DELETE com `window_expires_at < NOW()` |

### Janelas por tipo

| Tipo | Duracao | Quando |
|------|---------|--------|
| `user_initiated` | 24h | Mensagem recebida do usuario |
| `ctwa` (Click-to-WhatsApp) | 72h | Click em anuncio CTWA |

### Integracao com webhook

Quando webhook_meta recebe mensagem → chama `window_tracker.abrir_janela(chip_id, telefone, "user_initiated")`.

### Testes: `tests/services/meta/test_window_tracker.py` (12 testes)

| Area | Testes |
|------|--------|
| esta_na_janela | janela ativa → True, janela expirada → False, sem registro → False, erro DB → False |
| abrir_janela | user_initiated (24h), ctwa (72h), upsert renova existente |
| limpar | remove apenas expiradas, mantem ativas |
| edge cases | chip_id None, telefone vazio |

---

## Tarefa 05.2: Smart Send no ChipSender

### Arquivo: `app/services/chips/sender.py`

Adicionada funcao `_enviar_meta_smart()` e parametro `template_info` em `enviar_via_chip()`.

### Logica de decisao

```
chip.provider == "meta"?
  ├─ SIM → esta_na_janela(chip_id, telefone)?
  │        ├─ SIM → send_text(telefone, texto)  [free-form]
  │        └─ NAO → template_info existe?
  │                 ├─ SIM → send_template(telefone, template_name, language, components)
  │                 └─ NAO → return error "meta_fora_janela_sem_template"
  └─ NAO → send_text(telefone, texto)  [Evolution/Z-API normal]
```

### Gap CRITICO identificado

`enviar_media_via_chip()` NAO foi atualizado com a mesma logica. Se um chip Meta tentar enviar midia fora da janela 24h, vai falhar com erro 131026 sem tratamento adequado.

**Acao necessaria**: Sprint 66-fix (Gap G1)

### Testes faltando (Gap G2)

`_enviar_meta_smart()` tem 0 testes unitarios. Precisa de 7 testes:

1. Chip Meta + na janela → send_text chamado
2. Chip Meta + fora da janela + template_info → send_template chamado
3. Chip Meta + fora da janela + sem template → erro "meta_fora_janela_sem_template"
4. Chip Evolution → comportamento inalterado
5. Chip Z-API → comportamento inalterado
6. template_info propagado corretamente
7. Erro do provider propagado corretamente

---

## Tarefa 05.3: ChipSelector — Meta Eligibility

### Arquivo: `app/services/chips/selector.py`

Modificacoes na `_buscar_chips_elegiveis()`:

1. Chips com `provider="meta"` NAO precisam de `evolution_connected=True`
2. Chips com `meta_quality_rating='RED'` sao excluidos (equivalente a degradados)
3. Filtro aplicado tanto na selecao por afinidade quanto na selecao geral

### Gap identificado (G3)

Selector pode escolher chips Meta com credenciais invalidas (sem `meta_phone_number_id` ou `meta_access_token`). O factory vai levantar `ValueError`, mas isso acontece tarde demais — apos o chip ja ter sido selecionado.

**Acao necessaria**: Adicionar validacao de credenciais no selector para chips Meta.

### Testes faltando

0 testes para Meta eligibility no selector. Precisa de 4 testes:

1. Chip Meta sem `evolution_connected` → elegivel
2. Chip Meta com `meta_quality_rating='RED'` → nao elegivel
3. Chip Meta com `meta_quality_rating='GREEN'` → elegivel
4. Selecao mista (Evolution + Meta) funciona

---

## Definition of Done

- [x] Window tracker com 3 metodos (esta_na_janela, abrir_janela, limpar)
- [x] Janela 24h (user_initiated) e 72h (CTWA) implementadas
- [x] Smart routing no sender.py (free-form dentro, template fora)
- [x] Selector exclui chips Meta com quality RED
- [x] Selector nao exige evolution_connected para chips Meta
- [x] 12 testes do window tracker passando

## Gaps Criticos

| # | Gap | Severidade | Status |
|---|-----|-----------|--------|
| G1 | `enviar_media_via_chip` nao respeita janela 24h | CRITICO | Pendente |
| G2 | `_enviar_meta_smart()` sem testes unitarios (7 faltando) | CRITICO | Pendente |
| G3 | Selector pode escolher chips Meta sem credenciais | ALTO | Pendente |
