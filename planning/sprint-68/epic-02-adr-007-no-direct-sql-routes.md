# EPICO 02: Boundary Enforcement API -> Application -> Repository

## Prioridade: P2
## ADR relacionada: 007

## Contexto

Rotas de dominio ainda executam query direta em banco, reduzindo isolamento de dominio e duplicando regras.

## Escopo

- **Incluido**: migracao de 3 rotas criticas para application service + repository boundary, guardrail automatizado para evitar novos casos.
- **Excluido**: migracao total de todas as rotas legadas nesta sprint.

Rotas alvo da sprint:

1. `app/api/routes/campanhas.py`
2. `app/api/routes/group_entry.py`
3. `app/api/routes/incidents.py`

---

## Tarefa 1: Criar Estrutura de Application Services por Contexto

### Objetivo

Definir camada padrao de aplicacao para uso pelos routers.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `app/contexts/campanhas/application.py` |
| Criar | `app/contexts/group_entry/application.py` |
| Criar | `app/contexts/incidents/application.py` |
| Criar | `app/contexts/__init__.py` |

### Implementacao

- Application service encapsula caso de uso da rota.
- Router apenas valida input HTTP e chama service.
- Regras de negocio e acesso a dados ficam fora da rota.

### Testes Obrigatorios

**Unitarios:**
- [ ] Caso de sucesso para cada application service
- [ ] Caso de erro de validacao de negocio
- [ ] Caso de falha de infraestrutura (retorno controlado)

**Integracao:**
- [ ] Fluxo endpoint -> application -> repository para 1 caso por contexto

### Definition of Done

- [ ] 3 application services criados
- [ ] Contratos de entrada/saida documentados
- [ ] Testes unitarios passando

### Estimativa

8 pontos

---

## Tarefa 2: Migrar `campanhas.py` para boundary completo

### Objetivo

Remover SQL direto das operacoes criticas de campanhas no router.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/api/routes/campanhas.py` |
| Criar | `app/contexts/campanhas/repositories.py` |
| Criar | `tests/api/routes/test_campanhas_boundary.py` |
| Criar | `tests/contexts/campanhas/test_application.py` |

### Implementacao

- Extrair chamadas diretas de `supabase.table(...)` para repository.
- Reusar `app/services/campanhas/*` onde fizer sentido, sem duplicar regra.
- Router passa a delegar para application service.

### Testes Obrigatorios

**Unitarios:**
- [ ] Create/list/report de campanha via application
- [ ] Erro de campanha inexistente
- [ ] Status invalido e transicao invalida

**Integracao:**
- [ ] Endpoints principais de campanhas continuam com resposta compativel

### Definition of Done

- [ ] SQL direto removido dos fluxos criticos de `campanhas.py`
- [ ] Testes de regressao do endpoint passando
- [ ] Sem quebra de contrato HTTP

### Estimativa

10 pontos

---

## Tarefa 3: Migrar `group_entry.py` e `incidents.py` para boundary

### Objetivo

Aplicar o mesmo padrao nos outros dois contextos alvo da sprint.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/api/routes/group_entry.py` |
| Modificar | `app/api/routes/incidents.py` |
| Criar | `app/contexts/group_entry/repositories.py` |
| Criar | `app/contexts/incidents/repositories.py` |
| Criar | `tests/api/routes/test_group_entry_boundary.py` |
| Criar | `tests/api/routes/test_incidents_boundary.py` |

### Implementacao

- Remover `supabase.table(...)` de rotas de dominio selecionadas.
- Centralizar query e mapeamento em repositories.
- Tratar erros na camada de aplicacao (nao no router).

### Testes Obrigatorios

**Unitarios:**
- [ ] Success/error de casos de uso para ambos contextos
- [ ] Validacao de parametros invalidos

**Integracao:**
- [ ] Endpoints continuam respondendo com payload esperado
- [ ] Casos de erro mapeados para HTTP status corretos

### Definition of Done

- [ ] SQL direto removido das operacoes-alvo
- [ ] Testes de API e application passando
- [ ] Contrato HTTP preservado

### Estimativa

10 pontos

---

## Tarefa 4: Bloquear novos SQL diretos em rotas (guardrail)

### Objetivo

Evitar regressao apos migracao inicial.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `scripts/architecture/check_sql_in_routes.sh` |
| Modificar | `.github/workflows/*` (job de validacao) |
| Criar | `tests/scripts/test_check_sql_in_routes.sh` |

### Implementacao

- Script falha se detectar novo `supabase.table(` em `app/api/routes` fora de allowlist.
- Allowlist inicial para legado nao migrado.
- CI executa script em PR.

### Testes Obrigatorios

**Unitarios:**
- [ ] Script passa sem violacao
- [ ] Script falha com violacao simulada

**Integracao:**
- [ ] Job da pipeline executa check com sucesso

### Definition of Done

- [ ] Guardrail em CI ativo
- [ ] Allowlist documentada com plano de reducao
- [ ] Equipe alinhada sobre regra

### Estimativa

4 pontos

