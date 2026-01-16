"use client";

import { useState, useEffect, useCallback } from "react";
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
import { useToast } from "@/hooks/use-toast";
import {
  Plus,
  MoreHorizontal,
  Trash2,
  Calendar,
  User,
  Building2,
  Briefcase,
  Globe,
  Loader2,
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
  vagas?: { data: string; hospital_id: string } | null;
  clientes?: { primeiro_nome: string; sobrenome: string; telefone: string } | null;
  hospitais?: { nome: string } | null;
  especialidades?: { nome: string } | null;
}

const escopoIcons: Record<Escopo, React.ReactNode> = {
  vaga: <Calendar className="h-4 w-4" />,
  medico: <User className="h-4 w-4" />,
  hospital: <Building2 className="h-4 w-4" />,
  especialidade: <Briefcase className="h-4 w-4" />,
  global: <Globe className="h-4 w-4" />,
};

const tipoLabels: Record<TipoDiretriz, string> = {
  margem_negociacao: "Margem de Negociacao",
  regra_especial: "Regra Especial",
  info_adicional: "Info Adicional",
};

function getEscopoLabel(diretriz: Diretriz): string {
  switch (diretriz.escopo) {
    case "vaga":
      return diretriz.vagas?.data
        ? `Vaga ${format(new Date(diretriz.vagas.data), "dd/MM")}`
        : "Vaga";
    case "medico":
      return diretriz.clientes
        ? `${diretriz.clientes.primeiro_nome} ${diretriz.clientes.sobrenome}`.trim()
        : "Medico";
    case "hospital":
      return diretriz.hospitais?.nome ?? "Hospital";
    case "especialidade":
      return diretriz.especialidades?.nome ?? "Especialidade";
    case "global":
      return "Todas as conversas";
    default:
      return "";
  }
}

function getConteudoLabel(diretriz: Diretriz): string {
  const { conteudo, tipo } = diretriz;

  if (tipo === "margem_negociacao") {
    if (conteudo.valor_maximo) {
      return `Ate R$ ${conteudo.valor_maximo.toLocaleString("pt-BR")}`;
    }
    if (conteudo.percentual_maximo) {
      return `Ate ${conteudo.percentual_maximo}% acima`;
    }
  }

  if (tipo === "regra_especial") {
    return conteudo.regra ?? "";
  }

  if (tipo === "info_adicional") {
    return conteudo.info ?? "";
  }

  return JSON.stringify(conteudo);
}

export default function InstrucoesPage() {
  const { toast } = useToast();
  const [diretrizes, setDiretrizes] = useState<Diretriz[]>([]);
  const [loading, setLoading] = useState(true);
  const [novaOpen, setNovaOpen] = useState(false);
  const [cancelarDialog, setCancelarDialog] = useState<Diretriz | null>(null);
  const [canceling, setCanceling] = useState(false);
  const [tab, setTab] = useState<"ativas" | "historico">("ativas");

  const [error, setError] = useState<string | null>(null);

  const carregarDiretrizes = useCallback(async () => {
    try {
      setError(null);
      const status = tab === "ativas" ? "ativa" : "expirada,cancelada";
      const res = await fetch(`/api/diretrizes?status=${status}`);
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Erro ao carregar diretrizes");
        setDiretrizes([]);
        return;
      }

      setDiretrizes(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Erro ao carregar:", err);
      setError("Erro de conexao com o servidor");
      setDiretrizes([]);
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    setLoading(true);
    carregarDiretrizes();
  }, [carregarDiretrizes]);

  const handleCancelar = async (diretriz: Diretriz) => {
    setCanceling(true);
    try {
      const res = await fetch(`/api/diretrizes/${diretriz.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "cancelada" }),
      });

      if (!res.ok) throw new Error("Erro ao cancelar");

      toast({
        title: "Instrucao cancelada",
        description: "A diretriz foi desativada.",
      });

      setCancelarDialog(null);
      carregarDiretrizes();
    } catch {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Nao foi possivel cancelar a instrucao.",
      });
    } finally {
      setCanceling(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Instrucoes Ativas</h1>
          <p className="text-gray-500">
            Diretrizes contextuais que Julia segue nas conversas
          </p>
        </div>

        <Button onClick={() => setNovaOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Instrucao
        </Button>
      </div>

      {/* Alerta informativo */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          Instrucoes sao regras especificas que Julia segue em conversas.
          Por exemplo: margens de negociacao para vagas, regras especiais
          para hospitais ou informacoes sobre medicos.
        </p>
      </div>

      {/* Erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="ativas">Ativas ({diretrizes.length})</TabsTrigger>
          <TabsTrigger value="historico">Historico</TabsTrigger>
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

      {/* Dialog nova instrucao */}
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
            <AlertDialogTitle>Cancelar instrucao?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta instrucao sera desativada e Julia deixara de segui-la.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={canceling}>Voltar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => cancelarDialog && handleCancelar(cancelarDialog)}
              disabled={canceling}
            >
              {canceling ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Confirmar cancelamento"
              )}
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
    <div className="border rounded-lg bg-white">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tipo</TableHead>
            <TableHead>Escopo</TableHead>
            <TableHead>Conteudo</TableHead>
            <TableHead>Criada</TableHead>
            <TableHead>Expira</TableHead>
            {showActions && <TableHead className="w-[50px]"></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-8">
                <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
              </TableCell>
            </TableRow>
          ) : diretrizes.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-8">
                <div className="flex flex-col items-center gap-2">
                  <span className="text-4xl">📋</span>
                  <span className="text-gray-600">Nenhuma instrucao encontrada</span>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            diretrizes.map((diretriz) => (
              <TableRow key={diretriz.id}>
                <TableCell>
                  <Badge variant="outline">{tipoLabels[diretriz.tipo]}</Badge>
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
                  {diretriz.criado_em
                    ? formatDistanceToNow(new Date(diretriz.criado_em), {
                        addSuffix: true,
                        locale: ptBR,
                      })
                    : "-"}
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
                    <span className="text-gray-400">Nao expira</span>
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
