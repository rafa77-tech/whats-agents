# Decisoes Tecnicas: Codigo vs Banco

> Documento de analise para definir se o codigo deve se adequar ao banco ou vice-versa

---

## Criterios de Decisao

### Quando o CODIGO deve se adequar ao BANCO

1. **Banco ja esta em producao com dados** - Migrar schema pode causar perda de dados ou downtime
2. **Schema do banco esta correto semanticamente** - Nomes fazem sentido, estrutura adequada
3. **Codigo esta claramente desatualizado** - Usa nomes legados de versoes anteriores
4. **Custo de migracao de banco alto** - Muitas tabelas, views, triggers dependem do schema atual

### Quando o BANCO deve se adequar ao CODIGO

1. **Codigo representa a arquitetura correta** - Schema do banco foi criado ad-hoc
2. **Schema do banco tem problemas semanticos** - Nomes confusos, estrutura ruim
3. **Codigo e padronizado e bem testado** - Mudar codigo quebraria muitos testes
4. **Migracao de banco e simples** - Poucos dados, sem dependencias

---

## Analise por Item

### 1. Coluna `mensagem_template` (CODIGO -> BANCO)

| Aspecto | Analise |
|---------|---------|
| Existe no banco? | NAO |
| Codigo espera? | SIM (codigo legado) |
| Semantica correta? | NAO - para discovery, mensagem e gerada dinamicamente |
| Decisao | **CODIGO se adequa** |

**Justificativa:** O conceito de `mensagem_template` nao faz sentido para campanhas discovery. A geracao dinamica via `obter_abertura()` e a arquitetura correta. O codigo legado estava errado em esperar um template fixo.

**Acao:** Codigo deve usar `corpo` quando aplicavel ou geracao dinamica para discovery.

---

### 2. Coluna `tipo` vs `tipo_campanha` (CODIGO -> BANCO)

| Aspecto | Analise |
|---------|---------|
| Existe `tipo` no banco? | NAO |
| Existe `tipo_campanha` no banco? | SIM |
| Qual nome e melhor? | `tipo_campanha` e mais explicito |
| Decisao | **CODIGO se adequa** |

**Justificativa:** `tipo_campanha` e mais explicito e evita confusao com outros `tipo` no sistema.

**Acao:** Codigo deve usar `tipo_campanha`.

---

### 3. Coluna `config` vs `audience_filters` (CODIGO -> BANCO)

| Aspecto | Analise |
|---------|---------|
| Existe `config` no banco? | NAO |
| Existe `audience_filters` no banco? | SIM |
| Qual nome e melhor? | `audience_filters` e mais especifico |
| Decisao | **CODIGO se adequa** |

**Justificativa:** `config` e generico demais. `audience_filters` descreve exatamente o que contem.

**Acao:** Codigo deve usar `audience_filters`.

---

### 4. Coluna `nome` vs `nome_template` (CODIGO -> BANCO)

| Aspecto | Analise |
|---------|---------|
| Existe `nome` no banco? | NAO |
| Existe `nome_template` no banco? | SIM |
| Qual nome e melhor? | Ambos sao razoaveis |
| Dados existentes? | SIM, com `nome_template` |
| Decisao | **CODIGO se adequa** |

**Justificativa:** Ja existem dados com `nome_template`. Migrar seria trabalho extra sem beneficio claro.

**Acao:** Codigo deve usar `nome_template`.

---

### 5. Coluna `envios_criados` vs `enviados` (CODIGO -> BANCO)

| Aspecto | Analise |
|---------|---------|
| Existe `envios_criados` no banco? | NAO |
| Existe `enviados` no banco? | SIM |
| Qual nome e melhor? | `enviados` e mais claro |
| Decisao | **CODIGO se adequa** |

**Justificativa:** `enviados` e mais direto. `envios_criados` sugere apenas criacao, nao envio real.

**Acao:** Codigo deve usar `enviados`.

---

### 6. Tabela `envios_campanha` (CODIGO -> BANCO)

| Aspecto | Analise |
|---------|---------|
| Existe no banco? | NAO (foi removida) |
| Codigo espera? | SIM (codigo legado) |
| Substituicao existe? | SIM - `fila_mensagens` + views |
| Decisao | **CODIGO se adequa** |

**Justificativa:** A tabela foi removida como parte da migracao de arquitetura. As views `campaign_sends` e `campaign_metrics` ja fornecem a funcionalidade necessaria.

**Acao:** Codigo deve usar `fila_mensagens` via `fila_service.enfileirar()`.

---

### 7. Estrutura de `audience_filters` (A AVALIAR)

| Campo no codigo | Campo no banco | Decisao |
|-----------------|----------------|---------|
| `filtro_especialidades` | `especialidades` | **CODIGO se adequa** |
| `filtro_regioes` | `regioes` | **CODIGO se adequa** |
| `filtro_tags` | NAO EXISTE | **Avaliar se necessario** |

**Justificativa:** Os nomes no banco (`especialidades`, `regioes`) sao mais limpos, sem prefixo redundante.

**Acao pendente:** Verificar se `filtro_tags` e usado em algum lugar. Se nao, ignorar.

---

## Resumo de Decisoes

| Item | Decisao | Acao |
|------|---------|------|
| `mensagem_template` | Codigo se adequa | Usar geracao dinamica ou `corpo` |
| `tipo` vs `tipo_campanha` | Codigo se adequa | Usar `tipo_campanha` |
| `config` vs `audience_filters` | Codigo se adequa | Usar `audience_filters` |
| `nome` vs `nome_template` | Codigo se adequa | Usar `nome_template` |
| `envios_criados` vs `enviados` | Codigo se adequa | Usar `enviados` |
| `envios_campanha` (tabela) | Codigo se adequa | Usar `fila_mensagens` |
| Subcampos de filtros | Codigo se adequa | Usar nomes do banco |

**Conclusao:** Em todos os casos, o **codigo deve se adequar ao banco**. O schema atual do banco representa a arquitetura correta e moderna, enquanto o codigo esta preso em convencoes da epoca do Twilio.

---

## Casos que Precisam de Migracao de Banco (Nenhum Identificado)

Nao foram identificados casos onde o banco precisa ser alterado para esta sprint.

Se no futuro for necessario:
- Criar migration com `mcp__supabase__apply_migration`
- Testar em ambiente de desenvolvimento primeiro
- Documentar razao da mudanca

---

## Proximos Passos

1. **Epic 01:** Hotfix imediato para campanha 16 funcionar
2. **Epics 03-05:** Refatorar codigo para usar nomes corretos do banco
3. **Epic 06:** Remover todas referencias a codigo legado
4. **Validacao:** Garantir que nenhum codigo usa nomes antigos
