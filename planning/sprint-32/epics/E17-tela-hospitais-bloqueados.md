# E17 - Tela de Hospitais Bloqueados

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 5 - Dashboard
**Dependências:** E12 (Hospitais Bloqueados - Backend)
**Estimativa:** 4h

---

## Objetivo

Criar interface no dashboard para gerenciar **hospitais bloqueados** - permitindo bloquear, desbloquear e visualizar histórico.

---

## Contexto

O backend (E12) já implementa:
- Tabela `hospitais_bloqueados`
- Endpoints de bloquear/desbloquear
- Movimentação automática de vagas

Falta a interface visual para gestores.

---

## Tasks

### T1: Criar página de hospitais bloqueados (1h)

**Arquivo:** `dashboard/app/hospitais/bloqueados/page.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/components/ui/use-toast";
import { Plus, Unlock, Calendar, MessageSquare } from "lucide-react";
import { BloquearHospitalDialog } from "@/components/hospitais/bloquear-dialog";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

interface HospitalBloqueado {
  id: string;
  hospital_id: string;
  motivo: string;
  bloqueado_por: string;
  bloqueado_em: string;
  hospitais: {
    nome: string;
    cidade: string;
  };
  _count?: {
    vagas_movidas: number;
  };
}

export default function HospitaisBloqueadosPage() {
  const { toast } = useToast();
  const [bloqueados, setBloqueados] = useState<HospitalBloqueado[]>([]);
  const [loading, setLoading] = useState(true);
  const [bloquearOpen, setBloquearOpen] = useState(false);
  const [desbloquearDialog, setDesbloquearDialog] = useState<HospitalBloqueado | null>(null);

  const carregarBloqueados = async () => {
    try {
      const res = await fetch("/api/hospitais/bloqueados");
      const data = await res.json();
      setBloqueados(data);
    } catch (error) {
      console.error("Erro ao carregar:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarBloqueados();
  }, []);

  const handleDesbloquear = async (hospital: HospitalBloqueado) => {
    try {
      const res = await fetch("/api/hospitais/desbloquear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hospital_id: hospital.hospital_id }),
      });

      if (!res.ok) throw new Error("Erro ao desbloquear");

      const data = await res.json();

      toast({
        title: "Hospital desbloqueado",
        description: `${hospital.hospitais.nome} foi desbloqueado. ${data.vagas_restauradas} vaga(s) restaurada(s).`,
      });

      setDesbloquearDialog(null);
      carregarBloqueados();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Não foi possível desbloquear o hospital.",
      });
    }
  };

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Hospitais Bloqueados</h1>
          <p className="text-muted-foreground">
            Julia não oferece vagas de hospitais bloqueados
          </p>
        </div>

        <Button onClick={() => setBloquearOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Bloquear Hospital
        </Button>
      </div>

      {/* Alerta informativo */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-yellow-800">
          Quando um hospital é bloqueado, suas vagas são movidas para uma tabela
          separada. Julia automaticamente deixa de ver e ofertar essas vagas.
          Ao desbloquear, vagas futuras são restauradas.
        </p>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Hospital</TableHead>
              <TableHead>Cidade</TableHead>
              <TableHead>Motivo</TableHead>
              <TableHead>Bloqueado há</TableHead>
              <TableHead>Vagas afetadas</TableHead>
              <TableHead className="w-[100px]">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  Carregando...
                </TableCell>
              </TableRow>
            ) : bloqueados.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="flex flex-col items-center gap-2">
                    <span className="text-4xl">🏥</span>
                    <span>Nenhum hospital bloqueado</span>
                    <span className="text-sm text-muted-foreground">
                      Todos os hospitais estão ativos para oferta
                    </span>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              bloqueados.map((hospital) => (
                <TableRow key={hospital.id}>
                  <TableCell className="font-medium">
                    {hospital.hospitais.nome}
                  </TableCell>
                  <TableCell>{hospital.hospitais.cidade}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      <span className="max-w-[200px] truncate">
                        {hospital.motivo}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      {formatDistanceToNow(new Date(hospital.bloqueado_em), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {hospital._count?.vagas_movidas || 0} vagas
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setDesbloquearDialog(hospital)}
                    >
                      <Unlock className="h-4 w-4 mr-2" />
                      Desbloquear
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Dialog para bloquear */}
      <BloquearHospitalDialog
        open={bloquearOpen}
        onOpenChange={setBloquearOpen}
        onSuccess={carregarBloqueados}
      />

      {/* Dialog de confirmação para desbloquear */}
      <AlertDialog
        open={!!desbloquearDialog}
        onOpenChange={() => setDesbloquearDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desbloquear hospital?</AlertDialogTitle>
            <AlertDialogDescription>
              {desbloquearDialog && (
                <>
                  Você está prestes a desbloquear{" "}
                  <strong>{desbloquearDialog.hospitais.nome}</strong>.
                  <br />
                  <br />
                  Vagas futuras deste hospital serão restauradas e Julia voltará
                  a ofertá-las normalmente.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => desbloquearDialog && handleDesbloquear(desbloquearDialog)}
            >
              Confirmar desbloqueio
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

---

### T2: Criar dialog de bloqueio (1h)

**Arquivo:** `dashboard/components/hospitais/bloquear-dialog.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/components/ui/use-toast";
import { Check, ChevronsUpDown, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Hospital {
  id: string;
  nome: string;
  cidade: string;
  vagas_abertas?: number;
}

interface BloquearHospitalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function BloquearHospitalDialog({
  open,
  onOpenChange,
  onSuccess,
}: BloquearHospitalDialogProps) {
  const { toast } = useToast();
  const [hospitais, setHospitais] = useState<Hospital[]>([]);
  const [selectedHospital, setSelectedHospital] = useState<Hospital | null>(null);
  const [motivo, setMotivo] = useState("");
  const [comboOpen, setComboOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingHospitais, setLoadingHospitais] = useState(true);

  useEffect(() => {
    async function carregarHospitais() {
      try {
        const res = await fetch("/api/hospitais?excluir_bloqueados=true");
        const data = await res.json();
        setHospitais(data);
      } catch (error) {
        console.error("Erro ao carregar hospitais:", error);
      } finally {
        setLoadingHospitais(false);
      }
    }

    if (open) {
      carregarHospitais();
      setSelectedHospital(null);
      setMotivo("");
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!selectedHospital || !motivo.trim()) return;

    setLoading(true);

    try {
      const res = await fetch("/api/hospitais/bloquear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hospital_id: selectedHospital.id,
          motivo: motivo.trim(),
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Erro ao bloquear");
      }

      const data = await res.json();

      toast({
        title: "Hospital bloqueado",
        description: `${selectedHospital.nome} foi bloqueado. ${data.vagas_movidas} vaga(s) movida(s).`,
      });

      onOpenChange(false);
      onSuccess();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Bloquear Hospital</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Seletor de hospital */}
          <div className="space-y-2">
            <Label>Hospital</Label>
            <Popover open={comboOpen} onOpenChange={setComboOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={comboOpen}
                  className="w-full justify-between"
                >
                  {selectedHospital
                    ? selectedHospital.nome
                    : "Selecione um hospital..."}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-full p-0">
                <Command>
                  <CommandInput placeholder="Buscar hospital..." />
                  <CommandEmpty>
                    {loadingHospitais
                      ? "Carregando..."
                      : "Nenhum hospital encontrado"}
                  </CommandEmpty>
                  <CommandGroup className="max-h-[200px] overflow-auto">
                    {hospitais.map((hospital) => (
                      <CommandItem
                        key={hospital.id}
                        value={hospital.nome}
                        onSelect={() => {
                          setSelectedHospital(hospital);
                          setComboOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedHospital?.id === hospital.id
                              ? "opacity-100"
                              : "opacity-0"
                          )}
                        />
                        <div className="flex flex-col">
                          <span>{hospital.nome}</span>
                          <span className="text-xs text-muted-foreground">
                            {hospital.cidade} • {hospital.vagas_abertas || 0} vagas
                          </span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Motivo */}
          <div className="space-y-2">
            <Label htmlFor="motivo">Motivo do bloqueio *</Label>
            <Textarea
              id="motivo"
              placeholder="Ex: Problemas de pagamento, reforma em andamento..."
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              rows={3}
            />
          </div>

          {/* Alerta de impacto */}
          {selectedHospital && selectedHospital.vagas_abertas && selectedHospital.vagas_abertas > 0 && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Este hospital tem{" "}
                <strong>{selectedHospital.vagas_abertas} vaga(s) aberta(s)</strong>{" "}
                que serão movidas para a tabela de bloqueados.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!selectedHospital || !motivo.trim() || loading}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Bloqueando...
              </>
            ) : (
              "Bloquear Hospital"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

### T3: Criar API routes (1h)

**Arquivo:** `dashboard/app/api/hospitais/bloqueados/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = createRouteHandlerClient({ cookies });

  const { data, error } = await supabase
    .from("hospitais_bloqueados")
    .select(`
      *,
      hospitais (nome, cidade)
    `)
    .eq("status", "bloqueado")
    .order("bloqueado_em", { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Contar vagas movidas para cada bloqueio
  const bloqueadosComContagem = await Promise.all(
    (data || []).map(async (bloqueio) => {
      const { count } = await supabase
        .from("vagas_hospitais_bloqueados")
        .select("id", { count: "exact", head: true })
        .eq("bloqueio_id", bloqueio.id);

      return {
        ...bloqueio,
        _count: { vagas_movidas: count || 0 },
      };
    })
  );

  return NextResponse.json(bloqueadosComContagem);
}
```

**Arquivo:** `dashboard/app/api/hospitais/bloquear/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies });

  // Verificar autenticação
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const body = await request.json();
  const { hospital_id, motivo } = body;

  if (!hospital_id || !motivo) {
    return NextResponse.json(
      { error: "hospital_id e motivo são obrigatórios" },
      { status: 400 }
    );
  }

  // Verificar se hospital existe
  const { data: hospital, error: hospitalError } = await supabase
    .from("hospitais")
    .select("id, nome")
    .eq("id", hospital_id)
    .single();

  if (hospitalError || !hospital) {
    return NextResponse.json(
      { error: "Hospital não encontrado" },
      { status: 404 }
    );
  }

  // Verificar se já está bloqueado
  const { data: existing } = await supabase
    .from("hospitais_bloqueados")
    .select("id")
    .eq("hospital_id", hospital_id)
    .eq("status", "bloqueado")
    .single();

  if (existing) {
    return NextResponse.json(
      { error: "Hospital já está bloqueado" },
      { status: 400 }
    );
  }

  // Criar bloqueio
  const { data: bloqueio, error: bloqueioError } = await supabase
    .from("hospitais_bloqueados")
    .insert({
      hospital_id,
      motivo,
      bloqueado_por: user.id,
      status: "bloqueado",
    })
    .select()
    .single();

  if (bloqueioError) {
    return NextResponse.json(
      { error: bloqueioError.message },
      { status: 500 }
    );
  }

  // Mover vagas
  const { data: vagas } = await supabase
    .from("vagas")
    .select("*")
    .eq("hospital_id", hospital_id);

  let vagasMovidas = 0;

  if (vagas && vagas.length > 0) {
    for (const vaga of vagas) {
      await supabase.from("vagas_hospitais_bloqueados").insert({
        ...vaga,
        movido_em: new Date().toISOString(),
        movido_por: user.id,
        bloqueio_id: bloqueio.id,
      });
    }

    await supabase.from("vagas").delete().eq("hospital_id", hospital_id);

    vagasMovidas = vagas.length;
  }

  return NextResponse.json({
    bloqueio_id: bloqueio.id,
    hospital_id,
    hospital_nome: hospital.nome,
    motivo,
    vagas_movidas: vagasMovidas,
  });
}
```

**Arquivo:** `dashboard/app/api/hospitais/desbloquear/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const body = await request.json();
  const { hospital_id } = body;

  // Buscar bloqueio ativo
  const { data: bloqueio, error: bloqueioError } = await supabase
    .from("hospitais_bloqueados")
    .select("id")
    .eq("hospital_id", hospital_id)
    .eq("status", "bloqueado")
    .single();

  if (bloqueioError || !bloqueio) {
    return NextResponse.json(
      { error: "Hospital não está bloqueado" },
      { status: 404 }
    );
  }

  // Buscar vagas a restaurar (apenas futuras)
  const hoje = new Date().toISOString().split("T")[0];

  const { data: vagasBloqueadas } = await supabase
    .from("vagas_hospitais_bloqueados")
    .select("*")
    .eq("bloqueio_id", bloqueio.id)
    .gte("data", hoje);

  let vagasRestauradas = 0;

  if (vagasBloqueadas && vagasBloqueadas.length > 0) {
    for (const vaga of vagasBloqueadas) {
      // Remove campos de metadados
      const { movido_em, movido_por, bloqueio_id, ...vagaOriginal } = vaga;

      await supabase.from("vagas").insert({
        ...vagaOriginal,
        updated_at: new Date().toISOString(),
      });
    }

    await supabase
      .from("vagas_hospitais_bloqueados")
      .delete()
      .eq("bloqueio_id", bloqueio.id);

    vagasRestauradas = vagasBloqueadas.length;
  }

  // Atualizar status do bloqueio
  await supabase
    .from("hospitais_bloqueados")
    .update({
      status: "desbloqueado",
      desbloqueado_em: new Date().toISOString(),
      desbloqueado_por: user.id,
    })
    .eq("id", bloqueio.id);

  return NextResponse.json({
    hospital_id,
    vagas_restauradas: vagasRestauradas,
  });
}
```

---

### T4: Adicionar ao menu de navegação (30min)

**Arquivo:** `dashboard/components/layout/sidebar.tsx` (modificar)

```tsx
// Adicionar item ao menu
{
  title: "Hospitais",
  icon: Building2,
  items: [
    { title: "Todos", href: "/hospitais" },
    { title: "Bloqueados", href: "/hospitais/bloqueados" },
  ],
}
```

---

### T5: Criar testes (30min)

**Arquivo:** `dashboard/__tests__/hospitais/bloqueados.test.tsx`

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import HospitaisBloqueadosPage from "@/app/hospitais/bloqueados/page";
import { BloquearHospitalDialog } from "@/components/hospitais/bloquear-dialog";

// Mock fetch
global.fetch = vi.fn();

describe("HospitaisBloqueadosPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no hospitals are blocked", async () => {
    (fetch as any).mockResolvedValueOnce({
      json: () => Promise.resolve([]),
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Nenhum hospital bloqueado")).toBeInTheDocument();
    });
  });

  it("renders blocked hospitals list", async () => {
    const mockData = [
      {
        id: "1",
        hospital_id: "h1",
        motivo: "Reforma",
        bloqueado_em: "2026-01-10T10:00:00Z",
        hospitais: { nome: "Hospital X", cidade: "São Paulo" },
        _count: { vagas_movidas: 5 },
      },
    ];

    (fetch as any).mockResolvedValueOnce({
      json: () => Promise.resolve(mockData),
    });

    render(<HospitaisBloqueadosPage />);

    await waitFor(() => {
      expect(screen.getByText("Hospital X")).toBeInTheDocument();
      expect(screen.getByText("Reforma")).toBeInTheDocument();
      expect(screen.getByText("5 vagas")).toBeInTheDocument();
    });
  });
});

describe("BloquearHospitalDialog", () => {
  it("requires hospital and motivo to submit", () => {
    render(
      <BloquearHospitalDialog
        open={true}
        onOpenChange={vi.fn()}
        onSuccess={vi.fn()}
      />
    );

    const submitButton = screen.getByText("Bloquear Hospital");
    expect(submitButton).toBeDisabled();
  });
});
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Listagem de hospitais bloqueados
- [ ] Dialog para bloquear com seletor de hospital
- [ ] Motivo obrigatório
- [ ] Confirmação antes de desbloquear
- [ ] Contagem de vagas afetadas
- [ ] Menu de navegação atualizado

### UI/UX
- [ ] Empty state quando não há bloqueados
- [ ] Alerta explicativo sobre funcionamento
- [ ] Loading states em todas as operações
- [ ] Toast de sucesso/erro

### API
- [ ] GET /api/hospitais/bloqueados
- [ ] POST /api/hospitais/bloquear
- [ ] POST /api/hospitais/desbloquear

### Testes
- [ ] Testes de listagem
- [ ] Testes de validação do form
- [ ] Testes de mock API

### Verificação Manual

1. **Bloquear hospital:**
   - Clicar "Bloquear Hospital"
   - Selecionar hospital
   - Digitar motivo
   - Verificar toast de sucesso
   - Verificar que aparece na lista

2. **Desbloquear hospital:**
   - Clicar "Desbloquear"
   - Confirmar no dialog
   - Verificar toast com vagas restauradas
   - Verificar que sumiu da lista

3. **Verificar impacto:**
   - Bloquear hospital com vagas
   - Verificar no banco que vagas sumiram de `vagas`
   - Verificar que estão em `vagas_hospitais_bloqueados`

---

## Notas para Dev

1. **Autenticação:** Todas as rotas requerem usuário autenticado
2. **Permissões:** Considerar RBAC (apenas gestores podem bloquear)
3. **Auditoria:** Log de quem bloqueou/desbloqueou
4. **Mobile:** Testar em telas pequenas

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Bloqueios via dashboard | > 80% (vs. Slack) |
| Erros de operação | < 1% |
| Tempo de bloqueio | < 10s |
