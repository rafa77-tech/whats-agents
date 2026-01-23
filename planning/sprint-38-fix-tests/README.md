# Sprint 38 - Correção de Testes

## Objetivo

Resolver os 7 testes falhando e avaliar os 17 testes pulados para garantir cobertura completa.

---

## Resumo

| Categoria | Quantidade | Ação |
|-----------|------------|------|
| ❌ Falhando | 7 | Corrigir |
| ⏭️ Pulados | 17 | Avaliar/Habilitar |

---

## Testes Falhando (7)

### Epic 1: Gatilhos Autônomos (5 testes)

**Arquivo:** `tests/unit/test_gatilhos_autonomos.py`

**Testes:**
1. `test_retorna_none_em_modo_piloto` (Discovery)
2. `test_retorna_none_em_modo_piloto` (Oferta)
3. `test_retorna_none_em_modo_piloto` (Reativação)
4. `test_retorna_none_em_modo_piloto` (Feedback)
5. `test_retorna_pilot_mode_true_quando_ativo`

**Causa Raiz:**
```
ERROR: column clientes.status_telefone does not exist
```

O código em `gatilhos_autonomos.py:85` tenta acessar coluna `status_telefone` que não existe na tabela `clientes`.

**Solução:**
- [ ] Verificar se coluna foi removida ou renomeada
- [ ] Atualizar query em `gatilhos_autonomos.py`
- [ ] OU criar migration para adicionar coluna

**Estimativa:** 1h

---

### Epic 2: Modo Piloto (1 teste)

**Arquivo:** `tests/e2e/test_modo_piloto.py`

**Teste:** `test_require_pilot_disabled_bloqueia_em_piloto`

**Causa Raiz:**
```python
assert resultado is False
# resultado retorna True quando deveria ser False
```

A função `require_pilot_disabled()` não está bloqueando corretamente quando modo piloto está ativo.

**Solução:**
- [ ] Revisar lógica em `require_pilot_disabled()`
- [ ] Verificar se decorator está funcionando corretamente
- [ ] Corrigir condição de bloqueio

**Estimativa:** 30min

---

### Epic 3: Fila de Grupos (1 teste)

**Arquivo:** `tests/grupos/test_fila.py`

**Teste:** `test_enfileirar_mensagem_nova`

**Causa Raiz:**
```
ValueError: badly formed hexadecimal UUID string
```

A função `enfileirar_mensagem()` em `fila.py:81` tenta converter para UUID um valor que não é UUID válido.

**Solução:**
- [ ] Verificar retorno da query no Supabase
- [ ] Adicionar validação antes de converter para UUID
- [ ] Verificar se coluna ID está retornando corretamente

**Estimativa:** 30min

---

## Testes Pulados (17)

### Categoria A: Arquivos Não Encontrados (3 testes)

**Arquivo:** `tests/conhecimento/test_parser.py`

**Testes:**
1. `test_parsear_arquivo_abertura` - `docs/julia/MENSAGENS_ABERTURA.md`
2. `test_parsear_arquivo_objecoes` - `docs/julia/julia_catalogo_objecoes_respostas.md`
3. `test_chunks_tem_tamanho_adequado` - `docs/julia/julia_catalogo_objecoes_respostas.md`

**Causa:** Arquivos markdown não existem no repositório.

**Solução:**
- [ ] Criar arquivos de documentação faltantes
- [ ] OU remover testes se arquivos não são mais necessários

**Estimativa:** 1h

---

### Categoria B: Requerem Serviços Externos (5 testes)

**Arquivos:** `tests/persona/`

**Testes:**
1. `test_resistencia_provocacao`
2. `test_consistencia_informacoes`
3. `test_todas_respostas_informais`
4. `test_resistencia_todas_provocacoes`
5. `test_prompt_injection`

**Causa:** Requerem `RUN_PERSONA_TESTS=1` (LLM API + Redis)

**Ação:** Manter skip - são testes de integração que rodam manualmente ou em CI específico.

**Estimativa:** N/A (comportamento correto)

---

### Categoria C: Integração com API Externa (1 teste)

**Arquivo:** `tests/services/llm/test_providers.py`

**Teste:** `test_simple_generation`

**Causa:** Requer API key da Anthropic para rodar.

**Ação:** Manter skip - teste de integração.

**Estimativa:** N/A (comportamento correto)

---

### Categoria D: Validação de Views/Campanhas (3 testes)

**Arquivo:** `tests/unit/test_campaign_sends.py`

**Testes:**
1. `test_sem_colisao_send_id`
2. `test_sem_duplicata_canonical_key`
3. `test_metricas_somam_corretamente`

**Causa:** Provavelmente dependem de dados específicos ou views no banco.

**Solução:**
- [ ] Investigar por que estão sendo pulados
- [ ] Criar fixtures adequadas
- [ ] OU documentar como executar manualmente

**Estimativa:** 1h

---

### Categoria E: Segmentação Qualificada (5 testes)

**Arquivo:** `tests/unit/test_segmentacao_qualificada.py`

**Testes:**
1. `test_medico_sem_doctor_state_incluido`
2. `test_medico_contact_cap_excedido_excluido`
3. `test_medico_conversa_humana_excluido`
4. `test_medico_inbound_recente_excluido`
5. `test_ordem_deterministica`

**Causa:** Provavelmente dependem de banco de dados real ou fixtures específicas.

**Solução:**
- [ ] Investigar condição de skip
- [ ] Criar mocks adequados
- [ ] OU configurar ambiente de teste

**Estimativa:** 1.5h

---

## Priorização

### Alta Prioridade (Corrigir Primeiro)
1. **Epic 1: Gatilhos Autônomos** - 5 testes, impacta funcionalidade core
2. **Epic 3: Fila de Grupos** - Bug de UUID pode indicar problema maior

### Média Prioridade
3. **Epic 2: Modo Piloto** - 1 teste, lógica de segurança
4. **Categoria D: Views/Campanhas** - Validação de integridade

### Baixa Prioridade (Avaliar Necessidade)
5. **Categoria A: Arquivos** - Criar docs ou remover testes
6. **Categoria E: Segmentação** - Investigar dependências

### Manter Como Está
- **Categoria B e C:** Testes de integração com skip intencional

---

## Checklist de Execução

```
[x] Epic 1: Corrigir mocks de is_feature_enabled (5 testes)
[x] Epic 2: Corrigir require_pilot_disabled (1 teste)
[x] Epic 3: Corrigir mock de insert vs upsert (1 teste)
[x] Bonus: Renomear test_*.py → debug_*.py (4 falhas pré-existentes)
[ ] Categoria A: Criar/remover docs
[ ] Categoria D: Investigar views
[ ] Categoria E: Investigar segmentação
[x] Rodar suite completa (2320 passed, 17 skipped, 0 failures)
```

## Correções Realizadas

### Epic 1: test_gatilhos_autonomos.py
**Causa Real:** Testes mockavam `settings.is_pilot_mode = True` mas o código usa `settings.is_feature_enabled()`.

**Fix:** Adicionado `mock_settings.is_feature_enabled.return_value = False/True` em todos os testes.

### Epic 2: test_modo_piloto.py
**Causa Real:** Mesma causa do Epic 1 - `require_pilot_disabled()` usa `is_feature_enabled()`.

**Fix:** Adicionado `mock_settings.is_feature_enabled.return_value = False` no teste.

### Epic 3: test_fila.py
**Causa Real:** Teste mockava `.upsert()` mas implementação usa `.insert()`.

**Fix:** Alterado mock de `upsert` para `insert`.

### Falhas pré-existentes (4 testes) - RESOLVIDO
Os arquivos `app/api/routes/test_*.py` eram **rotas de API para debug**, não testes pytest.
O pytest os coletava incorretamente por causa do prefixo `test_`.

**Fix:** Renomeados para `debug_*.py`:
- `test_llm.py` → `debug_llm.py`
- `test_whatsapp.py` → `debug_whatsapp.py`

Atualizado `app/main.py` e `tests/test_architecture_guardrails.py` para refletir os novos nomes.

---

## Tempo Estimado Total

| Item | Tempo |
|------|-------|
| Epic 1-3 (Falhas) | 2h |
| Categoria A, D, E | 3.5h |
| Buffer/Investigação | 1.5h |
| **Total** | **7h** |
