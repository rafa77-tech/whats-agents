# Templates de Campanha

Templates para cada tipo de campanha da Julia.

## Como Usar

1. **Copie os templates para o Google Drive**
   - Crie uma pasta chamada `Templates` dentro da pasta de Briefings
   - Dentro de `Templates`, crie subpastas para cada tipo:
     - `Discovery/`
     - `Oferta/`
     - `Reativacao/`
     - `Followup/`
     - `Feedback/`

2. **Copie os arquivos .md para cada pasta**
   - Crie um Google Doc em cada subpasta
   - Cole o conteúdo do template correspondente
   - Nomeie com data: `discovery_2025-01-15`

3. **Configure a variável de ambiente**
   ```
   GOOGLE_TEMPLATES_FOLDER_ID=<ID da pasta Templates>
   ```

4. **A Julia sincroniza diariamente**
   - Busca o arquivo mais recente de cada pasta
   - Usa a data no nome do arquivo para ordenar
   - Armazena no banco para uso nos prompts

## Estrutura das Pastas

```
📁 Briefings Julia/
├── 📁 Templates/                    ← GOOGLE_TEMPLATES_FOLDER_ID
│   ├── 📁 Discovery/
│   │   ├── discovery_2025-01-15     ← Mais recente (usado)
│   │   └── discovery_2025-01-01     ← Arquivo antigo (ignorado)
│   ├── 📁 Oferta/
│   │   └── oferta_2025-01-14
│   ├── 📁 Reativacao/
│   │   └── reativacao_2025-01-10
│   ├── 📁 Followup/
│   │   └── followup_2025-01-12
│   └── 📁 Feedback/
│       └── feedback_2025-01-05
│
└── 📁 Diario/
    └── briefing_2025-01-16.md
```

## Templates Disponíveis

| Template | Arquivo | Descrição |
|----------|---------|-----------|
| Discovery | `discovery_2025-01-01.md` | Primeiro contato com médico novo |
| Oferta | `oferta_2025-01-01.md` | Oferecer vaga específica |
| Reativação | `reativacao_2025-01-01.md` | Retomar contato após 60+ dias |
| Follow-up | `followup_2025-01-01.md` | Seguir após sem resposta |
| Feedback | `feedback_2025-01-01.md` | Coletar feedback pós-plantão |

## Seções do Template

Cada template deve conter:

- `## Objetivo` - O que a campanha quer alcançar
- `## Tom` - Como a Julia deve se comunicar
- `## Informações Importantes` - Dados que precisa ter em mãos
- `## O que NÃO fazer` - Erros a evitar
- `## Exemplo de Abertura` - Mensagem modelo
- `## Follow-up` - Regras de seguimento
- `## Margem de Negociação` (opcional) - Limite para negociar valores

## Atualizando Templates

Para atualizar um template:

1. Crie um novo arquivo com data mais recente
2. Ex: `discovery_2025-01-20` substitui `discovery_2025-01-15`
3. A Julia automaticamente usa o mais recente
4. Mantenha arquivos antigos para histórico

## Sync Manual

```bash
# Via API
curl -X POST http://localhost:8000/jobs/sync-templates

# Via Slack
@Julia sync templates
```
