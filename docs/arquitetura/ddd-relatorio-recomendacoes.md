# Relatório de Arquitetura e Recomendações DDD - Projeto Julia

**Status:** Proposta Inicial (v1.0)
**Data:** 2026-02-21
**Autores:** Manus AI, Rafael

> **Nota:** O Context Map canônico está em `docs/arquitetura/ddd-context-map.md`.
> Este documento complementa o mapa com análise de dívida técnica e plano de ação.

## 1. Visão Geral e Objetivo

Este documento apresenta uma análise da arquitetura atual do projeto Julia sob a ótica do **Domain-Driven Design (DDD)**. Ele se baseia nos documentos de diagnóstico existentes (ADRs, relatórios) e em uma análise estática da base de código.

O objetivo é fornecer um **diagnóstico visual e acionável** dos pontos fortes e das áreas de melhoria, além de um **plano de refatoração pragmático** para fortalecer as fronteiras dos contextos de domínio, reduzir o acoplamento e aumentar a manutenibilidade e a escalabilidade do sistema.

## 2. Context Map

Veja `docs/arquitetura/ddd-context-map.md` para o diagrama canônico e descrição dos Bounded Contexts.

### Padrões de Relacionamento (complementar ao mapa)

| Relação | Padrão | Observação |
| :--- | :--- | :--- |
| ConversaMedica ↔ PolicyContato | Partnership | Evolução conjunta obrigatória |
| VagasAlocacao → ConversaMedica | Upstream/Downstream | VA define contratos de oferta |
| CampanhasOutbound → ConversaMedica | Downstream | CO inicia conversas, CM processa |
| ConversaMedica → HandoffSupervisao | Downstream | CM detecta, HS executa handoff |
| GroupEntry → ConversaMedica | Downstream | GE detecta leads, CM conversa |

## 3. Mapa de Calor da Dívida Arquitetural

A intensidade representa chamadas diretas a `supabase.table()` dentro dos arquivos de rotas da API, violando o **ADR-007** (sem SQL direto em rotas).

| Arquivo da Rota (`app/api/routes/`) | Nível de Dívida (Chamadas Diretas) | Prioridade de Refatoração |
| :--- | :--- | :--- |
| `supervisor_channel.py` | **MUITO ALTO** (>20) | **1a** |
| `campanhas.py` | **ALTO** (>10) | **2a** |
| `webhook_router.py` | **ALTO** (>10) | **3a** |
| `webhook_zapi.py` | **ALTO** (>10) | **3a** |
| `group_entry.py` | **MEDIO** (>4) | **4a** |
| `policy.py` | **BAIXO** (1) | **5a** |

## 4. Recomendações e Plano de Ação

### Fase 1: Fundações e Application Service (atual)

1. **Linguagem Ubíqua oficializada:** `docs/arquitetura/ddd-glossario-dominio.md`
2. **Application Service de Campanhas:** `app/contexts/campanhas/application.py`
   - Usa o repositório existente (`app/services/campanhas/repository.py`)
   - Lança exceções de domínio (`app/core/exceptions.py`)
   - Aceita injeção de dependências para testes
3. **Context Map:** `docs/arquitetura/ddd-context-map.md`

### Fase 2: Refatoração Incremental (próximas sprints)

1. **Aplicar o padrão:** Usar o Application Service de Campanhas como modelo para refatorar os outros contextos críticos, seguindo a ordem de prioridade do Mapa de Calor.
2. **Migrar rotas existentes:** Ao invés de criar rotas `/v2/`, refatorar as rotas existentes para delegar ao Application Service.
3. **Fortalecer governança:** Adicionar check no processo de Code Review para impedir novos acessos diretos ao Supabase em arquivos de rotas.

### Fase 3: Consolidação do Domínio

1. **Modelar Agregados:** Após isolar a persistência, modelar Agregados explícitos (ex: `Medico`, `Campanha`) para garantir a consistência transacional.
2. **Anti-Corruption Layers (ACL):** Implementar ACLs formais para integrações externas (WhatsApp, Slack), protegendo o domínio de mudanças em APIs de terceiros.

## 5. Governança

- Toda nova rota deve delegar a um Application Service (ADR-007)
- Repositórios existentes em `app/services/*/` são a fonte de verdade para persistência
- Novos Application Services vão em `app/contexts/<contexto>/application.py`
- Exceções de domínio em `app/core/exceptions.py`, nunca HTTPException no Application Service
