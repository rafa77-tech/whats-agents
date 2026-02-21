# EPIC 04: Template Management System

## Status: Implementado

## Contexto

Sistema completo de CRUD para templates Meta com approval workflow, variable mapping, e API routes protegidas. Templates sao a unica forma de iniciar conversas fora da janela 24h — componente critico para campanhas outbound.

## Escopo

- **Incluido**: Template service, variable mapper, API routes com auth guard, seed templates
- **Excluido**: Dashboard UI (sprint 69), MM Lite (sprint 68), Rich Media templates (sprint 68)

---

## Tarefa 04.1: Template Service

### Arquivo: `app/services/meta/template_service.py` (403 linhas)

`MetaTemplateService` (singleton `template_service`):

| Metodo | Descricao |
|--------|-----------|
| `_obter_access_token(waba_id)` | Busca token na tabela chips (campo `meta_access_token`) |
| `criar_template(waba_id, name, category, language, components)` | POST Graph API + upsert local. Se Meta falha, salva local com status `SUBMIT_ERROR` |
| `listar_templates(waba_id, status=None)` | Query local com filtro opcional |
| `buscar_template_por_nome(template_name)` | Query local, retorna apenas APPROVED |
| `sincronizar_templates(waba_id)` | GET da Meta + upsert local (syncs all) |
| `deletar_template(waba_id, template_name)` | DELETE Meta + DELETE local. Sem token → remove apenas local |

### Decisoes de design

1. **Access token do banco**: Nao usa envvar — cada WABA pode ter token diferente. Token fica na tabela `chips` campo `meta_access_token`.
2. **Salvar local mesmo com erro Meta**: Template com `SUBMIT_ERROR` pode ser resubmetido depois. Nao perde o trabalho do usuario.
3. **Singleton**: `template_service = MetaTemplateService()` — instancia unica reutilizada.

### Testes: `tests/services/meta/test_template_service.py` (12 testes)

| Classe | Testes |
|--------|--------|
| TestObterAccessToken | encontra_token, token_nao_encontrado, token_erro_retorna_none |
| TestCriarTemplate | criar_sucesso, criar_sem_access_token, criar_erro_meta_salva_local |
| TestListarTemplates | listar_todos, listar_com_filtro_status |
| TestBuscarTemplatePorNome | buscar_approved, buscar_nao_encontrado |
| TestSincronizarTemplates | sync_sucesso, sync_sem_token |
| TestDeletarTemplate | deletar_sucesso, deletar_sem_token_remove_local |

---

## Tarefa 04.2: Template Variable Mapper

### Arquivo: `app/services/meta/template_mapper.py` (99 linhas)

`TemplateMapper` (singleton `template_mapper`):

| Metodo | Descricao |
|--------|-----------|
| `mapear_variaveis(template, destinatario, campanha)` | Le `variable_mapping` do template, resolve valores, retorna formato Graph API |
| `_resolver_variavel(var_name, destinatario, campanha)` | Resolve nome da variavel para valor concreto |

### Variaveis suportadas

| Variavel | Aliases | Fonte |
|----------|---------|-------|
| `nome` | `name` | `destinatario["nome"]` |
| `especialidade` | `specialty` | `destinatario["especialidade"]` |
| `hospital` | `hospital_name` | `campanha["hospital"]` ou `destinatario["hospital"]` |
| `data_plantao` | `date`, `data` | `campanha["data_plantao"]` |
| `valor` | `value`, `price` | `campanha["valor"]` |
| `horario` | `time`, `schedule` | `campanha["horario"]` |
| `periodo` | `period`, `shift` | `campanha["periodo"]` |
| `setor` | `sector`, `department` | `campanha["setor"]` |

### Formato de saida (Graph API)

```json
[
  {
    "type": "body",
    "parameters": [
      {"type": "text", "text": "Dr Carlos"},
      {"type": "text", "text": "Cardiologia"}
    ]
  }
]
```

### Testes: `tests/services/meta/test_template_mapper.py` (~13 testes)

| Area | Testes |
|------|--------|
| Mapeamento basico | nome, especialidade |
| Mapeamento completo | 6 variaveis |
| Variavel ausente | usa string vazia |
| Template sem mapping | retorna [] |
| Aliases | name → nome, specialty → especialidade |
| Formato Graph API | validacao de estrutura |

---

## Tarefa 04.3: Template API Routes

### Arquivo: `app/api/routes/meta_templates.py` (157 linhas)

6 endpoints protegidos por `X-API-Key` (validado contra `settings.JWT_SECRET_KEY`):

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/meta/templates` | Criar e submeter template |
| GET | `/meta/templates` | Listar templates (query params: waba_id, status, category) |
| GET | `/meta/templates/{name}` | Buscar template por nome |
| PUT | `/meta/templates/{name}` | Atualizar template |
| DELETE | `/meta/templates/{name}` | Deletar template |
| POST | `/meta/templates/sync` | Sincronizar com Meta Graph API |

### Auth Guard

```python
async def _verificar_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.JWT_SECRET_KEY:
        raise HTTPException(401, "Invalid API key")
```

Todos os endpoints usam `Depends(_verificar_api_key)`.

### Request Models

| Model | Campos |
|-------|--------|
| `CreateTemplateRequest` | waba_id, name, category, language (default pt_BR), components |
| `UpdateTemplateRequest` | waba_id, components |
| `DeleteTemplateRequest` | waba_id |
| `SyncTemplatesRequest` | waba_id |

**Seguranca**: Nenhum model aceita `access_token` — token e buscado internamente pelo service.

### Validacao

- `category` deve ser MARKETING, UTILITY, ou AUTHENTICATION (senao → 400)
- `waba_id` obrigatorio em todos os endpoints
- Template nao encontrado → 404
- GET `/meta/templates` com `category` filtra client-side (retorno filtrado)

### Testes: `tests/api/routes/test_meta_templates.py` (10 testes)

| Classe | Testes |
|--------|--------|
| TestAuth | sem_api_key_422, api_key_invalida_401, api_key_valida_aceita |
| TestCriarTemplate | criar_sucesso, criar_categoria_invalida_400, criar_sem_access_token_no_body |
| TestListarTemplates | listar_com_filtros |
| TestBuscarTemplate | buscar_encontrado, buscar_nao_encontrado_404 |
| TestDeletarTemplate | deletar_sucesso |
| TestSincronizarTemplates | sync_sucesso |

---

## Tarefa 04.4: Seed Templates

5 templates iniciais inseridos na tabela `meta_templates` com variable_mapping:

| Nome | Categoria | Variaveis | Buttons |
|------|-----------|-----------|---------|
| `julia_discovery_v1` | MARKETING | {{1}}=nome | [Sim] [Agora nao] |
| `julia_oferta_v1` | MARKETING | {{1}}=nome, {{2}}=especialidade, {{3}}=hospital, {{4}}=data, {{5}}=horario, {{6}}=valor | [Tenho interesse] [Nao posso] |
| `julia_reativacao_v1` | MARKETING | {{1}}=nome, {{2}}=especialidade | [Pode mandar] [Sem interesse] |
| `julia_followup_v1` | UTILITY | {{1}}=nome, {{2}}=hospital | [Sim] [Nao] |
| `julia_confirmacao_v1` | UTILITY | {{1}}=nome, {{2}}=data, {{3}}=hospital | [Confirmado] [Preciso remarcar] |

**Status**: Inseridos com `waba_id="PLACEHOLDER_WABA"`. Quando WABA real for criada, rodar sync para atualizar.

---

## Definition of Done

- [x] Template service com 6 metodos CRUD
- [x] Access token buscado do banco (nao via envvar)
- [x] Variable mapper com 8 variaveis + aliases
- [x] 6 endpoints REST com auth guard (X-API-Key)
- [x] Nenhum endpoint aceita access_token no body
- [x] 5 seed templates inseridos
- [x] 12 + 13 + 10 = 35 testes passando

## Gaps Identificados

- [ ] PUT /meta/templates/{name} nao tem testes
- [ ] Template validation (nome com caracteres invalidos, components invalidos) — sem validacao
- [ ] Quality score do template nao e usado para decisoes de routing
- [ ] Nao ha cron job para sincronizar templates periodicamente
- [ ] Rich Media templates (header image/video) nao suportados (sprint 68)
