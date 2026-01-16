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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { Plus, Unlock, Calendar, MessageSquare, Loader2, History } from "lucide-react";
import { BloquearHospitalDialog } from "@/components/hospitais/bloquear-dialog";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

interface HospitalBloqueado {
  id: string;
  hospital_id: string;
  motivo: string;
  bloqueado_por: string;
  bloqueado_em: string;
  status: "bloqueado" | "desbloqueado";
  desbloqueado_em?: string;
  desbloqueado_por?: string;
  hospitais: {
    nome: string;
    cidade: string;
  };
  vagas_movidas?: number;
}

export default function HospitaisBloqueadosPage() {
  const { toast } = useToast();
  const [bloqueados, setBloqueados] = useState<HospitalBloqueado[]>([]);
  const [historico, setHistorico] = useState<HospitalBloqueado[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingHistorico, setLoadingHistorico] = useState(true);
  const [bloquearOpen, setBloquearOpen] = useState(false);
  const [desbloquearDialog, setDesbloquearDialog] = useState<HospitalBloqueado | null>(null);
  const [updating, setUpdating] = useState(false);
  const [tab, setTab] = useState<"ativos" | "historico">("ativos");
  const [error, setError] = useState<string | null>(null);

  const carregarBloqueados = async () => {
    try {
      setError(null);
      const res = await fetch("/api/hospitais/bloqueados");
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Erro ao carregar hospitais bloqueados");
        setBloqueados([]);
        return;
      }

      setBloqueados(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Erro ao carregar:", err);
      setError("Erro de conexao com o servidor");
      setBloqueados([]);
    } finally {
      setLoading(false);
    }
  };

  const carregarHistorico = async () => {
    try {
      const res = await fetch("/api/hospitais/bloqueados?historico=true");
      const data = await res.json();

      if (!res.ok) {
        setHistorico([]);
        return;
      }

      setHistorico(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Erro ao carregar historico:", err);
      setHistorico([]);
    } finally {
      setLoadingHistorico(false);
    }
  };

  useEffect(() => {
    carregarBloqueados();
  }, []);

  useEffect(() => {
    if (tab === "historico" && historico.length === 0 && loadingHistorico) {
      carregarHistorico();
    }
  }, [tab, historico.length, loadingHistorico]);

  const handleDesbloquear = async (hospital: HospitalBloqueado) => {
    setUpdating(true);
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
        description: `${hospital.hospitais?.nome ?? "Hospital"} foi desbloqueado. ${data.vagas_restauradas} vaga(s) restaurada(s).`,
      });

      setDesbloquearDialog(null);
      carregarBloqueados();
      // Recarregar historico se estiver na aba
      if (tab === "historico") {
        setLoadingHistorico(true);
        carregarHistorico();
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Nao foi possivel desbloquear o hospital.",
      });
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Hospitais Bloqueados</h1>
          <p className="text-gray-500">
            Julia nao oferece vagas de hospitais bloqueados
          </p>
        </div>

        <Button onClick={() => setBloquearOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Bloquear Hospital
        </Button>
      </div>

      {/* Alerta informativo */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          Quando um hospital e bloqueado, suas vagas sao movidas para uma tabela
          separada. Julia automaticamente deixa de ver e ofertar essas vagas.
          Ao desbloquear, vagas futuras sao restauradas.
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
          <TabsTrigger value="ativos">
            Bloqueados Ativos ({bloqueados.length})
          </TabsTrigger>
          <TabsTrigger value="historico">
            <History className="h-4 w-4 mr-2" />
            Historico
          </TabsTrigger>
        </TabsList>

        <TabsContent value="ativos" className="mt-4">
          <div className="border rounded-lg bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hospital</TableHead>
                  <TableHead>Cidade</TableHead>
                  <TableHead>Motivo</TableHead>
                  <TableHead>Bloqueado ha</TableHead>
                  <TableHead>Vagas afetadas</TableHead>
                  <TableHead className="w-[120px]">Acoes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                    </TableCell>
                  </TableRow>
                ) : bloqueados.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-4xl">🏥</span>
                        <span className="text-gray-600">Nenhum hospital bloqueado</span>
                        <span className="text-sm text-gray-400">
                          Todos os hospitais estao ativos para oferta
                        </span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  bloqueados.map((hospital) => (
                    <TableRow key={hospital.id}>
                      <TableCell className="font-medium">
                        {hospital.hospitais?.nome ?? "Hospital desconhecido"}
                      </TableCell>
                      <TableCell className="text-gray-600">
                        {hospital.hospitais?.cidade ?? "-"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-gray-400" />
                          <span className="max-w-[200px] truncate text-gray-600">
                            {hospital.motivo}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-gray-600">
                          <Calendar className="h-4 w-4 text-gray-400" />
                          {hospital.bloqueado_em
                            ? formatDistanceToNow(new Date(hospital.bloqueado_em), {
                                addSuffix: true,
                                locale: ptBR,
                              })
                            : "-"}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {hospital.vagas_movidas ?? 0} vagas
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
        </TabsContent>

        <TabsContent value="historico" className="mt-4">
          <div className="border rounded-lg bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hospital</TableHead>
                  <TableHead>Motivo</TableHead>
                  <TableHead>Bloqueado em</TableHead>
                  <TableHead>Desbloqueado em</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingHistorico ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                    </TableCell>
                  </TableRow>
                ) : historico.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      <span className="text-gray-400">Nenhum historico encontrado</span>
                    </TableCell>
                  </TableRow>
                ) : (
                  historico.map((registro) => (
                    <TableRow key={registro.id}>
                      <TableCell className="font-medium">
                        {registro.hospitais?.nome ?? "Hospital desconhecido"}
                      </TableCell>
                      <TableCell className="text-gray-600 max-w-[200px] truncate">
                        {registro.motivo}
                      </TableCell>
                      <TableCell className="text-gray-600">
                        {new Date(registro.bloqueado_em).toLocaleDateString("pt-BR")}
                      </TableCell>
                      <TableCell className="text-gray-600">
                        {registro.desbloqueado_em
                          ? new Date(registro.desbloqueado_em).toLocaleDateString("pt-BR")
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            registro.status === "bloqueado"
                              ? "bg-red-50 text-red-700 border-red-200"
                              : "bg-green-50 text-green-700 border-green-200"
                          }
                        >
                          {registro.status === "bloqueado" ? "Bloqueado" : "Desbloqueado"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* Dialog para bloquear */}
      <BloquearHospitalDialog
        open={bloquearOpen}
        onOpenChange={setBloquearOpen}
        onSuccess={() => {
          carregarBloqueados();
          if (tab === "historico") {
            setLoadingHistorico(true);
            carregarHistorico();
          }
        }}
      />

      {/* Dialog de confirmacao para desbloquear */}
      <AlertDialog
        open={!!desbloquearDialog}
        onOpenChange={() => setDesbloquearDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desbloquear hospital?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                {desbloquearDialog && (
                  <>
                    Voce esta prestes a desbloquear{" "}
                    <strong>{desbloquearDialog.hospitais?.nome ?? "o hospital"}</strong>.
                    <br />
                    <br />
                    Vagas futuras deste hospital serao restauradas e Julia voltara
                    a ofertas normalmente.
                  </>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={updating}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => desbloquearDialog && handleDesbloquear(desbloquearDialog)}
              disabled={updating}
            >
              {updating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Confirmar desbloqueio"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
