"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Settings,
  Users,
  MessageSquare,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Megaphone,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NovaCampanhaWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

interface CampanhaFormData {
  // Etapa 1 - Basico
  nome_template: string;
  tipo_campanha: string;
  categoria: string;
  objetivo: string;

  // Etapa 2 - Audiencia
  audiencia_tipo: "todos" | "filtrado";
  especialidades: string[];
  regioes: string[];
  status_cliente: string[];

  // Etapa 3 - Mensagem
  corpo: string;
  tom: string;

  // Etapa 4 - Agendamento
  agendar: boolean;
  agendar_para: string;
}

const STEPS = [
  { id: 1, title: "Configuracao", icon: Settings },
  { id: 2, title: "Audiencia", icon: Users },
  { id: 3, title: "Mensagem", icon: MessageSquare },
  { id: 4, title: "Revisao", icon: CheckCircle2 },
];

const TIPOS_CAMPANHA = [
  { value: "oferta_plantao", label: "Oferta de Plantao" },
  { value: "reativacao", label: "Reativacao" },
  { value: "followup", label: "Follow-up" },
  { value: "descoberta", label: "Descoberta" },
];

const CATEGORIAS = [
  { value: "marketing", label: "Marketing" },
  { value: "operacional", label: "Operacional" },
  { value: "relacionamento", label: "Relacionamento" },
];

const TONS = [
  { value: "amigavel", label: "Amigavel" },
  { value: "profissional", label: "Profissional" },
  { value: "urgente", label: "Urgente" },
  { value: "casual", label: "Casual" },
];

const ESPECIALIDADES = [
  "Cardiologia",
  "Clinica Medica",
  "Pediatria",
  "Ortopedia",
  "Ginecologia",
  "Neurologia",
  "Dermatologia",
  "Oftalmologia",
];

const REGIOES = [
  "Sao Paulo - Capital",
  "ABC Paulista",
  "Campinas",
  "Ribeiro Preto",
  "Santos",
  "Sorocaba",
];

export function NovaCampanhaWizard({
  open,
  onOpenChange,
  onSuccess,
}: NovaCampanhaWizardProps) {
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<CampanhaFormData>({
    nome_template: "",
    tipo_campanha: "oferta_plantao",
    categoria: "marketing",
    objetivo: "",
    audiencia_tipo: "todos",
    especialidades: [],
    regioes: [],
    status_cliente: [],
    corpo: "",
    tom: "amigavel",
    agendar: false,
    agendar_para: "",
  });

  const updateFormData = (field: keyof CampanhaFormData, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const toggleArrayItem = (field: "especialidades" | "regioes" | "status_cliente", item: string) => {
    setFormData((prev) => {
      const array = prev[field];
      if (array.includes(item)) {
        return { ...prev, [field]: array.filter((i) => i !== item) };
      }
      return { ...prev, [field]: [...array, item] };
    });
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return formData.nome_template.trim() !== "";
      case 2:
        return true;
      case 3:
        return formData.corpo.trim() !== "";
      case 4:
        return true;
      default:
        return false;
    }
  };

  const handleSubmit = async () => {
    setLoading(true);

    try {
      const payload = {
        nome_template: formData.nome_template,
        tipo_campanha: formData.tipo_campanha,
        categoria: formData.categoria,
        objetivo: formData.objetivo || null,
        corpo: formData.corpo,
        tom: formData.tom,
        audience_filters:
          formData.audiencia_tipo === "filtrado"
            ? {
                especialidades: formData.especialidades,
                regioes: formData.regioes,
                status_cliente: formData.status_cliente,
              }
            : {},
        agendar_para: formData.agendar && formData.agendar_para
          ? new Date(formData.agendar_para).toISOString()
          : null,
        status: formData.agendar ? "agendada" : "rascunho",
      };

      const res = await fetch("/api/campanhas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Erro ao criar campanha");
      }

      onSuccess();
      resetForm();
    } catch {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Nao foi possivel criar a campanha.",
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setStep(1);
    setFormData({
      nome_template: "",
      tipo_campanha: "oferta_plantao",
      categoria: "marketing",
      objetivo: "",
      audiencia_tipo: "todos",
      especialidades: [],
      regioes: [],
      status_cliente: [],
      corpo: "",
      tom: "amigavel",
      agendar: false,
      agendar_para: "",
    });
  };

  const handleClose = () => {
    resetForm();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Megaphone className="h-5 w-5" />
            Nova Campanha
          </DialogTitle>
        </DialogHeader>

        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-6">
          {STEPS.map((s, index) => {
            const StepIcon = s.icon;
            const isActive = step === s.id;
            const isCompleted = step > s.id;

            return (
              <div key={s.id} className="flex items-center">
                <div
                  className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors",
                    isActive && "border-primary bg-primary text-white",
                    isCompleted && "border-green-500 bg-green-500 text-white",
                    !isActive && !isCompleted && "border-gray-300 text-gray-400"
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <StepIcon className="h-5 w-5" />
                  )}
                </div>
                <span
                  className={cn(
                    "ml-2 text-sm font-medium",
                    isActive && "text-primary",
                    !isActive && "text-gray-500"
                  )}
                >
                  {s.title}
                </span>
                {index < STEPS.length - 1 && (
                  <ChevronRight className="mx-4 h-5 w-5 text-gray-300" />
                )}
              </div>
            );
          })}
        </div>

        {/* Step Content */}
        <div className="min-h-[300px]">
          {step === 1 && (
            <Step1Configuracao formData={formData} updateFormData={updateFormData} />
          )}
          {step === 2 && (
            <Step2Audiencia
              formData={formData}
              updateFormData={updateFormData}
              toggleArrayItem={toggleArrayItem}
            />
          )}
          {step === 3 && (
            <Step3Mensagem formData={formData} updateFormData={updateFormData} />
          )}
          {step === 4 && (
            <Step4Revisao formData={formData} updateFormData={updateFormData} />
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between mt-6 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => setStep((s) => s - 1)}
            disabled={step === 1}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Voltar
          </Button>

          {step < 4 ? (
            <Button onClick={() => setStep((s) => s + 1)} disabled={!canProceed()}>
              Proximo
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Criando...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Criar Campanha
                </>
              )}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Step 1 - Configuracao
function Step1Configuracao({
  formData,
  updateFormData,
}: {
  formData: CampanhaFormData;
  updateFormData: (field: keyof CampanhaFormData, value: unknown) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="nome">Nome da Campanha *</Label>
        <Input
          id="nome"
          placeholder="Ex: Oferta Cardio ABC - Janeiro"
          value={formData.nome_template}
          onChange={(e) => updateFormData("nome_template", e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Tipo de Campanha</Label>
          <Select
            value={formData.tipo_campanha}
            onValueChange={(v) => updateFormData("tipo_campanha", v)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIPOS_CAMPANHA.map((tipo) => (
                <SelectItem key={tipo.value} value={tipo.value}>
                  {tipo.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>Categoria</Label>
          <Select
            value={formData.categoria}
            onValueChange={(v) => updateFormData("categoria", v)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIAS.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="objetivo">Objetivo (opcional)</Label>
        <Textarea
          id="objetivo"
          placeholder="Descreva o objetivo desta campanha..."
          value={formData.objetivo}
          onChange={(e) => updateFormData("objetivo", e.target.value)}
          rows={3}
        />
      </div>
    </div>
  );
}

// Step 2 - Audiencia
function Step2Audiencia({
  formData,
  updateFormData,
  toggleArrayItem,
}: {
  formData: CampanhaFormData;
  updateFormData: (field: keyof CampanhaFormData, value: unknown) => void;
  toggleArrayItem: (field: "especialidades" | "regioes" | "status_cliente", item: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <Label>Audiencia</Label>
        <Select
          value={formData.audiencia_tipo}
          onValueChange={(v) => updateFormData("audiencia_tipo", v as "todos" | "filtrado")}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os medicos</SelectItem>
            <SelectItem value="filtrado">Filtrar audiencia</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {formData.audiencia_tipo === "filtrado" && (
        <>
          <div>
            <Label className="mb-2 block">Especialidades</Label>
            <div className="flex flex-wrap gap-2">
              {ESPECIALIDADES.map((esp) => (
                <Badge
                  key={esp}
                  variant={formData.especialidades.includes(esp) ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => toggleArrayItem("especialidades", esp)}
                >
                  {esp}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <Label className="mb-2 block">Regioes</Label>
            <div className="flex flex-wrap gap-2">
              {REGIOES.map((reg) => (
                <Badge
                  key={reg}
                  variant={formData.regioes.includes(reg) ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => toggleArrayItem("regioes", reg)}
                >
                  {reg}
                </Badge>
              ))}
            </div>
          </div>
        </>
      )}

      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-600">
          {formData.audiencia_tipo === "todos" ? (
            <>A campanha sera enviada para todos os medicos cadastrados.</>
          ) : (
            <>
              Filtros selecionados:{" "}
              {formData.especialidades.length > 0 && (
                <span className="font-medium">{formData.especialidades.length} especialidades</span>
              )}
              {formData.regioes.length > 0 && (
                <span className="font-medium ml-1">, {formData.regioes.length} regioes</span>
              )}
              {formData.especialidades.length === 0 && formData.regioes.length === 0 && (
                <span className="text-gray-400">Nenhum filtro selecionado</span>
              )}
            </>
          )}
        </p>
      </div>
    </div>
  );
}

// Step 3 - Mensagem
function Step3Mensagem({
  formData,
  updateFormData,
}: {
  formData: CampanhaFormData;
  updateFormData: (field: keyof CampanhaFormData, value: unknown) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <Label>Tom da Mensagem</Label>
        <Select value={formData.tom} onValueChange={(v) => updateFormData("tom", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TONS.map((tom) => (
              <SelectItem key={tom.value} value={tom.value}>
                {tom.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="corpo">Mensagem *</Label>
        <Textarea
          id="corpo"
          placeholder="Digite a mensagem que sera enviada aos medicos...

Use {{nome}} para inserir o nome do medico.
Use {{especialidade}} para a especialidade.
Use {{hospital}} para o hospital da vaga."
          value={formData.corpo}
          onChange={(e) => updateFormData("corpo", e.target.value)}
          rows={8}
          className="font-mono text-sm"
        />
        <p className="text-xs text-gray-500 mt-1">
          Variaveis disponiveis: {"{{nome}}"}, {"{{especialidade}}"}, {"{{hospital}}"}, {"{{valor}}"}
        </p>
      </div>

      {formData.corpo && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm font-medium text-green-800 mb-2">Preview:</p>
          <p className="text-sm text-green-700 whitespace-pre-wrap">
            {formData.corpo
              .replace("{{nome}}", "Dr. Carlos")
              .replace("{{especialidade}}", "Cardiologia")
              .replace("{{hospital}}", "Hospital Sao Luiz")
              .replace("{{valor}}", "R$ 2.500")}
          </p>
        </div>
      )}
    </div>
  );
}

// Step 4 - Revisao
function Step4Revisao({
  formData,
  updateFormData,
}: {
  formData: CampanhaFormData;
  updateFormData: (field: keyof CampanhaFormData, value: unknown) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <h3 className="font-medium">Resumo da Campanha</h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Nome:</span>
            <p className="font-medium">{formData.nome_template}</p>
          </div>

          <div>
            <span className="text-gray-500">Tipo:</span>
            <p className="font-medium">
              {TIPOS_CAMPANHA.find((t) => t.value === formData.tipo_campanha)?.label}
            </p>
          </div>

          <div>
            <span className="text-gray-500">Categoria:</span>
            <p className="font-medium">
              {CATEGORIAS.find((c) => c.value === formData.categoria)?.label}
            </p>
          </div>

          <div>
            <span className="text-gray-500">Tom:</span>
            <p className="font-medium">
              {TONS.find((t) => t.value === formData.tom)?.label}
            </p>
          </div>
        </div>

        {formData.objetivo && (
          <div className="text-sm">
            <span className="text-gray-500">Objetivo:</span>
            <p>{formData.objetivo}</p>
          </div>
        )}

        <div className="text-sm">
          <span className="text-gray-500">Audiencia:</span>
          <p>
            {formData.audiencia_tipo === "todos"
              ? "Todos os medicos"
              : `Filtrada (${formData.especialidades.length} especialidades, ${formData.regioes.length} regioes)`}
          </p>
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="agendar"
            checked={formData.agendar}
            onCheckedChange={(checked) => updateFormData("agendar", checked)}
          />
          <Label htmlFor="agendar">Agendar envio</Label>
        </div>

        {formData.agendar && (
          <div className="mt-4">
            <Label htmlFor="data">Data e Hora do Envio</Label>
            <Input
              id="data"
              type="datetime-local"
              value={formData.agendar_para}
              onChange={(e) => updateFormData("agendar_para", e.target.value)}
            />
          </div>
        )}

        {!formData.agendar && (
          <p className="text-sm text-gray-500 mt-2">
            A campanha sera salva como rascunho. Voce podera iniciar o envio manualmente depois.
          </p>
        )}
      </div>
    </div>
  );
}
