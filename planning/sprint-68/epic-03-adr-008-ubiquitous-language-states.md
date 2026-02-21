# EPICO 03: Ubiquitous Language e Canonical States

## Prioridade: P3
## ADR relacionada: 008

## Contexto

O dominio usa termos e estados mistos (PT/EN e semantica sobreposta), o que gera ambiguidade entre produto e engenharia e aumenta risco de regra inconsistente.

## Escopo

- **Incluido**: dicionario oficial de termos, catalogo de estados canonicos por contexto, aliases legados e validacoes basicas em codigo.
- **Excluido**: migracao completa de todos os dados historicos nesta sprint.

---

## Tarefa 1: Publicar Dicionario de Linguagem Ubiqua

### Objetivo

Consolidar os principais termos de negocio e sua semantica oficial.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `docs/arquitetura/ddd-ubiquitous-language.md` |
| Modificar | `docs/arquitetura/logica-negocio.md` |

### Implementacao

- Definir termo canonic, sinonimos e anti-termos (nao usar).
- Cobrir termos criticos: medico/cliente, jornada, contato, oferta, reserva, handoff, opt-out, cooling-off.

### Testes Obrigatorios

**Unitarios:**
- [ ] N/A

**Integracao:**
- [ ] Revisao conjunta Engenharia + Produto registrada em documento

### Definition of Done

- [ ] Dicionario publicado
- [ ] Termos criticos aprovados
- [ ] Referencia cruzada na documentacao de arquitetura

### Estimativa

4 pontos

---

## Tarefa 2: Publicar Catalogo de Estados Canonicos

### Objetivo

Definir estados canonicos por contexto e mapear aliases legados.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `docs/arquitetura/ddd-canonical-states.md` |
| Modificar | `app/services/policy/types.py` |
| Modificar | `app/services/campanhas/types.py` |

### Implementacao

- Tabelar estados por entidade/contexto:
  - conversa
  - doctor_state/policy
  - campanha
  - vaga
  - handoff
- Para cada estado: significado, transicoes validas, aliases legados.

### Testes Obrigatorios

**Unitarios:**
- [ ] Testes de parse/mapeamento de aliases para estados canonicos
- [ ] Testes de fallback para estados desconhecidos

**Integracao:**
- [ ] Fluxo de policy e campanha com enums sem regressao de comportamento

### Definition of Done

- [ ] Catalogo publicado
- [ ] Mapeamentos de aliases implementados nos pontos criticos
- [ ] Testes de mapeamento passando

### Estimativa

8 pontos

---

## Tarefa 3: Criar Validacoes de Estado em Pontos Criticos

### Objetivo

Evitar escrita de estado invalido em fluxos centrais.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `app/core/domain_state_validators.py` |
| Modificar | `app/services/policy/state_update.py` |
| Modificar | `app/services/campanhas/repository.py` |
| Criar | `tests/core/test_domain_state_validators.py` |

### Implementacao

- Helpers de validacao:
  - `validate_policy_state(...)`
  - `validate_campaign_status_transition(...)`
- Aplicar em update points de maior risco.
- Em caso de estado invalido: log estruturado + erro explicito.

### Testes Obrigatorios

**Unitarios:**
- [ ] Transicoes validas aceitas
- [ ] Transicoes invalidas rejeitadas
- [ ] Mensagens de erro claras

**Integracao:**
- [ ] Endpoints de campanha/policy preservam contrato ao rejeitar estado invalido

### Definition of Done

- [ ] Validadores criados e aplicados
- [ ] Testes unitarios e integracao passando
- [ ] Logs com contexto do estado invalido

### Estimativa

6 pontos

---

## Tarefa 4: Atualizar ADR-008 com Evidencias de Implementacao

### Objetivo

Fechar ciclo de governanca: ADR refletir o que foi efetivamente entregue.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `docs/adrs/008-ubiquitous-language-and-canonical-states.md` |
| Modificar | `docs/adrs/README.md` |

### Implementacao

- Mover status de `Proposta` para `Aceita` se criterios completos forem atingidos.
- Linkar documentos e testes criados.

### Testes Obrigatorios

**Unitarios:**
- [ ] N/A

**Integracao:**
- [ ] Checklist de aceite arquitetural concluido

### Definition of Done

- [ ] ADR-008 atualizada com evidencias
- [ ] Index ADR atualizado
- [ ] Aceite formal registrado

### Estimativa

2 pontos

