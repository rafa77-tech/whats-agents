# Epic 3: Protecao do Chip de Grupos

**Status:** 🔴 Nao Iniciada
**Prioridade:** P0 - Critico

---

## Contexto

O chip **5511916175810** (instance: Revoluna) e o unico com acesso a **174 grupos** de WhatsApp onde medicos postam ofertas de plantao.

Este chip e um **ativo estrategico** que alimenta toda nossa inteligencia de mercado. Se for banido:
- Perdemos acesso a 174 grupos
- Perdemos visibilidade do mercado
- Reconstruir levaria meses (se possivel)

---

## Regra de Ouro

> **O chip de grupos e READ-ONLY. Ele NUNCA envia mensagens.**

---

## Situacao Atual

```sql
SELECT id, telefone, tipo, status FROM chips WHERE telefone LIKE '%5810';

-- Resultado:
-- tipo = 'julia'  ← ERRADO! Deveria ser 'escuta' ou 'grupos'
```

O chip esta marcado como `tipo = 'julia'`, o que significa que ele **pode ser selecionado** para enviar mensagens de prospecao. Isso e um risco critico.

---

## Stories

### S51.E3.1 - Criar Tipo de Chip 'listener' ✅ FEITO

**Objetivo:** Definir um tipo especifico para chips que so recebem mensagens

**Status:** ✅ Aplicado em 02/02/2026

**SQL Executado:**
```sql
UPDATE chips
SET
  tipo = 'listener',
  pode_prospectar = false,
  pode_followup = false,
  pode_responder = false
WHERE telefone = '5511916175810';
```

**Resultado:**
- tipo = 'listener' ✅
- pode_prospectar = false ✅
- pode_followup = false ✅
- pode_responder = false ✅

**Nota:** O tipo 'listener' ja existia na constraint `chips_tipo_check`. Tipos permitidos: `['julia', 'listener']`

**DoD:**
- [x] Chip 5810 com tipo 'listener'
- [ ] Documentacao atualizada

---

### S51.E3.2 - Bloquear Envio para Chips de Escuta

**Objetivo:** Garantir que o sistema nunca envie mensagens por chips de escuta

**Arquivos a modificar:**
- `app/services/chips/seletor.py` - Excluir chips de escuta da selecao
- `app/services/evolution/sender.py` - Validar antes de enviar
- `app/services/whatsapp/envio.py` - Validar antes de enviar

**Codigo:**
```python
# Em qualquer funcao que seleciona chip para envio
async def selecionar_chip_para_envio(...):
    # Excluir chips de escuta
    query = query.neq("tipo", "escuta")
    ...

# Em qualquer funcao que envia mensagem
async def enviar_mensagem(chip_id, ...):
    chip = await buscar_chip(chip_id)
    if chip.tipo == "escuta":
        raise ChipReadOnlyError(
            f"Chip {chip.telefone} e read-only (tipo=escuta)"
        )
    ...
```

**DoD:**
- [ ] Chips de escuta excluidos da selecao automatica
- [ ] Validacao antes de qualquer envio
- [ ] Exception especifica para tentativa de envio
- [ ] Testes unitarios

---

### S51.E3.3 - Alertas de Tentativa de Envio

**Objetivo:** Ser notificado se alguem tentar enviar por chip de escuta

**Tarefas:**
1. Criar alerta no Slack quando `ChipReadOnlyError` for lancado
2. Logar com nivel CRITICAL
3. Incluir stack trace para identificar origem

**Codigo:**
```python
except ChipReadOnlyError as e:
    logger.critical(
        "Tentativa de envio por chip de escuta!",
        extra={
            "chip_id": chip_id,
            "chip_telefone": chip.telefone,
            "origem": traceback.format_stack(),
        }
    )
    await notificar_slack_urgente(
        f"🚨 ALERTA: Tentativa de envio por chip de escuta {chip.telefone}"
    )
    raise
```

**DoD:**
- [ ] Alerta no Slack configurado
- [ ] Log com nivel CRITICAL
- [ ] Stack trace para debug

---

### S51.E3.4 - Dashboard de Status do Chip

**Objetivo:** Visibilidade do chip de grupos no dashboard

**Tarefas:**
1. Adicionar card especial para chip de escuta na pagina /chips
2. Mostrar: grupos ativos, mensagens/dia, ultima atividade
3. Indicador visual de "READ-ONLY"

**DoD:**
- [ ] Card no dashboard
- [ ] Metricas visiveis
- [ ] Indicador READ-ONLY claro

---

### S51.E3.5 - Documentacao e Runbook

**Objetivo:** Documentar operacao do chip de grupos

**Arquivo:** `docs/operacao/chip-grupos.md`

**Conteudo:**
1. O que e o chip de grupos
2. Por que e importante
3. Regras de uso (READ-ONLY)
4. O que fazer se for banido
5. Como adicionar novo chip de grupos

**DoD:**
- [ ] Documento criado
- [ ] Revisado pela equipe

---

## Validacao Final

Apos implementacao, executar:

```sql
-- Verificar tipo do chip
SELECT telefone, tipo, status FROM chips WHERE telefone LIKE '%5810';
-- Esperado: tipo = 'escuta'

-- Verificar que nao ha envios por este chip
SELECT COUNT(*) FROM fila_mensagens WHERE chip_id = '4cfcd8e9-6920-44d0-9b64-0c9aefe14a03';
-- Esperado: 0

-- Verificar que nao esta no pool de envio
SELECT * FROM chips WHERE pode_prospectar = true AND tipo = 'escuta';
-- Esperado: 0 rows
```

---

## Riscos

| Risco | Mitigacao |
|-------|-----------|
| Codigo legado ignorar validacao | Code review + testes |
| Alguem alterar tipo no banco | Trigger de protecao |
| Novo codigo nao seguir padrao | Documentacao clara |
