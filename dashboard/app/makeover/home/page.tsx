const kpis = [
  { label: 'Taxa de resposta', value: '98%', delta: '+2%' },
  { label: 'Conversao', value: '12%', delta: '+1%' },
  { label: 'Latencia media', value: '1.6s', delta: '-0.2s' },
  { label: 'Fila', value: '4', delta: '-3' },
]

const criticalConversations = [
  { name: 'Dra. Ana', time: '12 min', status: 'Sem resposta' },
  { name: 'Dr. Carlos', time: '18 min', status: 'Sem resposta' },
  { name: 'Dra. Flavia', time: '24 min', status: 'Risco de perda' },
]

const activeCampaigns = [
  { name: 'Reativacao SP', status: 'Rodando', kpi: '2.4% resp.' },
  { name: 'Plantao Noturno', status: 'Pausada', kpi: '0.9% resp.' },
  { name: 'Recuperacao Inativos', status: 'Rodando', kpi: '3.1% resp.' },
]

export default function MakeoverHomePage() {
  return (
    <div className="space-y-8">
      <section className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-border p-5">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Saude do sistema</div>
          <div className="mt-3 font-display text-3xl">95/100</div>
          <div className="mt-2 text-sm text-muted-foreground">Sem incidentes criticos ativos.</div>
          <button className="mt-4 rounded-md border border-border px-3 py-2 text-xs">Ver Health</button>
        </div>
        <div className="rounded-lg border border-border p-5">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Campanhas ativas</div>
          <ul className="mt-4 space-y-2 text-sm">
            {activeCampaigns.map((campaign) => (
              <li key={campaign.name} className="flex items-center justify-between">
                <span className="font-medium">{campaign.name}</span>
                <span className="text-muted-foreground">{campaign.kpi}</span>
              </li>
            ))}
          </ul>
          <button className="mt-4 rounded-md border border-border px-3 py-2 text-xs">Abrir campanhas</button>
        </div>
        <div className="rounded-lg border border-border p-5">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Conversas criticas</div>
          <ul className="mt-4 space-y-2 text-sm">
            {criticalConversations.map((item) => (
              <li key={item.name} className="flex items-center justify-between">
                <span className="font-medium">{item.name}</span>
                <span className="text-muted-foreground">{item.time}</span>
              </li>
            ))}
          </ul>
          <button className="mt-4 rounded-md border border-border px-3 py-2 text-xs">Ir para inbox</button>
        </div>
      </section>

      <section className="rounded-lg border border-border p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Proxima acao</div>
            <div className="mt-2 font-display text-2xl">Resolver alerta de conexao perdida</div>
            <div className="text-sm text-muted-foreground">Chip zapi-revoluna desconectado ha 10h.</div>
          </div>
          <button className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white">
            Ir para alertas
          </button>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-border p-4">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">{kpi.label}</div>
            <div className="mt-2 font-display text-2xl">{kpi.value}</div>
            <div className="text-xs text-muted-foreground">{kpi.delta}</div>
          </div>
        ))}
      </section>
    </div>
  )
}
