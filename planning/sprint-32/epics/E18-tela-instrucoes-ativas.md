# E18 - Tela de Instruções Ativas (Diretrizes Contextuais)

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 5 - Dashboard
**Dependências:** E10 (Diretrizes Contextuais - Backend)
**Estimativa:** 4h

---

## Objetivo

Criar interface para visualizar e gerenciar **diretrizes contextuais** (instruções ativas) - margens de negociação e regras específicas por vaga/médico.

---

## Contexto

O backend (E10) implementa:
- Tabela `diretrizes_contextuais`
- Escopos: vaga, médico, hospital, especialidade, global
- Expiração automática
- Endpoints CRUD

Falta interface visual para gestores verem e gerenciarem instruções ativas.

---

## Tasks

### T1: Criar página de instruções ativas (1.5h)

**Arquivo:** `dashboard/app/instrucoes/page.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import {
  Plus,
  MoreHorizontal,
  Trash2,
  Calendar,
  User,
  Building2,
  Briefcase,
  Globe,
} from "lucide-react";
import { NovaInstrucaoDialog } from "@/components/instrucoes/nova-instrucao-dialog";
import { formatDistanceToNow, format } from "date-fns";
import { ptBR } from "date-fns/locale";

type TipoDiretriz = "margem_negociacao" | "regra_especial" | "info_adicional";
type Escopo = "vaga" | "medico" | "hospital" | "especialidade" | "global";

interface Diretriz {
  id: string;
  tipo: TipoDiretriz;
  escopo: Escopo;
  vaga_id?: string;
  cliente_id?: string;
  hospital_id?: string;
  especialidade_id?: string;
  conteudo: {
    valor_maximo?: number;
    percentual_maximo?: number;
    regra?: string;
    info?: string;
  };
  criado_por: string;
  criado_em: string;
  expira_em?: string;
  status: "ativa" | "expirada" | "cancelada";
  // Joins
  vagas?: { data: string; hospital_id: string };
  clientes?: { nome: string; telefone: string };
  hospitais?: { nome: string };
  especialidades?: { nome: string };
}

const escopoIcons: Record<Escopo, React.ReactNode> = {
  vaga: <Calendar className="h-4 w-4" />,
  medico: <User className="h-4 w-4" />,
  hospital: <Building2 className="h-4 w-4" />,
  especialidade: <Briefcase className="h-4 w-4" />,
  global: <Globe className="h-4 w-4" />,
};

const escopoLabels: Record<Escopo, string> = {
  vaga: "Vaga",
  medico: "Médico",
  hospital: "Hospital",
  especialidade: "Especialidade",
  global: "Global",
};

const tipoLabels: Record<TipoDiretriz, string> = {
  margem_negociacao: "Margem de Negociação",
  regra_especial: "Regra Especial",
  info_adicional: "Informação Adicional",
};

export default function InstrucoesPage() {
  const { toast } = useToast();
  const [diretrizes, setDiretrizes] = useState<Diretriz[]>([]);
  const [loading, setLoading] = useState(true);
  const [novaOpen, setNovaOpen] = useState(false);
  const [cancelarDialog, setCancelarDialog] = useState<Diretriz | null>(null);
  const [tab, setTab] = useState<"ativas" | "historico">("ativas");

  const carregarDiretrizes = async () => {
    try {
      const status = tab === "ativas" ? "ativa" : "expirada,cancelada";
      const res = await fetch(`/api/diretrizes?status=${status}`);
      const data = await res.json();
      setDiretrizes(data);
    } catch (error) {
      console.error("Erro ao carregar:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    carregarDiretrizes();
  }, [tab]);

  const handleCancelar = async (diretriz: Diretriz) => {
    try {
      const res = await fetch(`/api/diretrizes/${diretriz.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "cancelada" }),
      });

      if (!res.ok) throw new Error("Erro ao cancelar");

      toast({
        title: "Instrução cancelada",
        description: "A diretriz foi desativada.",
      });

      setCancelarDialog(null);
      carregarDiretrizes();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Não foi possível cancelar a instrução.",
      });
    }
  };

  const getEscopoLabel = (diretriz: Diretriz): string => {
    switch (diretriz.escopo) {
      case "vaga":
        return diretriz.vagas
          ? `Vaga ${format(new Date(diretriz.vagas.data), "dd/MM")}`
          : "Vaga";
      case "medico":
        return diretriz.clientes?.nome || "Médico";
      case "hospital":
        return diretriz.hospitais?.nome || "Hospital";
      case "especialidade":
        return diretriz.especialidades?.nome || "Especialidade";
      case "global":
        return "Todas as conversas";
      default:
        return "";
    }
  };

  const getConteudoLabel = (diretriz: Diretriz): string => {
    const { conteudo, tipo } = diretriz;

    if (tipo === "margem_negociacao") {
      if (conteudo.valor_maximo) {
        return `Até R$ ${conteudo.valor_maximo.toLocaleString("pt-BR")}`;
      }
      if (conteudo.percentual_maximo) {
        return `Até ${conteudo.percentual_maximo}% acima`;
      }
    }

    if (tipo === "regra_especial") {
      return conteudo.regra || "";
    }

    if (tipo === "info_adicional") {
      return conteudo.info || "";
    }

    return JSON.stringify(conteudo);
  };

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Instruções Ativas</h1>
          <p className="text-muted-foreground">
            Diretrizes contextuais que Julia segue nas conversas
          </p>
        </div>

        <Button onClick={() => setNovaOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Instrução
        </Button>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="ativas">Ativas</TabsTrigger>
          <TabsTrigger value="historico">Histórico</TabsTrigger>
        </TabsList>

        <TabsContent value="ativas" className="mt-4">
          <DiretrizesTable
            diretrizes={diretrizes}
            loading={loading}
            onCancelar={setCancelarDialog}
            showActions
          />
        </TabsContent>

        <TabsContent value="historico" className="mt-4">
          <DiretrizesTable
            diretrizes={diretrizes}
            loading={loading}
            onCancelar={() => {}}
            showActions={false}
          />
        </TabsContent>
      </Tabs>

      {/* Dialog nova instrução */}
      <NovaInstrucaoDialog
        open={novaOpen}
        onOpenChange={setNovaOpen}
        onSuccess={carregarDiretrizes}
      />

      {/* Dialog cancelar */}
      <AlertDialog
        open={!!cancelarDialog}
        onOpenChange={() => setCancelarDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar instrução?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta instrução será desativada e Julia deixará de segui-la.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => cancelarDialog && handleCancelar(cancelarDialog)}
            >
              Confirmar cancelamento
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

interface DiretrizesTableProps {
  diretrizes: Diretriz[];
  loading: boolean;
  onCancelar: (d: Diretriz) => void;
  showActions: boolean;
}

function DiretrizesTable({
  diretrizes,
  loading,
  onCancelar,
  showActions,
}: DiretrizesTableProps) {
  return (
    <div className="border rounded-lg">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tipo</TableHead>
            <TableHead>Escopo</TableHead>
            <TableHead>Conteúdo</TableHead>
            <TableHead>Criada</TableHead>
            <TableHead>Expira</TableHead>
            {showActions && <TableHead className="w-[50px]"></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-8">
                Carregando...
              </TableCell>
            </TableRow>
          ) : diretrizes.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-8">
                Nenhuma instrução encontrada
              </TableCell>
            </TableRow>
          ) : (
            diretrizes.map((diretriz) => (
              <TableRow key={diretriz.id}>
                <TableCell>
                  <Badge variant="outline">
                    {tipoLabels[diretriz.tipo]}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {escopoIcons[diretriz.escopo]}
                    <span>{getEscopoLabel(diretriz)}</span>
                  </div>
                </TableCell>
                <TableCell className="max-w-[250px] truncate">
                  {getConteudoLabel(diretriz)}
                </TableCell>
                <TableCell>
                  {formatDistanceToNow(new Date(diretriz.criado_em), {
                    addSuffix: true,
                    locale: ptBR,
                  })}
                </TableCell>
                <TableCell>
                  {diretriz.expira_em ? (
                    <span
                      className={
                        new Date(diretriz.expira_em) < new Date()
                          ? "text-red-500"
                          : ""
                      }
                    >
                      {format(new Date(diretriz.expira_em), "dd/MM HH:mm")}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">Não expira</span>
                  )}
                </TableCell>
                {showActions && (
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        <DropdownMenuItem
                          className="text-red-600"
                          onClick={() => onCancelar(diretriz)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Cancelar
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                )}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
```

---

### T2: Criar dialog de nova instrução (1.5h)

**Arquivo:** `dashboard/components/instrucoes/nova-instrucao-dialog.tsx`

```tsx
"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useToast } from "@/components/ui/use-toast";
import { Loader2 } from "lucide-react";
import { SeletorVaga } from "./seletor-vaga";
import { SeletorMedico } from "./seletor-medico";
import { SeletorHospital } from "./seletor-hospital";

type TipoDiretriz = "margem_negociacao" | "regra_especial" | "info_adicional";
type Escopo = "vaga" | "medico" | "hospital" | "especialidade" | "global";

interface NovaInstrucaoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function NovaInstrucaoDialog({
  open,
  onOpenChange,
  onSuccess,
}: NovaInstrucaoDialogProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [tipo, setTipo] = useState<TipoDiretriz>("margem_negociacao");
  const [escopo, setEscopo] = useState<Escopo>("vaga");

  // Referências do escopo
  const [vagaId, setVagaId] = useState<string>("");
  const [clienteId, setClienteId] = useState<string>("");
  const [hospitalId, setHospitalId] = useState<string>("");
  const [especialidadeId, setEspecialidadeId] = useState<string>("");

  // Conteúdo
  const [valorMaximo, setValorMaximo] = useState<string>("");
  const [percentualMaximo, setPercentualMaximo] = useState<string>("");
  const [regra, setRegra] = useState<string>("");
  const [info, setInfo] = useState<string>("");

  // Expiração
  const [expiraEm, setExpiraEm] = useState<string>("");

  const resetForm = () => {
    setTipo("margem_negociacao");
    setEscopo("vaga");
    setVagaId("");
    setClienteId("");
    setHospitalId("");
    setEspecialidadeId("");
    setValorMaximo("");
    setPercentualMaximo("");
    setRegra("");
    setInfo("");
    setExpiraEm("");
  };

  const handleSubmit = async () => {
    setLoading(true);

    try {
      const conteudo: Record<string, unknown> = {};

      if (tipo === "margem_negociacao") {
        if (valorMaximo) conteudo.valor_maximo = Number(valorMaximo);
        if (percentualMaximo) conteudo.percentual_maximo = Number(percentualMaximo);
      } else if (tipo === "regra_especial") {
        conteudo.regra = regra;
      } else if (tipo === "info_adicional") {
        conteudo.info = info;
      }

      const payload: Record<string, unknown> = {
        tipo,
        escopo,
        conteudo,
      };

      if (escopo === "vaga") payload.vaga_id = vagaId;
      if (escopo === "medico") payload.cliente_id = clienteId;
      if (escopo === "hospital") payload.hospital_id = hospitalId;
      if (escopo === "especialidade") payload.especialidade_id = especialidadeId;
      if (expiraEm) payload.expira_em = new Date(expiraEm).toISOString();

      const res = await fetch("/api/diretrizes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Erro ao criar instrução");

      toast({
        title: "Instrução criada",
        description: "Julia seguirá esta diretriz a partir de agora.",
      });

      resetForm();
      onOpenChange(false);
      onSuccess();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Não foi possível criar a instrução.",
      });
    } finally {
      setLoading(false);
    }
  };

  const canSubmit = () => {
    // Validar escopo
    if (escopo === "vaga" && !vagaId) return false;
    if (escopo === "medico" && !clienteId) return false;
    if (escopo === "hospital" && !hospitalId) return false;
    if (escopo === "especialidade" && !especialidadeId) return false;

    // Validar conteúdo
    if (tipo === "margem_negociacao" && !valorMaximo && !percentualMaximo)
      return false;
    if (tipo === "regra_especial" && !regra.trim()) return false;
    if (tipo === "info_adicional" && !info.trim()) return false;

    return true;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nova Instrução</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Tipo de instrução */}
          <div className="space-y-2">
            <Label>Tipo de instrução</Label>
            <RadioGroup value={tipo} onValueChange={(v) => setTipo(v as TipoDiretriz)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="margem_negociacao" id="margem" />
                <Label htmlFor="margem" className="font-normal">
                  Margem de Negociação
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="regra_especial" id="regra" />
                <Label htmlFor="regra" className="font-normal">
                  Regra Especial
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="info_adicional" id="info" />
                <Label htmlFor="info" className="font-normal">
                  Informação Adicional
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Escopo */}
          <div className="space-y-2">
            <Label>Aplica-se a</Label>
            <Select value={escopo} onValueChange={(v) => setEscopo(v as Escopo)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="vaga">Vaga específica</SelectItem>
                <SelectItem value="medico">Médico específico</SelectItem>
                <SelectItem value="hospital">Hospital</SelectItem>
                <SelectItem value="especialidade">Especialidade</SelectItem>
                <SelectItem value="global">Todas as conversas</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Seletor baseado no escopo */}
          {escopo === "vaga" && (
            <SeletorVaga value={vagaId} onChange={setVagaId} />
          )}
          {escopo === "medico" && (
            <SeletorMedico value={clienteId} onChange={setClienteId} />
          )}
          {escopo === "hospital" && (
            <SeletorHospital value={hospitalId} onChange={setHospitalId} />
          )}

          {/* Conteúdo baseado no tipo */}
          {tipo === "margem_negociacao" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Valor máximo (R$)</Label>
                <Input
                  type="number"
                  placeholder="Ex: 3000"
                  value={valorMaximo}
                  onChange={(e) => setValorMaximo(e.target.value)}
                />
              </div>
              <div className="text-center text-muted-foreground">ou</div>
              <div className="space-y-2">
                <Label>Percentual máximo acima do base (%)</Label>
                <Input
                  type="number"
                  placeholder="Ex: 15"
                  value={percentualMaximo}
                  onChange={(e) => setPercentualMaximo(e.target.value)}
                />
              </div>
            </div>
          )}

          {tipo === "regra_especial" && (
            <div className="space-y-2">
              <Label>Regra</Label>
              <Textarea
                placeholder="Ex: Pode flexibilizar horário de entrada em até 1 hora"
                value={regra}
                onChange={(e) => setRegra(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {tipo === "info_adicional" && (
            <div className="space-y-2">
              <Label>Informação</Label>
              <Textarea
                placeholder="Ex: Este médico prefere plantões noturnos"
                value={info}
                onChange={(e) => setInfo(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {/* Expiração */}
          <div className="space-y-2">
            <Label>Expira em (opcional)</Label>
            <Input
              type="datetime-local"
              value={expiraEm}
              onChange={(e) => setExpiraEm(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Deixe vazio para não expirar automaticamente
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit() || loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Criando...
              </>
            ) : (
              "Criar Instrução"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

### T3: Criar componentes de seletores (30min)

**Arquivo:** `dashboard/components/instrucoes/seletor-vaga.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { format } from "date-fns";

interface Vaga {
  id: string;
  data: string;
  hospital_id: string;
  hospitais: { nome: string };
  especialidades: { nome: string };
  valor: number;
}

interface SeletorVagaProps {
  value: string;
  onChange: (id: string) => void;
}

export function SeletorVaga({ value, onChange }: SeletorVagaProps) {
  const [vagas, setVagas] = useState<Vaga[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function carregar() {
      try {
        const res = await fetch("/api/vagas?status=aberta&limit=50");
        const data = await res.json();
        setVagas(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  return (
    <div className="space-y-2">
      <Label>Vaga</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder={loading ? "Carregando..." : "Selecione a vaga"} />
        </SelectTrigger>
        <SelectContent>
          {vagas.map((vaga) => (
            <SelectItem key={vaga.id} value={vaga.id}>
              {format(new Date(vaga.data), "dd/MM")} - {vaga.hospitais.nome} (
              {vaga.especialidades.nome}) - R$ {vaga.valor}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

**Arquivo:** `dashboard/components/instrucoes/seletor-medico.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
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
import { Button } from "@/components/ui/button";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface Medico {
  id: string;
  nome: string;
  telefone: string;
}

interface SeletorMedicoProps {
  value: string;
  onChange: (id: string) => void;
}

export function SeletorMedico({ value, onChange }: SeletorMedicoProps) {
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [open, setOpen] = useState(false);
  const [busca, setBusca] = useState("");

  useEffect(() => {
    async function buscar() {
      if (busca.length < 2) return;

      try {
        const res = await fetch(`/api/medicos?q=${encodeURIComponent(busca)}&limit=20`);
        const data = await res.json();
        setMedicos(data);
      } catch (error) {
        console.error(error);
      }
    }

    const debounce = setTimeout(buscar, 300);
    return () => clearTimeout(debounce);
  }, [busca]);

  const selected = medicos.find((m) => m.id === value);

  return (
    <div className="space-y-2">
      <Label>Médico</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" className="w-full justify-between">
            {selected ? selected.nome : "Buscar médico..."}
            <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0">
          <Command>
            <CommandInput
              placeholder="Digite o nome..."
              value={busca}
              onValueChange={setBusca}
            />
            <CommandEmpty>Nenhum médico encontrado</CommandEmpty>
            <CommandGroup>
              {medicos.map((medico) => (
                <CommandItem
                  key={medico.id}
                  value={medico.id}
                  onSelect={() => {
                    onChange(medico.id);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === medico.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <div className="flex flex-col">
                    <span>{medico.nome}</span>
                    <span className="text-xs text-muted-foreground">
                      {medico.telefone}
                    </span>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
```

---

### T4: Criar API routes (30min)

**Arquivo:** `dashboard/app/api/diretrizes/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies });
  const status = request.nextUrl.searchParams.get("status") || "ativa";

  const statusArray = status.split(",");

  const { data, error } = await supabase
    .from("diretrizes_contextuais")
    .select(`
      *,
      vagas (data, hospital_id),
      clientes (nome, telefone),
      hospitais (nome),
      especialidades (nome)
    `)
    .in("status", statusArray)
    .order("criado_em", { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const body = await request.json();

  const { data, error } = await supabase
    .from("diretrizes_contextuais")
    .insert({
      ...body,
      criado_por: user.id,
      status: "ativa",
    })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Listagem de diretrizes ativas
- [ ] Aba de histórico (expiradas/canceladas)
- [ ] Dialog para criar nova instrução
- [ ] Tipos: margem, regra especial, info
- [ ] Escopos: vaga, médico, hospital, especialidade, global
- [ ] Cancelamento de instruções
- [ ] Expiração opcional

### Testes
- [ ] Testes de listagem
- [ ] Testes de criação
- [ ] Testes de validação

### Verificação Manual

1. **Criar margem para vaga:**
   - Abrir dialog
   - Selecionar "Margem de Negociação"
   - Selecionar escopo "Vaga"
   - Escolher vaga
   - Definir valor máximo
   - Criar e verificar na lista

2. **Verificar que Julia usa:**
   - Iniciar conversa sobre a vaga
   - Verificar que Julia respeita a margem

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Instruções criadas pelo dashboard | > 70% |
| Erros de criação | < 2% |
