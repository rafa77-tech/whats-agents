"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
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
import { useToast } from "@/hooks/use-toast";
import {
  Shield,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";

interface SystemStatus {
  pilot_mode: boolean;
  autonomous_features: {
    discovery_automatico: boolean;
    oferta_automatica: boolean;
    reativacao_automatica: boolean;
    feedback_automatico: boolean;
  };
  last_changed_by?: string;
  last_changed_at?: string;
}

export default function SistemaPage() {
  const { toast } = useToast();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmDialog, setConfirmDialog] = useState<"enable" | "disable" | null>(null);
  const [updating, setUpdating] = useState(false);

  const carregarStatus = async () => {
    try {
      const res = await fetch("/api/sistema/status");
      const data = await res.json();
      setStatus(data);
    } catch (error) {
      console.error("Erro ao carregar status:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarStatus();
  }, []);

  const handleToggle = async (novoPilotMode: boolean) => {
    setUpdating(true);

    try {
      const res = await fetch("/api/sistema/pilot-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pilot_mode: novoPilotMode }),
      });

      if (!res.ok) throw new Error("Erro ao atualizar");

      toast({
        title: novoPilotMode ? "Modo Piloto ATIVADO" : "Modo Piloto DESATIVADO",
        description: novoPilotMode
          ? "Julia nao executara acoes autonomas."
          : "Julia agora age autonomamente!",
      });

      setConfirmDialog(null);
      carregarStatus();
    } catch (_error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Nao foi possivel alterar o modo piloto.",
      });
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sistema</h1>
          <p className="text-gray-500">Configuracoes e controles do sistema Julia</p>
        </div>
        <div className="text-center py-8">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-gray-400" />
          <p className="text-gray-500 mt-2">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sistema</h1>
        <p className="text-gray-500">Configuracoes e controles do sistema Julia</p>
      </div>

      {/* Card principal do Modo Piloto */}
      <Card className={status?.pilot_mode ? "border-yellow-300" : "border-green-300"}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield
                className={`h-8 w-8 ${
                  status?.pilot_mode ? "text-yellow-500" : "text-green-500"
                }`}
              />
              <div>
                <CardTitle className="text-xl">Modo Piloto</CardTitle>
                <CardDescription>
                  Controla se Julia age autonomamente
                </CardDescription>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Badge
                variant="outline"
                className={
                  status?.pilot_mode
                    ? "bg-yellow-100 text-yellow-800 border-yellow-300"
                    : "bg-green-100 text-green-800 border-green-300"
                }
              >
                {status?.pilot_mode ? "ATIVO" : "DESATIVADO"}
              </Badge>

              <Switch
                checked={!status?.pilot_mode}
                onCheckedChange={(checked) => {
                  setConfirmDialog(checked ? "disable" : "enable");
                }}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {status?.pilot_mode ? (
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-yellow-800 mb-2">
                <AlertTriangle className="h-5 w-5" />
                <span className="font-medium">Modo seguro ativo</span>
              </div>
              <p className="text-sm text-yellow-700">
                Julia esta em modo piloto. Acoes autonomas estao desabilitadas.
                Ela so responde quando acionada por campanhas manuais ou mensagens
                de medicos.
              </p>
            </div>
          ) : (
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-green-800 mb-2">
                <Zap className="h-5 w-5" />
                <span className="font-medium">Julia autonoma</span>
              </div>
              <p className="text-sm text-green-700">
                Julia esta operando de forma autonoma. Ela identifica oportunidades
                e age proativamente conforme as regras configuradas.
              </p>
            </div>
          )}

          {/* Status das features autonomas */}
          <div className="grid grid-cols-2 gap-4 pt-4">
            <FeatureStatus
              title="Discovery Automatico"
              description="Conhecer medicos nao-enriquecidos"
              enabled={status?.autonomous_features.discovery_automatico ?? false}
            />
            <FeatureStatus
              title="Oferta Automatica"
              description="Ofertar vagas com furo de escala"
              enabled={status?.autonomous_features.oferta_automatica ?? false}
            />
            <FeatureStatus
              title="Reativacao Automatica"
              description="Retomar contato com inativos"
              enabled={status?.autonomous_features.reativacao_automatica ?? false}
            />
            <FeatureStatus
              title="Feedback Automatico"
              description="Pedir feedback pos-plantao"
              enabled={status?.autonomous_features.feedback_automatico ?? false}
            />
          </div>

          {/* Ultima alteracao */}
          {status?.last_changed_at && (
            <p className="text-xs text-gray-500 pt-4">
              Ultima alteracao: {new Date(status.last_changed_at).toLocaleString("pt-BR")}
              {status.last_changed_by && ` por ${status.last_changed_by}`}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Outros cards de configuracao */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Rate Limiting</CardTitle>
            <CardDescription>Limites de envio de mensagens</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Mensagens por hora</span>
                <span className="font-medium">20</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Mensagens por dia</span>
                <span className="font-medium">100</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Intervalo entre mensagens</span>
                <span className="font-medium">45-180s</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Horario de Operacao</CardTitle>
            <CardDescription>Quando Julia pode enviar mensagens</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Horario</span>
                <span className="font-medium">08h as 20h</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Dias</span>
                <span className="font-medium">Segunda a Sexta</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dialogs de confirmacao */}
      <AlertDialog
        open={confirmDialog === "enable"}
        onOpenChange={() => setConfirmDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ativar Modo Piloto?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                Julia deixara de agir autonomamente. As seguintes funcionalidades
                serao desabilitadas:
                <ul className="list-disc list-inside mt-2">
                  <li>Discovery automatico</li>
                  <li>Oferta automatica por furo de escala</li>
                  <li>Reativacao automatica</li>
                  <li>Feedback automatico</li>
                </ul>
                <p className="mt-4">
                  Julia ainda respondera mensagens de medicos e campanhas manuais.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleToggle(true)}
              disabled={updating}
            >
              {updating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Ativar Modo Piloto"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={confirmDialog === "disable"}
        onOpenChange={() => setConfirmDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desativar Modo Piloto?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                <div className="flex items-center gap-2 text-yellow-600 mb-4">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Atencao: acao significativa</span>
                </div>
                Julia passara a agir autonomamente:
                <ul className="list-disc list-inside mt-2">
                  <li>Iniciara Discovery com medicos nao-enriquecidos</li>
                  <li>Ofertara vagas quando houver furo de escala</li>
                  <li>Reativara medicos inativos</li>
                  <li>Pedira feedback apos plantoes</li>
                </ul>
                <p className="mt-4">
                  Certifique-se de que as configuracoes estao corretas antes de prosseguir.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleToggle(false)}
              disabled={updating}
              className="bg-green-600 hover:bg-green-700"
            >
              {updating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Desativar Modo Piloto"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

interface FeatureStatusProps {
  title: string;
  description: string;
  enabled: boolean;
}

function FeatureStatus({ title, description, enabled }: FeatureStatusProps) {
  return (
    <div
      className={`p-3 rounded-lg border ${
        enabled
          ? "bg-green-50 border-green-200"
          : "bg-gray-50 border-gray-200"
      }`}
    >
      <div className="flex items-center gap-2">
        {enabled ? (
          <CheckCircle2 className="h-4 w-4 text-green-600" />
        ) : (
          <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
        )}
        <span className={`font-medium ${enabled ? "text-green-800" : "text-gray-500"}`}>
          {title}
        </span>
      </div>
      <p className={`text-xs mt-1 ${enabled ? "text-green-600" : "text-gray-400"}`}>
        {description}
      </p>
    </div>
  );
}
