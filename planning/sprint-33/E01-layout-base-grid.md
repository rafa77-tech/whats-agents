# E01 - Layout Base e Grid

## Objetivo

Criar a estrutura base da pagina do dashboard com o grid responsivo que comportara todos os componentes.

## Contexto

O dashboard sera a pagina principal (`/`) do sistema. Atualmente, ao acessar `/`, o usuario e redirecionado para `/campanhas`. Este epico criara a pagina real do dashboard.

O layout e desktop-first com grid de alta densidade de informacao.

## Requisitos Funcionais

1. Criar pagina `/app/(dashboard)/page.tsx` como dashboard principal
2. Implementar grid responsivo com as seguintes areas:
   - Header (full width)
   - 3 colunas de cards de metricas
   - Secao de chips (full width)
   - Funil (full width)
   - 2 colunas: Tendencias | Alertas
   - Feed de atividades (full width)
3. Scroll suave na pagina
4. Background neutro (`bg-gray-50`)

## Requisitos Tecnicos

### Arquivo a Criar

```
/app/(dashboard)/page.tsx
```

### Estrutura do Grid (CSS Grid)

```
desktop (>= 1280px):
┌─────────────────────────────────────────┐
│              HEADER                      │
├─────────────┬─────────────┬─────────────┤
│  METRICAS   │  QUALIDADE  │ OPERACIONAL │
├─────────────┴─────────────┴─────────────┤
│              CHIPS POOL                  │
├─────────────────────────────────────────┤
│              FUNIL                       │
├───────────────────┬─────────────────────┤
│    TENDENCIAS     │      ALERTAS        │
├───────────────────┴─────────────────────┤
│           ACTIVITY FEED                  │
└─────────────────────────────────────────┘
```

### Codigo Base

```tsx
// app/(dashboard)/page.tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <section>
        {/* E02 implementara */}
        <div className="h-16 bg-white rounded-lg border" />
      </section>

      {/* Cards de Metricas - 3 colunas */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* E03, E04, E05 implementarao */}
        <div className="h-48 bg-white rounded-lg border" />
        <div className="h-48 bg-white rounded-lg border" />
        <div className="h-48 bg-white rounded-lg border" />
      </section>

      {/* Pool de Chips */}
      <section>
        {/* E06, E07 implementarao */}
        <div className="h-64 bg-white rounded-lg border" />
      </section>

      {/* Funil */}
      <section>
        {/* E10 implementara */}
        <div className="h-48 bg-white rounded-lg border" />
      </section>

      {/* Tendencias e Alertas - 2 colunas */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* E12 implementara */}
        <div className="h-64 bg-white rounded-lg border" />
        {/* E13 implementara */}
        <div className="h-64 bg-white rounded-lg border" />
      </section>

      {/* Activity Feed */}
      <section>
        {/* E14 implementara */}
        <div className="h-48 bg-white rounded-lg border" />
      </section>
    </div>
  );
}
```

## Criterios de Aceite

- [ ] Acessar `/` exibe a pagina do dashboard (nao redireciona para `/campanhas`)
- [ ] Layout exibe placeholders para todas as secoes
- [ ] Grid responsivo funciona em telas >= 1024px
- [ ] Espacamento consistente entre secoes (24px / `gap-6`)
- [ ] Background da pagina e `bg-gray-50`
- [ ] Cards placeholder tem `bg-white`, `rounded-lg`, `border`

## Definition of Done (DoD)

- [ ] Arquivo `/app/(dashboard)/page.tsx` criado
- [ ] Remover redirect de `/` para `/campanhas` em `middleware.ts` (se existir)
- [ ] Grid renderiza corretamente em 1280px, 1440px, 1920px
- [ ] Sem erros no console do navegador
- [ ] `npm run build` passa sem erros
- [ ] `npm run lint` passa sem erros
- [ ] Testado manualmente no Chrome

## Dependencias

- Nenhuma (primeiro epico)

## Complexidade

**Baixa** - Apenas estrutura HTML/CSS, sem logica.

## Tempo Estimado

2-3 horas

## Notas para o Desenvolvedor

1. O arquivo `page.tsx` atual em `/app/(dashboard)/` provavelmente nao existe ou redireciona. Verifique primeiro.

2. Nao se preocupe com os dados ainda - apenas crie a estrutura visual com placeholders.

3. Use classes Tailwind para o grid. Referencia:
   ```
   grid grid-cols-1 lg:grid-cols-3 gap-6
   ```

4. Os placeholders serao substituidos nos proximos epicos.
