# Changelog - Sprint 35: Debt Cleanup

## [Sprint 35] - 2026-01-22

### Added
- Novo módulo `app/services/campanhas/` com arquitetura limpa
  - `types.py` - Enums (TipoCampanha, StatusCampanha) e dataclasses (AudienceFilters, CampanhaData)
  - `repository.py` - CampanhaRepository para CRUD de campanhas
  - `executor.py` - CampanhaExecutor para execução de campanhas
  - `__init__.py` - Exports públicos do módulo
  - `README.md` - Documentação do módulo
- 63 novos testes unitários para o módulo de campanhas
  - 7 testes para hotfix (test_campanha_hotfix.py)
  - 21 testes para repository (test_repository.py)
  - 16 testes para executor (test_executor.py)
  - 19 testes para endpoints (test_campanhas.py)
- Novos endpoints de API
  - `GET /campanhas/` - Listar campanhas com filtros
  - `GET /campanhas/{id}` - Buscar campanha por ID
  - `PATCH /campanhas/{id}/status` - Atualizar status
- Documentação completa
  - `docs/arquitetura/campanhas.md` - Arquitetura do módulo
  - `docs/arquitetura/schema-campanhas.md` - Schema do banco
  - `docs/arquitetura/migracao-campanhas-codigo.md` - Guia de migração

### Changed
- Endpoints de campanhas agora usam novos módulos
  - `POST /campanhas/` - Usa `campanha_repository.criar()`
  - `POST /campanhas/{id}/iniciar` - Usa `campanha_executor.executar()`
  - `GET /campanhas/{id}/relatorio` - Usa `campanha_repository.buscar_por_id()`
- `app/services/jobs/campanhas.py` - Usa novo executor e repository
- `app/api/routes/piloto.py` - Usa `fila_mensagens` em vez de `envios_campanha`
- Geração de mensagem discovery agora usa `obter_abertura_texto()` para variedade

### Deprecated
- `app/services/campanha.py` - Usar `app/services/campanhas/` em vez disso
  - `criar_campanha_piloto()` - Usa colunas legadas
  - `executar_campanha()` - Usa tabela removida
  - `controlador_envio` - Usa tabela removida
- `scripts/executar_piloto.py` - Script legado que não funciona mais

### Removed
- Referências a tabela `envios_campanha` (removida do banco)
- Uso de colunas inexistentes:
  - `mensagem_template` - Nunca existiu, usar `corpo` + geração dinâmica
  - `tipo` - Usar `tipo_campanha`
  - `config` - Usar `audience_filters`
  - `nome` - Usar `nome_template`
  - `envios_criados` - Usar `enviados`

### Fixed
- `KeyError: 'mensagem_template'` ao executar campanha 16
- Endpoint `POST /campanhas/` usando colunas erradas
- Endpoint `GET /campanhas/{id}/relatorio` com KeyError
- Endpoint `GET /piloto/status` usando tabela removida

### Security
- N/A

### Performance
- N/A

---

## Commits

1. `b65092e` - fix(campanhas): corrigir criar_envios_campanha para schema atual
2. `d35ffbb` - docs(campanhas): adicionar documentacao de schema e guia de migracao
3. `7bec80f` - feat(campanhas): criar modulo campanhas com repository e types
4. `d925075` - feat(campanhas): criar executor e atualizar job de campanhas
5. `b7e4151` - refactor(campanhas): update API endpoints to use new modules
6. `2793115` - refactor(campanhas): add deprecation warnings to legacy code

---

## Métricas

| Métrica | Valor |
|---------|-------|
| Arquivos criados | 8 |
| Arquivos modificados | 5 |
| Testes adicionados | 63 |
| Cobertura campanhas | 144 testes passando |

---

## Próximos Passos

- [ ] Corrigir 3 falhas pré-existentes (persona + arquitetura)
- [ ] Remover código deprecated após período de depreciação
- [ ] Migrar chamadas restantes de `app/services/campanha.py`
