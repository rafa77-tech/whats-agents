const jobs = [
  {
    name: 'Processar Campanhas',
    category: 'critical',
    lastRun: '41s atras',
    status: 'Sucesso',
    duration: '499ms',
    executions: '200',
  },
  {
    name: 'Processar Mensagens',
    category: 'critical',
    lastRun: '42s atras',
    status: 'Sucesso',
    duration: '506ms',
    executions: '200',
  },
  {
    name: 'Snapshot de Chips',
    category: 'daily',
    lastRun: '11h atras',
    status: 'Sucesso',
    duration: '2.2s',
    executions: '1',
  },
]

export default function MakeoverMonitorPage() {
  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Monitor</div>
          <div className="font-display text-2xl">Operacao em tempo real</div>
        </div>
        <div className="flex gap-2">
          <button className="rounded-md border border-border px-3 py-2 text-xs">Ultima hora</button>
          <button className="rounded-md border border-border px-3 py-2 text-xs">Ultimas 24h</button>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        {[
          { label: 'Jobs', value: '32' },
          { label: 'Sucesso', value: '96%' },
          { label: 'Erros', value: '1' },
          { label: 'Atrasados', value: '0' },
        ].map((item) => (
          <div key={item.label} className="rounded-lg border border-border p-4">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">
              {item.label}
            </div>
            <div className="font-display mt-2 text-2xl">{item.value}</div>
          </div>
        ))}
      </section>

      <section className="rounded-lg border border-border">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-4 py-3">
          <div className="text-sm font-medium">Jobs do sistema</div>
          <div className="flex gap-2">
            <button className="rounded-md border border-border px-3 py-2 text-xs">Status</button>
            <button className="rounded-md border border-border px-3 py-2 text-xs">Categoria</button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted text-xs uppercase tracking-widest text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Job</th>
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3">Ultima execucao</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Duracao</th>
                <th className="px-4 py-3">Execucoes</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.name} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{job.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{job.category}</td>
                  <td className="px-4 py-3 text-muted-foreground">{job.lastRun}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{job.status}</span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{job.duration}</td>
                  <td className="px-4 py-3 text-muted-foreground">{job.executions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
