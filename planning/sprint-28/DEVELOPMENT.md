# Sprint 28 - Guia de Desenvolvimento

## Branch Strategy

```
main (producao)
  └── sprint-28/dashboard (desenvolvimento)
```

## Ambientes

| Ambiente | Branch | Supabase | Railway Service | URL |
|----------|--------|----------|-----------------|-----|
| **DEV** | `sprint-28/dashboard` | `supabase-dev` (ofpnronthwcsybfxnxgj) | `julia-dashboard-dev` | A configurar |
| **PROD** | `main` | `supabase-prod` (jyqgbzhqavgpxqacduoi) | `julia-dashboard` | A configurar |

---

## Setup Ambiente DEV no Railway

### Passo 1: Criar Novo Servico

1. Acesse [Railway Dashboard](https://railway.app)
2. Abra o projeto `remarkable-communication`
3. Clique em **"+ New Service"**
4. Selecione **"GitHub Repo"**
5. Escolha o repositorio `whats-agents`

### Passo 2: Configurar Branch e Diretorio

No painel do novo servico:

1. **Settings > Source**
   - Branch: `sprint-28/dashboard`
   - Root Directory: `/dashboard`

2. **Settings > Build**
   - Builder: `Nixpacks`
   - Build Command: `npm run build`
   - Start Command: `npm run start`

3. **Settings > Networking**
   - Generate Domain: Clicar para gerar URL publica

### Passo 3: Configurar Variaveis de Ambiente

Em **Variables**, adicionar:

```bash
# Supabase DEV
NEXT_PUBLIC_SUPABASE_URL=https://ofpnronthwcsybfxnxgj.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key-do-supabase-dev>

# API Backend (mesmo do backend em producao ou um dev)
NEXT_PUBLIC_API_URL=https://whats-agents-production.up.railway.app

# Ambiente
NEXT_PUBLIC_ENV=development
NODE_ENV=production
```

### Passo 4: Nomear o Servico

1. Clique no nome do servico (canto superior)
2. Renomeie para: `julia-dashboard-dev`

### Passo 5: Deploy

O Railway fara deploy automatico a cada push no branch `sprint-28/dashboard`.

---

## Desenvolvimento Local

### Pré-requisitos

- Node.js 18+
- npm ou pnpm

### Setup

```bash
cd dashboard

# Instalar dependencias
npm install

# Copiar variaveis de ambiente
cp .env.example .env.local

# Editar .env.local com as credenciais do Supabase DEV

# Rodar em modo desenvolvimento
npm run dev
```

Acesse: http://localhost:3000

---

## Fluxo de Trabalho

### 1. Desenvolvimento

```bash
# Certifique-se de estar no branch correto
git checkout sprint-28/dashboard

# Fazer alteracoes...

# Commitar
git add .
git commit -m "feat(dashboard): descricao"

# Push (triggera deploy no Railway dev)
git push origin sprint-28/dashboard
```

### 2. Testar em DEV

- Acessar URL do Railway dev
- Testar funcionalidades
- Verificar logs no Railway

### 3. Merge para Producao

```bash
# Quando estiver pronto para producao
git checkout main
git merge sprint-28/dashboard
git push origin main
```

O merge para `main` vai triggerar o deploy de producao.

---

## Variaveis por Ambiente

### DEV (.env.local ou Railway dev)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://ofpnronthwcsybfxnxgj.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<dev-anon-key>
NEXT_PUBLIC_API_URL=https://whats-agents-production.up.railway.app
NEXT_PUBLIC_ENV=development
```

### PROD (Railway production)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://jyqgbzhqavgpxqacduoi.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<prod-anon-key>
NEXT_PUBLIC_API_URL=https://whats-agents-production.up.railway.app
NEXT_PUBLIC_ENV=production
```

---

## Estrutura do Projeto

```
/dashboard
├── app/                      # Next.js App Router
│   ├── (auth)/              # Rotas de autenticacao
│   │   ├── login/
│   │   └── callback/
│   ├── (dashboard)/         # Rotas protegidas
│   │   ├── page.tsx         # Dashboard principal
│   │   ├── conversas/
│   │   ├── medicos/
│   │   ├── vagas/
│   │   ├── campanhas/
│   │   ├── metricas/
│   │   ├── sistema/
│   │   └── auditoria/
│   ├── api/                 # API routes (BFF)
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── components/
│   ├── ui/                  # Componentes base (shadcn/ui)
│   ├── dashboard/           # Componentes do dashboard
│   └── charts/              # Graficos
├── lib/
│   ├── supabase/            # Clients Supabase
│   ├── api/                 # Client para FastAPI
│   └── utils/               # Funcoes utilitarias
├── hooks/                   # Custom hooks
├── types/                   # TypeScript types
└── public/                  # Assets estaticos
```

---

## Comandos Uteis

```bash
# Desenvolvimento
npm run dev          # Rodar servidor local
npm run build        # Build de producao
npm run start        # Rodar build local
npm run lint         # Verificar linting
npm run type-check   # Verificar tipos

# Git
git checkout sprint-28/dashboard   # Ir para branch dev
git pull origin sprint-28/dashboard # Atualizar branch
```

---

## Troubleshooting

### Build falha no Railway

1. Verificar logs no Railway
2. Rodar `npm run build` localmente
3. Verificar se todas as variaveis de ambiente estao configuradas

### Supabase nao conecta

1. Verificar se as variaveis `NEXT_PUBLIC_SUPABASE_*` estao corretas
2. Verificar se o IP do Railway esta na allowlist do Supabase (se houver restricao)

### API retorna erro

1. Verificar se `NEXT_PUBLIC_API_URL` esta correto
2. Verificar CORS no backend FastAPI

---

*Criado em 03/01/2026*
