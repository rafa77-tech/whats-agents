# E19 - Tela do Canal de Ajuda

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 5 - Dashboard
**Dependências:** E08 (Canal de Ajuda - Backend)
**Estimativa:** 4h

---

## Objetivo

Criar interface no dashboard para gestores visualizarem e responderem **pedidos de ajuda** da Julia - perguntas que ela não soube responder.

---

## Contexto

O backend (E08) implementa:
- Tabela `pedidos_ajuda`
- Integração com Slack para notificações
- Timeout de 5 minutos
- Lembretes automáticos

Esta tela é alternativa ao Slack para gestores que preferem interface visual.

---

## Tasks

### T1: Criar página de pedidos de ajuda (1.5h)

**Arquivo:** `dashboard/app/ajuda/page.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import {
  HelpCircle,
  Clock,
  CheckCircle2,
  MessageSquare,
  User,
  Building2,
  Send,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface PedidoAjuda {
  id: string;
  conversa_id: string;
  cliente_id: string;
  hospital_id?: string;
  pergunta_original: string;
  contexto: string;
  status: "pendente" | "respondido" | "timeout" | "cancelado";
  resposta?: string;
  respondido_por?: string;
  respondido_em?: string;
  criado_em: string;
  // Joins
  clientes?: { nome: string; telefone: string };
  hospitais?: { nome: string };
}

const statusConfig = {
  pendente: {
    label: "Pendente",
    color: "bg-yellow-100 text-yellow-800",
    icon: Clock,
  },
  respondido: {
    label: "Respondido",
    color: "bg-green-100 text-green-800",
    icon: CheckCircle2,
  },
  timeout: {
    label: "Timeout",
    color: "bg-orange-100 text-orange-800",
    icon: Clock,
  },
  cancelado: {
    label: "Cancelado",
    color: "bg-gray-100 text-gray-800",
    icon: HelpCircle,
  },
};

export default function CanalAjudaPage() {
  const { toast } = useToast();
  const [pedidos, setPedidos] = useState<PedidoAjuda[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"pendentes" | "todos">("pendentes");
  const [respondendo, setRespondendo] = useState<string | null>(null);
  const [resposta, setResposta] = useState("");
  const [enviando, setEnviando] = useState(false);

  const carregarPedidos = async () => {
    try {
      const status = tab === "pendentes" ? "pendente,timeout" : "";
      const res = await fetch(`/api/ajuda?status=${status}`);
      const data = await res.json();
      setPedidos(data);
    } catch (error) {
      console.error("Erro ao carregar:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    carregarPedidos();
  }, [tab]);

  // Auto-refresh a cada 30 segundos para pedidos pendentes
  useEffect(() => {
    if (tab === "pendentes") {
      const interval = setInterval(carregarPedidos, 30000);
      return () => clearInterval(interval);
    }
  }, [tab]);

  const handleResponder = async (pedidoId: string) => {
    if (!resposta.trim()) return;

    setEnviando(true);

    try {
      const res = await fetch(`/api/ajuda/${pedidoId}/responder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resposta: resposta.trim() }),
      });

      if (!res.ok) throw new Error("Erro ao responder");

      toast({
        title: "Resposta enviada",
        description: "Julia retomará a conversa com o médico.",
      });

      setRespondendo(null);
      setResposta("");
      carregarPedidos();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Não foi possível enviar a resposta.",
      });
    } finally {
      setEnviando(false);
    }
  };

  const pendentesCount = pedidos.filter(
    (p) => p.status === "pendente" || p.status === "timeout"
  ).length;

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Canal de Ajuda</h1>
          <p className="text-muted-foreground">
            Perguntas que Julia não soube responder
          </p>
        </div>

        <Button variant="outline" onClick={carregarPedidos} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      {/* Alerta de pendentes */}
      {tab === "pendentes" && pendentesCount > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-yellow-600" />
            <span className="font-medium text-yellow-800">
              {pendentesCount} pedido(s) aguardando resposta
            </span>
          </div>
          <p className="text-sm text-yellow-700 mt-1">
            Médicos estão esperando. Responda para Julia continuar a conversa.
          </p>
        </div>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="pendentes">
            Pendentes
            {pendentesCount > 0 && (
              <Badge className="ml-2 bg-yellow-500">{pendentesCount}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="todos">Todos</TabsTrigger>
        </TabsList>

        <TabsContent value="pendentes" className="mt-4 space-y-4">
          {loading ? (
            <div className="text-center py-8">Carregando...</div>
          ) : pedidos.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle2 className="h-12 w-12 mx-auto text-green-500 mb-4" />
              <p className="text-lg font-medium">Tudo em dia!</p>
              <p className="text-muted-foreground">
                Nenhum pedido pendente no momento.
              </p>
            </div>
          ) : (
            pedidos.map((pedido) => (
              <PedidoCard
                key={pedido.id}
                pedido={pedido}
                isExpanded={respondendo === pedido.id}
                onToggle={() => {
                  setRespondendo(respondendo === pedido.id ? null : pedido.id);
                  setResposta("");
                }}
                resposta={resposta}
                onRespostaChange={setResposta}
                onResponder={() => handleResponder(pedido.id)}
                enviando={enviando}
              />
            ))
          )}
        </TabsContent>

        <TabsContent value="todos" className="mt-4 space-y-4">
          {loading ? (
            <div className="text-center py-8">Carregando...</div>
          ) : (
            pedidos.map((pedido) => (
              <PedidoCard
                key={pedido.id}
                pedido={pedido}
                isExpanded={false}
                onToggle={() => {}}
                resposta=""
                onRespostaChange={() => {}}
                onResponder={() => {}}
                enviando={false}
                readOnly
              />
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

interface PedidoCardProps {
  pedido: PedidoAjuda;
  isExpanded: boolean;
  onToggle: () => void;
  resposta: string;
  onRespostaChange: (value: string) => void;
  onResponder: () => void;
  enviando: boolean;
  readOnly?: boolean;
}

function PedidoCard({
  pedido,
  isExpanded,
  onToggle,
  resposta,
  onRespostaChange,
  onResponder,
  enviando,
  readOnly,
}: PedidoCardProps) {
  const status = statusConfig[pedido.status];
  const StatusIcon = status.icon;

  const isPending = pedido.status === "pendente" || pedido.status === "timeout";

  return (
    <Card className={isPending ? "border-yellow-200" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <User className="h-8 w-8 text-muted-foreground" />
            <div>
              <CardTitle className="text-lg">
                {pedido.clientes?.nome || "Médico"}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {pedido.clientes?.telefone}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge className={status.color}>
              <StatusIcon className="h-3 w-3 mr-1" />
              {status.label}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {formatDistanceToNow(new Date(pedido.criado_em), {
                addSuffix: true,
                locale: ptBR,
              })}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Hospital */}
        {pedido.hospitais && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Building2 className="h-4 w-4" />
            <span>Conversa sobre: {pedido.hospitais.nome}</span>
          </div>
        )}

        {/* Pergunta */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <MessageSquare className="h-4 w-4" />
            <span>Pergunta do médico:</span>
          </div>
          <p className="font-medium">{pedido.pergunta_original}</p>
        </div>

        {/* Contexto */}
        {pedido.contexto && (
          <div className="text-sm">
            <span className="text-muted-foreground">Contexto: </span>
            <span>{pedido.contexto}</span>
          </div>
        )}

        {/* Resposta (se já respondido) */}
        {pedido.resposta && (
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center gap-2 text-sm text-green-700 mb-2">
              <CheckCircle2 className="h-4 w-4" />
              <span>
                Respondido em{" "}
                {format(new Date(pedido.respondido_em!), "dd/MM HH:mm")}
              </span>
            </div>
            <p>{pedido.resposta}</p>
          </div>
        )}

        {/* Área de resposta (se pendente) */}
        {isPending && !readOnly && (
          <>
            {isExpanded ? (
              <div className="space-y-3">
                <Textarea
                  placeholder="Digite sua resposta para Julia repassar ao médico..."
                  value={resposta}
                  onChange={(e) => onRespostaChange(e.target.value)}
                  rows={3}
                />
                <div className="flex gap-2">
                  <Button
                    onClick={onResponder}
                    disabled={!resposta.trim() || enviando}
                  >
                    {enviando ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Enviar Resposta
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={onToggle}>
                    Cancelar
                  </Button>
                </div>
              </div>
            ) : (
              <Button onClick={onToggle}>Responder</Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

---

### T2: Criar API routes (1h)

**Arquivo:** `dashboard/app/api/ajuda/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies });
  const status = request.nextUrl.searchParams.get("status");

  let query = supabase
    .from("pedidos_ajuda")
    .select(`
      *,
      clientes (nome, telefone),
      hospitais (nome)
    `)
    .order("criado_em", { ascending: false })
    .limit(50);

  if (status) {
    const statusArray = status.split(",");
    query = query.in("status", statusArray);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}
```

**Arquivo:** `dashboard/app/api/ajuda/[id]/responder/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const supabase = createRouteHandlerClient({ cookies });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const body = await request.json();
  const { resposta } = body;

  if (!resposta?.trim()) {
    return NextResponse.json(
      { error: "Resposta é obrigatória" },
      { status: 400 }
    );
  }

  // Buscar pedido
  const { data: pedido, error: pedidoError } = await supabase
    .from("pedidos_ajuda")
    .select("*")
    .eq("id", params.id)
    .single();

  if (pedidoError || !pedido) {
    return NextResponse.json(
      { error: "Pedido não encontrado" },
      { status: 404 }
    );
  }

  // Atualizar pedido
  const { data, error } = await supabase
    .from("pedidos_ajuda")
    .update({
      status: "respondido",
      resposta: resposta.trim(),
      respondido_por: user.id,
      respondido_em: new Date().toISOString(),
    })
    .eq("id", params.id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Retomar conversa (chamar backend Python)
  try {
    await fetch(`${process.env.API_URL}/conversas/${pedido.conversa_id}/retomar`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.API_SECRET}`,
      },
      body: JSON.stringify({
        resposta_gestor: resposta.trim(),
        pedido_ajuda_id: params.id,
      }),
    });
  } catch (error) {
    console.error("Erro ao retomar conversa:", error);
    // Não falha a request - pedido já foi marcado como respondido
  }

  return NextResponse.json(data);
}
```

---

### T3: Adicionar notificação visual (30min)

**Arquivo:** `dashboard/components/layout/header.tsx` (modificar)

```tsx
// Adicionar componente de notificação
import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export function NotificacaoAjuda() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    async function verificar() {
      try {
        const res = await fetch("/api/ajuda?status=pendente,timeout");
        const data = await res.json();
        setCount(data.length);
      } catch (error) {
        console.error(error);
      }
    }

    verificar();
    const interval = setInterval(verificar, 60000); // A cada minuto

    return () => clearInterval(interval);
  }, []);

  return (
    <Link href="/ajuda" className="relative">
      <Bell className="h-5 w-5" />
      {count > 0 && (
        <Badge className="absolute -top-2 -right-2 h-5 w-5 p-0 flex items-center justify-center bg-red-500">
          {count}
        </Badge>
      )}
    </Link>
  );
}
```

---

### T4: Criar testes (30min)

**Arquivo:** `dashboard/__tests__/ajuda/canal-ajuda.test.tsx`

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import CanalAjudaPage from "@/app/ajuda/page";

global.fetch = vi.fn();

describe("CanalAjudaPage", () => {
  it("shows empty state when no pending requests", async () => {
    (fetch as any).mockResolvedValueOnce({
      json: () => Promise.resolve([]),
    });

    render(<CanalAjudaPage />);

    await waitFor(() => {
      expect(screen.getByText("Tudo em dia!")).toBeInTheDocument();
    });
  });

  it("renders pending requests", async () => {
    const mockData = [
      {
        id: "1",
        pergunta_original: "Tem estacionamento?",
        status: "pendente",
        criado_em: new Date().toISOString(),
        clientes: { nome: "Dr. Carlos", telefone: "11999999999" },
        hospitais: { nome: "Hospital X" },
      },
    ];

    (fetch as any).mockResolvedValueOnce({
      json: () => Promise.resolve(mockData),
    });

    render(<CanalAjudaPage />);

    await waitFor(() => {
      expect(screen.getByText("Dr. Carlos")).toBeInTheDocument();
      expect(screen.getByText("Tem estacionamento?")).toBeInTheDocument();
    });
  });

  it("shows response form when clicking Responder", async () => {
    const mockData = [
      {
        id: "1",
        pergunta_original: "Tem estacionamento?",
        status: "pendente",
        criado_em: new Date().toISOString(),
        clientes: { nome: "Dr. Carlos", telefone: "11999999999" },
      },
    ];

    (fetch as any).mockResolvedValueOnce({
      json: () => Promise.resolve(mockData),
    });

    render(<CanalAjudaPage />);

    await waitFor(() => {
      fireEvent.click(screen.getByText("Responder"));
    });

    expect(screen.getByPlaceholderText(/Digite sua resposta/)).toBeInTheDocument();
  });
});
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Listagem de pedidos pendentes
- [ ] Badge com contagem de pendentes
- [ ] Formulário de resposta inline
- [ ] Histórico de todos os pedidos
- [ ] Auto-refresh a cada 30 segundos
- [ ] Notificação no header

### UI/UX
- [ ] Cards com informações claras
- [ ] Status visual (cores e ícones)
- [ ] Empty state quando tudo ok
- [ ] Loading states

### Testes
- [ ] Testes de listagem
- [ ] Testes de resposta
- [ ] Testes de empty state

### Verificação Manual

1. **Simular pedido pendente:**
   - Criar pedido via API ou Slack
   - Verificar que aparece na tela
   - Badge no header mostra 1

2. **Responder pedido:**
   - Clicar "Responder"
   - Digitar resposta
   - Enviar e verificar que some da lista

3. **Verificar retomada:**
   - Após responder, Julia deve retomar conversa
   - Médico recebe resposta

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Respostas via dashboard | > 30% |
| Tempo médio de resposta | < 15 min |
