# Sistema de Briefings e Templates

Este documento explica como configurar e usar o sistema de briefings da Julia.

## Visao Geral

O sistema permite que gestores configurem o comportamento da Julia via Google Docs, sem precisar alterar codigo. Existem dois componentes principais:

1. **Briefings** - Diretrizes semanais (foco, tom, vagas prioritarias)
2. **Templates de Campanha** - Modelos de mensagem por tipo de abordagem

---

## Configuracao

### Variaveis de Ambiente

```bash
# Credenciais Google (obrigatorio)
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json

# Pasta de briefings (recomendado - Sprint 11)
GOOGLE_BRIEFINGS_FOLDER_ID=1abc...xyz

# Documento unico de briefing (legado)
BRIEFING_DOC_ID=1abc...xyz

# Pasta de templates de campanha
GOOGLE_TEMPLATES_FOLDER_ID=1abc...xyz
```

### Service Account Google

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/)
2. Ative as APIs: Google Docs API e Google Drive API
3. Crie uma Service Account com papel "Editor"
4. Baixe o JSON de credenciais para `credentials/google-sa.json`
5. Compartilhe as pastas do Drive com o email da Service Account

---

## Briefings

### Estrutura do Documento

O gestor deve usar marcadores `#` e `##` literalmente:

```markdown
# Briefing Julia - Semana 15/01

## Foco da Semana
- Prioridade 1: Anestesistas do ABC
- Prioridade 2: Follow-ups com 7+ dias
- Evitar: Contatos de madrugada

## Vagas Prioritarias
- Hospital Sao Luiz Morumbi - 14/01 - ate R$ 3.000
- Hospital Albert Einstein - 15/01 - ate R$ 3.500

## Tom da Semana
- Ser mais direto, menos enrolacao
- Pode oferecer ate 10% a mais se necessario

## Observacoes
- Feriado quinta-feira
- Nao mencionar vaga X ate sexta
```

### Secoes Reconhecidas

| Secao | Uso | Destino |
|-------|-----|---------|
| `Foco da Semana` | Prioridades de abordagem | `diretrizes.tipo='foco_semana'` |
| `Tom da Semana` | Estilo de comunicacao | `diretrizes.tipo='tom_semana'` |
| `Vagas Prioritarias` | Vagas urgentes | Marca vagas como `prioridade='urgente'` |
| `Observacoes` | Notas gerais | `diretrizes.tipo='observacoes'` |
| Margem (no Tom) | Negociacao maxima | `diretrizes.tipo='margem_negociacao'` |

### Formato de Vagas Prioritarias

Cada linha deve seguir o formato:
```
- Hospital Nome - DD/MM - ate R$ Valor
```

Exemplo:
```
- Hospital Sao Luiz - 15/01 - ate R$ 3.000
- Clinica ABC - 20/01 - ate R$ 2.500
```

### Sincronizacao

- **Frequencia:** A cada 60 minutos (automatico)
- **Job:** `POST /jobs/sincronizar-briefing`
- **Cache:** Hash MD5 evita atualizacoes desnecessarias
- **Notificacao:** Slack recebe aviso quando briefing muda

---

## Templates de Campanha

### Estrutura de Pastas

```
Templates/
├── Discovery/      <- Primeiro contato
├── Oferta/         <- Ofertas de vaga
├── Reativacao/     <- Reativar medicos inativos
├── Followup/       <- Acompanhamento
└── Feedback/       <- Coleta de feedback
```

### Nomenclatura de Arquivos

```
{tipo}_{YYYY-MM-DD}.md
```

Exemplos:
- `discovery_2025-01-15.md`
- `oferta_2025-01-14.md`
- `reativacao_2025-01-10.md`

A Julia sempre usa o arquivo **mais recente** de cada pasta.

### Estrutura do Template

```markdown
## Objetivo
Fazer primeiro contato com medicos novos na base

## Tom
- Amigavel e profissional
- Nao ser invasivo
- Mostrar conhecimento sobre a especialidade

## Informacoes Importantes
- Mencionar nome da Revoluna
- Perguntar sobre disponibilidade
- Nao falar de valores no primeiro contato

## O que NAO fazer
- Nao enviar mensagens longas
- Nao pressionar por resposta
- Nao enviar fora do horario comercial

## Exemplo de Abertura
Oi Dr. {nome}! Tudo bem?

Sou a Julia da Revoluna, trabalho com escalas medicas aqui no ABC.

Vi que vc e {especialidade}, queria saber se tem interesse em conhecer nossas vagas?

## Follow-up
- Aguardar 48h antes do primeiro follow-up
- Maximo 2 follow-ups se nao responder

## Margem de Negociacao
Ate 5% de desconto no primeiro plantao
```

### Sincronizacao

- **Frequencia:** Diaria
- **Job:** `POST /jobs/sincronizar-templates`
- **Armazenamento:** Tabela `diretrizes` com `tipo='template_{tipo}'`

---

## Como a Julia Usa

### Fluxo de Dados

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Google Docs    │────▶│   Sync Job   │────▶│  diretrizes │
│  (gestor edita) │     │  (60 min)    │     │  (banco)    │
└─────────────────┘     └──────────────┘     └──────┬──────┘
                                                    │
                                                    ▼
                                            ┌──────────────┐
                                            │ Prompt Julia │
                                            │  (injetado)  │
                                            └──────────────┘
```

### Injecao no Prompt

A cada mensagem recebida, Julia carrega:
1. Diretrizes ativas do banco (`carregar_diretrizes_ativas()`)
2. Template da campanha atual (se aplicavel)
3. Injeta no system prompt com alta prioridade

### Prioridade das Diretrizes

| Tipo | Prioridade | Exemplo |
|------|------------|---------|
| Foco da Semana | 10 (alta) | "Priorizar anestesistas" |
| Tom da Semana | 8 | "Ser mais direto" |
| Margem Negociacao | 7 | "Ate 10%" |
| Observacoes | 5 | "Feriado quinta" |
| Templates | 5 | Modelo de mensagem |

---

## Comandos Slack

O gestor pode interagir com briefings via Slack:

### Listar Documentos
```
@Julia lista os briefings disponiveis
```

### Ler Documento
```
@Julia mostra o briefing da semana
```

### Analisar Briefing
```
@Julia analisa o briefing do laboratorio
```

A analise usa Claude Sonnet para:
- Entender a demanda do gestor
- Avaliar viabilidade
- Propor plano de acao
- Identificar riscos

---

## Tabelas do Banco

### diretrizes

```sql
CREATE TABLE diretrizes (
    id UUID PRIMARY KEY,
    tipo TEXT NOT NULL,           -- foco_semana, tom_semana, template_discovery, etc
    conteudo TEXT NOT NULL,       -- Conteudo ou JSON
    prioridade INT DEFAULT 5,     -- 1-10
    ativo BOOLEAN DEFAULT true,
    origem TEXT,                  -- google_docs, slack, manual
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### briefing_sync_log

```sql
CREATE TABLE briefing_sync_log (
    id UUID PRIMARY KEY,
    doc_hash TEXT,                -- MD5 do conteudo
    doc_title TEXT,
    conteudo_raw TEXT,            -- Primeiros 5000 chars
    parseado JSONB,               -- Secoes parseadas
    created_at TIMESTAMPTZ
);
```

---

## Troubleshooting

### Briefing nao sincroniza

1. Verificar credenciais Google:
   ```bash
   curl -X POST http://localhost:8000/jobs/sincronizar-briefing
   ```

2. Verificar logs:
   ```bash
   docker logs julia-api | grep briefing
   ```

3. Verificar permissoes da Service Account no Drive

### Template nao carrega

1. Verificar nomenclatura: `tipo_YYYY-MM-DD.md`
2. Verificar se pasta esta compartilhada com Service Account
3. Executar sync manual:
   ```bash
   curl -X POST http://localhost:8000/jobs/sincronizar-templates
   ```

### Diretrizes nao aparecem no prompt

1. Verificar se `ativo=true` na tabela `diretrizes`:
   ```sql
   SELECT * FROM diretrizes WHERE ativo = true ORDER BY prioridade DESC;
   ```

2. Verificar se tipo esta correto (ex: `foco_semana`, nao `foco-semana`)

---

## Boas Praticas

### Para Gestores

1. **Use marcadores literais** - `#` e `##` devem aparecer no texto
2. **Listas com `-`** - Cada item em linha separada
3. **Formato de vagas** - `Hospital - Data - ate R$ Valor`
4. **Atualize semanalmente** - Briefing desatualizado afeta qualidade
5. **Seja conciso** - Sistema le primeiros 5000 caracteres

### Para Desenvolvedores

1. **Cache por hash** - Evita updates desnecessarios
2. **Carregar do banco** - Nao usar cache em memoria para diretrizes
3. **Templates como JSON** - Flexibilidade para novos campos
4. **Log de sync** - Sempre registrar em `briefing_sync_log`
5. **Credenciais no .env** - Nunca hardcoded

---

## Arquivos Relacionados

Verificar estrutura atual em `app/services/` para paths corretos dos módulos de briefing.

---

**Validado em 10/02/2026**
