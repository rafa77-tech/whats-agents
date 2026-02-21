# ADR-007: Isolar Domínio de Interface (Sem SQL Direto em Rotas)

- Status: Proposta
- Data: 2026-02-21
- Sprint: Backlog Arquitetural (DDD)
- Decisores: Equipe de Engenharia

## Contexto

Há múltiplos endpoints acessando `supabase.table(...)` diretamente em camada de rota, inclusive em áreas onde já existem serviços/repositórios de domínio.

Exemplos:

- `app/api/routes/campanhas.py:259`
- `app/api/routes/group_entry.py:200`
- `app/api/routes/policy.py:602`
- `app/api/routes/incidents.py:61`

Isso mistura interface + aplicação + persistência no mesmo ponto, dificulta testes por contexto e espalha regras.

## Decisão

Adotar regra arquitetural:

1. Rotas API não executam acesso direto a banco para casos de domínio.
2. Rotas chamam **Application Services** por contexto.
3. Persistência fica em **Repositories** do contexto.

Exceções permitidas:

- Endpoints técnicos de health/debug estritamente operacionais.
- Scripts/migrações fora da camada de runtime da API.

Estrutura alvo (exemplo):

- `app/contexts/campanhas/application.py`
- `app/contexts/campanhas/repositories/*.py`
- `app/api/routes/campanhas.py` (apenas orchestration HTTP)

## Alternativas Consideradas

1. **Permitir SQL direto em rotas com convenção informal**
   - Pros: menor esforço imediato
   - Cons: dívida estrutural contínua, baixa previsibilidade

2. **Aplicar só para novos módulos**
   - Pros: menor custo de adoção
   - Cons: legado crítico permanece sem controle

3. **Aplicar para novos módulos + migração gradual dos críticos (decisão escolhida)**
   - Pros: equilíbrio risco/benefício
   - Cons: exige plano incremental e governança de transição

## Consequências

### Positivas

- Fronteira clara entre interface e domínio
- Redução de duplicação de regra de negócio
- Melhor testabilidade de casos de uso
- Evolução mais segura por contexto

### Negativas

- Trabalho de refatoração em endpoints legados
- Mais arquivos/camadas para navegar inicialmente

### Mitigações

- Migrar primeiro os contextos críticos (`campanhas`, `policy`, `group_entry`)
- Introduzir linter/check simples para bloquear novo SQL direto em rotas
- Criar templates de application service para acelerar adoção

## Referências

- `docs/auditorias/relatorio-ddd-2026-02-21.md`
- `app/repositories/base.py:28`
- `app/repositories/cliente.py:79`
