# Templates de Campanha

> Sistema de templates editaveis no Google Drive para campanhas da Julia.

---

## Visao Geral

Templates de campanha permitem que o gestor customize o comportamento da Julia para cada tipo de abordagem, sem precisar alterar codigo. Os templates ficam no Google Drive e sao sincronizados automaticamente.

### Tipos de Campanha

| Tipo | Uso | Quando |
|------|-----|--------|
| **Discovery** | Primeiro contato com medico novo | Prospeccao fria |
| **Oferta** | Oferecer vaga especifica | Medico ja conhece Revoluna |
| **Reativacao** | Retomar contato apos 60+ dias | Medico inativo |
| **Followup** | Seguir conversa sem resposta | 48h, 5 dias, 15 dias |
| **Feedback** | Coletar feedback pos-plantao | 24-48h apos plantao |

---

## Estrutura no Google Drive

```
📁 Briefings/
└── 📁 Templates/                         <- GOOGLE_TEMPLATES_FOLDER_ID
    ├── 📂 Discovery/
    │   ├── 📄 discovery_2025-01-15       <- Mais recente (usado)
    │   └── 📄 discovery_2025-01-01       <- Historico
    ├── 📂 Oferta/
    │   └── 📄 oferta_2025-01-14
    ├── 📂 Reativacao/
    │   └── 📄 reativacao_2025-01-10
    ├── 📂 Followup/
    │   └── 📄 followup_2025-01-12
    └── 📂 Feedback/
        └── 📄 feedback_2025-01-05
```

**Regras:**
- Julia usa sempre o arquivo **mais recente** de cada pasta (pela data no nome)
- Mantenha arquivos antigos para historico
- Nomes devem seguir padrao: `tipo_YYYY-MM-DD`

---

## Estrutura do Template

Cada template deve conter as seguintes secoes:

```markdown
# Template [Tipo]

## Objetivo
O que a campanha quer alcançar.

## Tom
Como a Julia deve se comunicar (lista de caracteristicas).

## Informacoes Importantes
Dados que a Julia precisa ter em maos.

## O que NAO fazer
Erros a evitar (lista).

## Exemplo de Abertura
Mensagem modelo para iniciar conversa.

## Follow-up
Regras de seguimento (timing, quantidade).

## Margem de Negociacao (opcional)
Limite para negociar valores.
```

---

## Configuracao

### 1. Variaveis de Ambiente

```bash
# ID da pasta Templates no Google Drive
GOOGLE_TEMPLATES_FOLDER_ID=1LhdnNM-lbrvso5C-ydp5mx7MRSen2Ag5

# Credenciais do Service Account
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json
```

### 2. Permissoes do Service Account

O Service Account precisa ter acesso de **Editor** na pasta:

```
julia-docs-reader@julia-briefing.iam.gserviceaccount.com
```

---

## Sincronizacao

### Automatica

A Julia sincroniza templates diariamente as **6h** via scheduler.

### Manual

```bash
# Via API
curl -X POST http://localhost:8000/jobs/sync-templates

# Via Slack
@Julia sync templates
```

---

## Setup Inicial

Para criar a estrutura de pastas automaticamente:

```bash
# Substitua pelo ID da pasta de Briefings
curl -X POST "http://localhost:8000/jobs/setup-templates?parent_folder_id=SEU_FOLDER_ID"
```

Isso cria:
- Pasta `Templates/`
- 5 subpastas (Discovery, Oferta, etc)
- Documentos iniciais com templates padrao

---

## Como Funciona

1. **Gestor edita template** no Google Drive
2. **Scheduler sincroniza** diariamente (ou manual)
3. **Julia busca template** ao iniciar conversa de campanha
4. **Template e injetado** no prompt do agente
5. **Julia segue diretrizes** do template na conversa

### Fluxo de Dados

```
Google Drive -> Sync -> Banco (diretrizes) -> Prompt Julia
```

---

## Servicos Relacionados

| Servico | Funcao |
|---------|--------|
| `campaign_templates.py` | Sync e parsing de templates |
| `google_docs.py` | Acesso ao Google Drive/Docs |
| `jobs.py` | Endpoints de sync e setup |
| `scheduler.py` | Job diario de sincronizacao |

---

## Troubleshooting

### Template nao esta sendo usado

1. Verificar se sync rodou: `GET /jobs/sync-templates`
2. Verificar banco: `SELECT * FROM diretrizes WHERE tipo LIKE 'template_%'`
3. Verificar nome do arquivo (deve ter data no formato correto)

### Erro de permissao no Google Drive

1. Verificar se pasta foi compartilhada com Service Account
2. Permissao deve ser **Editor** ou **Administrador de Conteudo**
3. Email: `julia-docs-reader@julia-briefing.iam.gserviceaccount.com`

### Sync nao encontra arquivos

1. Verificar estrutura de pastas (subpastas com nomes corretos)
2. Verificar nomes dos arquivos (`tipo_YYYY-MM-DD`)
3. Verificar `GOOGLE_TEMPLATES_FOLDER_ID` no `.env`

---

*Documentacao criada em 29/12/2025*
