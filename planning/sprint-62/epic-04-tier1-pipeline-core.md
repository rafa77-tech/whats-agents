# EPIC 04: Tier 1 Coverage — Message Pipeline Core

## Contexto

O pipeline de mensagens e o coracao do sistema — toda mensagem recebida passa por ele.
Os arquivos core (`core.py`, `processor.py`, `base.py`, `setup.py`, `post_processors.py`) somam ~970 linhas com ZERO testes diretos.
Somente 2 de 14 processors tem testes unitarios.

Bug aqui = mensagem processada na ordem errada, entregue ao medico errado, ou perdida silenciosamente.

## Escopo

- **Incluido**: Testes para pipeline core, post_processors, e processors criticos sem cobertura
- **Excluido**: Processors de baixo risco (media, presence, chatwoot sync), refatoracao do pipeline

---

## Tarefa 4.1: Testes para `app/pipeline/core.py` + `processor.py` + `base.py`

### Objetivo
Cobrir a engine de dispatch do pipeline (385 linhas combinadas, 0 testes).

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/unit/pipeline/test_core.py` |
| Ler | `app/pipeline/core.py` (49 linhas) |
| Ler | `app/pipeline/processor.py` (161 linhas) |
| Ler | `app/pipeline/base.py` (175 linhas) |

### Testes Obrigatorios

**Unitarios:**
- [ ] Pipeline processa mensagem simples end-to-end (com processors mockados)
- [ ] Processors executados na ordem correta de prioridade
- [ ] Processor que retorna "stop" interrompe o pipeline
- [ ] Processor que levanta excecao: pipeline continua com os demais (graceful)
- [ ] Contexto do pipeline propagado entre processors
- [ ] Pipeline com zero processors: mensagem passa sem alteracao

**Edge cases:**
- [ ] Mensagem vazia
- [ ] Mensagem com caracteres especiais/unicode
- [ ] Processor com timeout

### Definition of Done
- [ ] >80% de cobertura em core.py + processor.py + base.py
- [ ] Testes verificam ordering e error handling

---

## Tarefa 4.2: Testes para `app/pipeline/post_processors.py`

### Objetivo
Cobrir o post-processing que aciona LLM e entrega mensagem (507 linhas, 0 testes).

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/unit/pipeline/test_post_processors.py` |
| Ler | `app/pipeline/post_processors.py` |

### Testes Obrigatorios

**Unitarios (mocando LLM, Evolution API, Supabase):**
- [ ] Chamada ao LLM: prompt construido corretamente
- [ ] Resposta do LLM entregue via Evolution API
- [ ] Falha do LLM: fallback executado (se existir)
- [ ] Falha da Evolution API: mensagem reagendada na fila
- [ ] Rate limit atingido: mensagem NAO enviada, reagendada
- [ ] Mensagem de handoff: LLM NAO acionado
- [ ] Logging correto com contexto (medico_id, conversa_id)

**Edge cases:**
- [ ] Resposta do LLM vazia
- [ ] Resposta do LLM com tool calls
- [ ] Timeout do LLM

### Definition of Done
- [ ] >75% de cobertura em post_processors.py
- [ ] Testes verificam que falhas nao causam perda silenciosa de mensagem

---

## Tarefa 4.3: Testes para `app/pipeline/setup.py`

### Objetivo
Verificar que a montagem do pipeline registra todos os processors na ordem correta.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/unit/pipeline/test_setup.py` |
| Ler | `app/pipeline/setup.py` (79 linhas) |

### Testes Obrigatorios

- [ ] Todos os processors esperados estao registrados
- [ ] Ordem de prioridade: opt-out e handoff rodam ANTES do LLM
- [ ] Nenhum processor duplicado
- [ ] Pipeline funcional apos setup (smoke test)

### Definition of Done
- [ ] 100% de cobertura em setup.py
- [ ] Teste serve como documentacao viva da ordem do pipeline

---

## Tarefa 4.4: Testes para processors criticos sem cobertura

### Objetivo
Adicionar testes para os processors de maior risco que ainda nao tem cobertura.

### Arquivos
| Acao | Arquivo | Risco |
|------|---------|-------|
| Criar | `tests/unit/pipeline/test_human_control_processor.py` | Alto — controla se Julia responde |
| Criar | `tests/unit/pipeline/test_chip_mapping_processor.py` | Medio — roteia para chip correto |
| Ler | `app/pipeline/processors/human_control.py` | |
| Ler | `app/pipeline/processors/chip_mapping.py` | |

### Testes Obrigatorios

**human_control.py:**
- [ ] Conversa controlada por humano: bloqueia Julia
- [ ] Conversa controlada por Julia: permite processamento
- [ ] Transicao humano -> Julia: desbloqueia
- [ ] Estado `controlled_by` consultado corretamente do banco

**chip_mapping.py:**
- [ ] Mensagem roteada para chip correto baseado no medico
- [ ] Chip indisponivel: fallback para outro chip
- [ ] Nenhum chip disponivel: mensagem enfileirada

### Definition of Done
- [ ] >80% de cobertura nos processors testados
- [ ] Processors criticos documentados via testes
