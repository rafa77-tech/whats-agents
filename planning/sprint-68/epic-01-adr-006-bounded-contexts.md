# EPICO 01: Context Map e Ownership de Contextos

## Prioridade: P1
## ADR relacionada: 006

## Contexto

Os contextos de dominio existem na pratica, mas nao estao formalizados com contratos e ownership explicito. Sem isso, as proximas refatoracoes tendem a introduzir ambiguidades.

## Escopo

- **Incluido**: context map oficial, owners, contratos de cada contexto, checklist de arquitetura por PR.
- **Excluido**: refatoracao de codigo de rotas/queries (Epic 02) e migracao de nomenclaturas (Epic 03).

---

## Tarefa 1: Definir Context Map Oficial

### Objetivo

Publicar mapa oficial dos bounded contexts com relacoes de dependencia e eventos principais.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `docs/arquitetura/ddd-context-map.md` |
| Modificar | `docs/arquitetura/visao-geral.md` |
| Modificar | `docs/adrs/006-ddd-bounded-contexts.md` |

### Implementacao

- Mapear contextos: `ConversaMedica`, `PolicyContato`, `CampanhasOutbound`, `VagasAlocacao`, `HandoffSupervisao`, `BusinessEventsAuditoria`.
- Para cada um, registrar:
  - responsabilidade
  - modelo central
  - APIs internas expostas
  - eventos consumidos/publicados
  - dependencias permitidas

### Testes Obrigatorios

**Unitarios:**
- [ ] N/A (epico documental)

**Integracao:**
- [ ] Checklist manual de consistencia entre `ddd-context-map.md` e `visao-geral.md`

### Definition of Done

- [ ] Documento publicado e revisado
- [ ] ADR-006 refletindo artefatos criados
- [ ] Referencia cruzada em arquitetura geral

### Estimativa

5 pontos

---

## Tarefa 2: Definir Ownership e Fronteiras por Contexto

### Objetivo

Remover ambiguidade de ownership tecnico e semantico.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `docs/arquitetura/ddd-ownership.md` |
| Modificar | `docs/arquitetura/servicos.md` |

### Implementacao

- Criar matriz:
  - `contexto -> owner tecnico -> owner de produto -> repositorios/modulos`
- Definir politica de mudanca cross-context:
  - requer aprovacao de owner do contexto alvo
  - requer atualizacao de contrato/evento quando houver breaking change

### Testes Obrigatorios

**Unitarios:**
- [ ] N/A

**Integracao:**
- [ ] Revisao de 2 PRs piloto usando matriz de ownership

### Definition of Done

- [ ] Ownership de todos os contextos preenchido
- [ ] Politica de change management publicada
- [ ] Owners validados em reuniao de engenharia

### Estimativa

5 pontos

---

## Tarefa 3: Criar Checklist Arquitetural para PR

### Objetivo

Aplicar governance leve para impedir erosao arquitetural apos a sprint.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `.github/pull_request_template.md` |
| Criar | `docs/arquitetura/ddd-pr-checklist.md` |

### Implementacao

- Checklist minimo:
  - contexto afetado declarado
  - SQL direto em rota? (sim/nao + justificativa)
  - alteracao de estado de dominio mapeada em contrato canonic
  - evento de dominio alterado/versionado?

### Testes Obrigatorios

**Unitarios:**
- [ ] N/A

**Integracao:**
- [ ] Simular preenchimento em 1 PR real

### Definition of Done

- [ ] Template de PR atualizado
- [ ] Checklist publicado em docs
- [ ] Time orientado sobre uso

### Estimativa

3 pontos

---

## Tarefa 4: Definir Baseline de Acoplamento (Metrica Inicial)

### Objetivo

Criar baseline quantificavel para medir impacto do Epic 02.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `docs/auditorias/ddd-baseline-2026-02-68.md` |
| Criar | `scripts/architecture/check_sql_in_routes.sh` |

### Implementacao

- Script para contar ocorrencias de `supabase.table(` em `app/api/routes`.
- Publicar baseline:
  - total de ocorrencias
  - rotas mais criticas
  - meta de reducao por sprint

### Testes Obrigatorios

**Unitarios:**
- [ ] Script retorna codigo 0 quando executado com sucesso

**Integracao:**
- [ ] Script executado em CI local (ou comando de validacao do projeto)

### Definition of Done

- [ ] Baseline publicado
- [ ] Script versionado e documentado
- [ ] Metas numericas definidas para sprint

### Estimativa

5 pontos

