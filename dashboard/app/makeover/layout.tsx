import Link from 'next/link'

const navSections = [
  {
    title: 'Centro de Comando',
    items: [
      { label: 'Home', href: '/makeover/home' as const },
      { label: 'Alertas', href: '/makeover/monitor' as const },
    ],
  },
  {
    title: 'Operacao',
    items: [
      { label: 'Monitor', href: '/makeover/monitor' as const },
      { label: 'Health', href: '/makeover/monitor' as const },
    ],
  },
  {
    title: 'Core',
    items: [
      { label: 'Campanhas', href: '/makeover/home' as const },
      { label: 'Conversas', href: '/makeover/home' as const },
      { label: 'Vagas', href: '/makeover/home' as const },
    ],
  },
  {
    title: 'Infra',
    items: [
      { label: 'Chips', href: '/makeover/monitor' as const },
      { label: 'Warmup', href: '/makeover/monitor' as const },
      { label: 'Grupos', href: '/makeover/monitor' as const },
    ],
  },
]

export default function MakeoverLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 flex-shrink-0 border-r border-border bg-white p-6 lg:block">
          <div className="mb-8">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Jull.ia</div>
            <div className="font-display text-xl">Controle</div>
          </div>
          <nav className="space-y-6 text-sm">
            {navSections.map((section) => (
              <div key={section.title}>
                <div className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
                  {section.title}
                </div>
                <ul className="space-y-1">
                  {section.items.map((item) => (
                    <li key={item.label}>
                      <Link
                        className="block rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted"
                        href={item.href}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="border-b border-border bg-white px-6 py-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-white">
                  Saude OK
                </div>
                <div className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
                  1 alerta critico
                </div>
              </div>
              <div className="flex flex-1 items-center justify-end gap-3">
                <input
                  className="h-10 w-full max-w-md rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  placeholder="Buscar chips, conversas, campanhas"
                />
                <button className="h-10 rounded-md border border-border px-4 text-sm">Atualizar</button>
              </div>
            </div>
          </header>

          <main className="flex-1 bg-white px-6 py-6">{children}</main>
        </div>
      </div>
    </div>
  )
}
