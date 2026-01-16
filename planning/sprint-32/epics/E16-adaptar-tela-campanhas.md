# E16 - Adaptar Tela de Campanhas

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 5 - Dashboard
**Dependências:** E14 (Reestruturar Campanhas)
**Estimativa:** 6h

---

## Objetivo

Adaptar a tela de campanhas do dashboard para suportar o novo modelo de **comportamento** com tipos, objetivos, regras e escopo de vagas.

---

## Contexto

O dashboard já existe (Sprint 28) com:
- Next.js 14 + shadcn/ui + Tailwind
- Página de campanhas em `/app/campanhas/page.tsx`
- Listagem básica de campanhas

**Problema:** A tela atual mostra campos legados (`corpo`, `template`) que não fazem mais sentido.

---

## Solução

Criar wizard de criação de campanhas com:
1. Seleção do tipo de comportamento
2. Definição de objetivo
3. Configuração de regras
4. Escopo de vagas (se tipo=oferta)
5. Preview e criação

---

## Tasks

### T1: Criar componente de seleção de tipo (1h)

**Arquivo:** `dashboard/components/campanhas/tipo-selector.tsx`

```tsx
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Search, Gift, MessageSquare, Star, RefreshCw } from "lucide-react";

export type TipoCampanha = "discovery" | "oferta" | "followup" | "feedback" | "reativacao";

interface TipoInfo {
  tipo: TipoCampanha;
  titulo: string;
  descricao: string;
  icon: React.ReactNode;
  podeOfertar: boolean;
  cor: string;
}

const TIPOS: TipoInfo[] = [
  {
    tipo: "discovery",
    titulo: "Discovery",
    descricao: "Conhecer médicos novos. Não ofertar vagas.",
    icon: <Search className="h-6 w-6" />,
    podeOfertar: false,
    cor: "border-blue-500 bg-blue-50",
  },
  {
    tipo: "oferta",
    titulo: "Oferta",
    descricao: "Apresentar vagas específicas para médicos.",
    icon: <Gift className="h-6 w-6" />,
    podeOfertar: true,
    cor: "border-green-500 bg-green-50",
  },
  {
    tipo: "followup",
    titulo: "Follow-up",
    descricao: "Manter relacionamento ativo.",
    icon: <MessageSquare className="h-6 w-6" />,
    podeOfertar: false,
    cor: "border-purple-500 bg-purple-50",
  },
  {
    tipo: "feedback",
    titulo: "Feedback",
    descricao: "Coletar opinião sobre plantões.",
    icon: <Star className="h-6 w-6" />,
    podeOfertar: false,
    cor: "border-yellow-500 bg-yellow-50",
  },
  {
    tipo: "reativacao",
    titulo: "Reativação",
    descricao: "Retomar contato com inativos.",
    icon: <RefreshCw className="h-6 w-6" />,
    podeOfertar: false,
    cor: "border-orange-500 bg-orange-50",
  },
];

interface TipoSelectorProps {
  value: TipoCampanha | null;
  onChange: (tipo: TipoCampanha) => void;
}

export function TipoSelector({ value, onChange }: TipoSelectorProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {TIPOS.map((tipo) => (
        <Card
          key={tipo.tipo}
          className={cn(
            "cursor-pointer transition-all hover:shadow-md",
            value === tipo.tipo ? tipo.cor : "hover:border-gray-300"
          )}
          onClick={() => onChange(tipo.tipo)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              {tipo.icon}
              <CardTitle className="text-lg">{tipo.titulo}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <CardDescription>{tipo.descricao}</CardDescription>
            {tipo.podeOfertar && (
              <span className="inline-block mt-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                Pode ofertar vagas
              </span>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function getTipoInfo(tipo: TipoCampanha): TipoInfo | undefined {
  return TIPOS.find((t) => t.tipo === tipo);
}
```

---

### T2: Criar componente de regras (1h)

**Arquivo:** `dashboard/components/campanhas/regras-editor.tsx`

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { X, Plus, Lightbulb } from "lucide-react";
import { TipoCampanha } from "./tipo-selector";

// Regras padrão por tipo
const REGRAS_PADRAO: Record<TipoCampanha, string[]> = {
  discovery: [
    "Nunca mencionar vagas ou oportunidades",
    "Não falar de valores",
    "Foco em conhecer o médico",
    "Só ofertar se médico perguntar explicitamente",
  ],
  oferta: [
    "Apresentar apenas vagas dentro do escopo definido",
    "Consultar sistema antes de mencionar qualquer vaga",
    "Nunca inventar ou prometer vagas",
    "Respeitar margem de negociação definida",
  ],
  followup: [
    "Perguntar como o médico está",
    "Manter conversa leve e natural",
    "Só ofertar se médico perguntar",
  ],
  feedback: [
    "Perguntar como foi o plantão",
    "Coletar elogios e reclamações",
    "Não ofertar novo plantão proativamente",
  ],
  reativacao: [
    "Reestabelecer contato de forma natural",
    "Perguntar se ainda tem interesse em plantões",
    "Não ofertar imediatamente",
  ],
};

interface RegrasEditorProps {
  tipo: TipoCampanha;
  value: string[];
  onChange: (regras: string[]) => void;
}

export function RegrasEditor({ tipo, value, onChange }: RegrasEditorProps) {
  const [novaRegra, setNovaRegra] = useState("");

  const adicionarRegra = () => {
    if (novaRegra.trim()) {
      onChange([...value, novaRegra.trim()]);
      setNovaRegra("");
    }
  };

  const removerRegra = (index: number) => {
    const novas = value.filter((_, i) => i !== index);
    onChange(novas);
  };

  const usarPadrao = () => {
    onChange(REGRAS_PADRAO[tipo] || []);
  };

  return (
    <div className="space-y-4">
      {/* Botão para usar regras padrão */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Regras comportamentais que Julia seguirá nesta campanha.
        </p>
        <Button variant="outline" size="sm" onClick={usarPadrao}>
          <Lightbulb className="h-4 w-4 mr-2" />
          Usar padrão
        </Button>
      </div>

      {/* Lista de regras */}
      <div className="space-y-2">
        {value.map((regra, index) => (
          <div
            key={index}
            className="flex items-center gap-2 p-2 bg-gray-50 rounded-md"
          >
            <span className="flex-1 text-sm">{regra}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => removerRegra(index)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>

      {/* Input para nova regra */}
      <div className="flex gap-2">
        <Input
          placeholder="Adicionar regra..."
          value={novaRegra}
          onChange={(e) => setNovaRegra(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && adicionarRegra()}
        />
        <Button onClick={adicionarRegra}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Preview de regras padrão */}
      {value.length === 0 && (
        <div className="p-4 bg-blue-50 rounded-lg">
          <p className="text-sm font-medium text-blue-800 mb-2">
            Regras padrão para {tipo}:
          </p>
          <div className="flex flex-wrap gap-2">
            {REGRAS_PADRAO[tipo]?.map((regra, i) => (
              <Badge key={i} variant="secondary">
                {regra}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

### T3: Criar componente de escopo de vagas (1h)

**Arquivo:** `dashboard/components/campanhas/escopo-vagas.tsx`

```tsx
"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DatePickerWithRange } from "@/components/ui/date-range-picker";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle, CheckCircle } from "lucide-react";
import { DateRange } from "react-day-picker";

export interface EscopoVagas {
  especialidade_id?: string;
  hospital_id?: string;
  regiao?: string;
  periodo_inicio?: string;
  periodo_fim?: string;
  turno?: "diurno" | "noturno" | "ambos";
  valor_minimo?: number;
  valor_maximo?: number;
}

interface EscopoVagasEditorProps {
  value: EscopoVagas;
  onChange: (escopo: EscopoVagas) => void;
}

export function EscopoVagasEditor({ value, onChange }: EscopoVagasEditorProps) {
  const [especialidades, setEspecialidades] = useState<Array<{id: string, nome: string}>>([]);
  const [hospitais, setHospitais] = useState<Array<{id: string, nome: string}>>([]);
  const [vagasDisponiveis, setVagasDisponiveis] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // Carregar especialidades e hospitais
  useEffect(() => {
    async function carregarDados() {
      const [espRes, hospRes] = await Promise.all([
        fetch("/api/especialidades"),
        fetch("/api/hospitais"),
      ]);

      const esp = await espRes.json();
      const hosp = await hospRes.json();

      setEspecialidades(esp);
      setHospitais(hosp);
    }

    carregarDados();
  }, []);

  // Verificar vagas disponíveis quando escopo muda
  useEffect(() => {
    async function verificarVagas() {
      if (!value.especialidade_id && !value.hospital_id && !value.periodo_inicio) {
        setVagasDisponiveis(null);
        return;
      }

      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (value.especialidade_id) params.set("especialidade_id", value.especialidade_id);
        if (value.hospital_id) params.set("hospital_id", value.hospital_id);
        if (value.periodo_inicio) params.set("periodo_inicio", value.periodo_inicio);
        if (value.periodo_fim) params.set("periodo_fim", value.periodo_fim);

        const res = await fetch(`/api/vagas/contar?${params}`);
        const data = await res.json();
        setVagasDisponiveis(data.count);
      } catch (error) {
        console.error("Erro ao verificar vagas:", error);
      } finally {
        setLoading(false);
      }
    }

    const debounce = setTimeout(verificarVagas, 500);
    return () => clearTimeout(debounce);
  }, [value]);

  const updateField = <K extends keyof EscopoVagas>(
    field: K,
    fieldValue: EscopoVagas[K]
  ) => {
    onChange({ ...value, [field]: fieldValue });
  };

  const handleDateChange = (range: DateRange | undefined) => {
    onChange({
      ...value,
      periodo_inicio: range?.from?.toISOString().split("T")[0],
      periodo_fim: range?.to?.toISOString().split("T")[0],
    });
  };

  return (
    <div className="space-y-6">
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Defina o escopo de vagas que Julia pode ofertar. A campanha só
          será disparada se existirem vagas neste escopo.
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Especialidade */}
        <div className="space-y-2">
          <Label>Especialidade</Label>
          <Select
            value={value.especialidade_id || ""}
            onValueChange={(v) => updateField("especialidade_id", v || undefined)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Qualquer especialidade" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Qualquer</SelectItem>
              {especialidades.map((esp) => (
                <SelectItem key={esp.id} value={esp.id}>
                  {esp.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Hospital */}
        <div className="space-y-2">
          <Label>Hospital</Label>
          <Select
            value={value.hospital_id || ""}
            onValueChange={(v) => updateField("hospital_id", v || undefined)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Qualquer hospital" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Qualquer</SelectItem>
              {hospitais.map((hosp) => (
                <SelectItem key={hosp.id} value={hosp.id}>
                  {hosp.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Período */}
        <div className="space-y-2 md:col-span-2">
          <Label>Período</Label>
          <DatePickerWithRange
            date={{
              from: value.periodo_inicio ? new Date(value.periodo_inicio) : undefined,
              to: value.periodo_fim ? new Date(value.periodo_fim) : undefined,
            }}
            onSelect={handleDateChange}
          />
        </div>

        {/* Turno */}
        <div className="space-y-2">
          <Label>Turno</Label>
          <Select
            value={value.turno || "ambos"}
            onValueChange={(v) => updateField("turno", v as EscopoVagas["turno"])}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ambos">Ambos</SelectItem>
              <SelectItem value="diurno">Diurno</SelectItem>
              <SelectItem value="noturno">Noturno</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Faixa de valor */}
        <div className="space-y-2">
          <Label>Faixa de valor</Label>
          <div className="flex gap-2 items-center">
            <Input
              type="number"
              placeholder="Mín"
              value={value.valor_minimo || ""}
              onChange={(e) =>
                updateField("valor_minimo", e.target.value ? Number(e.target.value) : undefined)
              }
            />
            <span>a</span>
            <Input
              type="number"
              placeholder="Máx"
              value={value.valor_maximo || ""}
              onChange={(e) =>
                updateField("valor_maximo", e.target.value ? Number(e.target.value) : undefined)
              }
            />
          </div>
        </div>
      </div>

      {/* Indicador de vagas disponíveis */}
      <div className="p-4 rounded-lg bg-gray-50">
        {loading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Verificando vagas...
          </div>
        ) : vagasDisponiveis !== null ? (
          <div
            className={`flex items-center gap-2 ${
              vagasDisponiveis > 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {vagasDisponiveis > 0 ? (
              <>
                <CheckCircle className="h-4 w-4" />
                {vagasDisponiveis} vaga(s) disponível(is) no escopo
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4" />
                Nenhuma vaga no escopo. A campanha não será disparada.
              </>
            )}
          </div>
        ) : (
          <span className="text-muted-foreground">
            Defina o escopo para ver vagas disponíveis
          </span>
        )}
      </div>
    </div>
  );
}
```

---

### T4: Criar wizard de criação (1.5h)

**Arquivo:** `dashboard/components/campanhas/criar-campanha-wizard.tsx`

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/use-toast";
import { TipoSelector, TipoCampanha, getTipoInfo } from "./tipo-selector";
import { RegrasEditor } from "./regras-editor";
import { EscopoVagasEditor, EscopoVagas } from "./escopo-vagas";
import { ArrowLeft, ArrowRight, Check, Loader2 } from "lucide-react";

interface CampanhaData {
  nome: string;
  tipo: TipoCampanha | null;
  objetivo: string;
  regras: string[];
  escopo_vagas: EscopoVagas;
}

interface CriarCampanhaWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const STEPS = [
  { id: 1, title: "Tipo", description: "Escolha o tipo de comportamento" },
  { id: 2, title: "Detalhes", description: "Nome e objetivo da campanha" },
  { id: 3, title: "Regras", description: "Defina as regras comportamentais" },
  { id: 4, title: "Escopo", description: "Defina o escopo de vagas" },
  { id: 5, title: "Revisar", description: "Confirme os dados" },
];

export function CriarCampanhaWizard({
  open,
  onOpenChange,
}: CriarCampanhaWizardProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<CampanhaData>({
    nome: "",
    tipo: null,
    objetivo: "",
    regras: [],
    escopo_vagas: {},
  });

  const tipoInfo = data.tipo ? getTipoInfo(data.tipo) : null;
  const needsEscopo = data.tipo === "oferta";

  // Ajustar steps se não precisa de escopo
  const activeSteps = needsEscopo
    ? STEPS
    : STEPS.filter((s) => s.id !== 4);
  const totalSteps = activeSteps.length;
  const progress = (step / totalSteps) * 100;

  const canProceed = () => {
    switch (step) {
      case 1:
        return data.tipo !== null;
      case 2:
        return data.nome.trim().length >= 3;
      case 3:
        return true; // Regras são opcionais
      case 4:
        // Escopo só aparece para oferta
        return !needsEscopo || Object.keys(data.escopo_vagas).length > 0;
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (step < totalSteps) {
      // Pular step 4 se não precisa de escopo
      if (step === 3 && !needsEscopo) {
        setStep(5);
      } else {
        setStep(step + 1);
      }
    }
  };

  const handleBack = () => {
    if (step > 1) {
      // Voltar do step 5 para 3 se não precisa de escopo
      if (step === 5 && !needsEscopo) {
        setStep(3);
      } else {
        setStep(step - 1);
      }
    }
  };

  const handleSubmit = async () => {
    setLoading(true);

    try {
      const payload = {
        nome: data.nome,
        tipo: data.tipo,
        objetivo: data.objetivo || undefined,
        regras: data.regras.length > 0 ? data.regras : undefined,
        escopo_vagas: needsEscopo ? data.escopo_vagas : undefined,
      };

      const res = await fetch("/api/campanhas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Erro ao criar campanha");
      }

      const campanha = await res.json();

      toast({
        title: "Campanha criada!",
        description: `${data.nome} foi criada com sucesso.`,
      });

      onOpenChange(false);
      router.push(`/campanhas/${campanha.id}`);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Não foi possível criar a campanha.",
      });
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <p className="text-muted-foreground">
              Escolha o tipo de comportamento da campanha.
            </p>
            <TipoSelector
              value={data.tipo}
              onChange={(tipo) => setData({ ...data, tipo })}
            />
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="nome">Nome da campanha *</Label>
              <Input
                id="nome"
                placeholder="Ex: Discovery Janeiro 2026"
                value={data.nome}
                onChange={(e) => setData({ ...data, nome: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="objetivo">Objetivo (opcional)</Label>
              <Textarea
                id="objetivo"
                placeholder="Descreva o objetivo em linguagem natural..."
                value={data.objetivo}
                onChange={(e) => setData({ ...data, objetivo: e.target.value })}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Este texto será incluído no prompt da Julia.
              </p>
            </div>
          </div>
        );

      case 3:
        return data.tipo ? (
          <RegrasEditor
            tipo={data.tipo}
            value={data.regras}
            onChange={(regras) => setData({ ...data, regras })}
          />
        ) : null;

      case 4:
        return (
          <EscopoVagasEditor
            value={data.escopo_vagas}
            onChange={(escopo_vagas) => setData({ ...data, escopo_vagas })}
          />
        );

      case 5:
        return (
          <div className="space-y-4">
            <h3 className="font-medium">Resumo da campanha</h3>

            <div className="grid gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <span className="text-sm text-muted-foreground">Nome:</span>
                <p className="font-medium">{data.nome}</p>
              </div>

              <div>
                <span className="text-sm text-muted-foreground">Tipo:</span>
                <p className="font-medium">{tipoInfo?.titulo}</p>
              </div>

              {data.objetivo && (
                <div>
                  <span className="text-sm text-muted-foreground">Objetivo:</span>
                  <p>{data.objetivo}</p>
                </div>
              )}

              {data.regras.length > 0 && (
                <div>
                  <span className="text-sm text-muted-foreground">
                    Regras ({data.regras.length}):
                  </span>
                  <ul className="list-disc list-inside text-sm">
                    {data.regras.slice(0, 3).map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                    {data.regras.length > 3 && (
                      <li className="text-muted-foreground">
                        +{data.regras.length - 3} mais...
                      </li>
                    )}
                  </ul>
                </div>
              )}

              {needsEscopo && Object.keys(data.escopo_vagas).length > 0 && (
                <div>
                  <span className="text-sm text-muted-foreground">
                    Escopo de vagas:
                  </span>
                  <p className="text-sm">
                    {JSON.stringify(data.escopo_vagas, null, 2)}
                  </p>
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Nova Campanha</DialogTitle>
        </DialogHeader>

        {/* Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>{activeSteps[step - 1]?.title}</span>
            <span>
              {step}/{totalSteps}
            </span>
          </div>
          <Progress value={progress} />
        </div>

        {/* Content */}
        <div className="min-h-[300px] py-4">{renderStep()}</div>

        {/* Actions */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={step === 1}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar
          </Button>

          {step < totalSteps ? (
            <Button onClick={handleNext} disabled={!canProceed()}>
              Próximo
              <ArrowRight className="h-4 w-4 ml-2" />
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
                  <Check className="h-4 w-4 mr-2" />
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
```

---

### T5: Atualizar página de campanhas (1h)

**Arquivo:** `dashboard/app/campanhas/page.tsx` (modificar)

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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Plus, MoreHorizontal, Play, Pause, Trash2 } from "lucide-react";
import { CriarCampanhaWizard } from "@/components/campanhas/criar-campanha-wizard";
import { getTipoInfo, TipoCampanha } from "@/components/campanhas/tipo-selector";

interface Campanha {
  id: string;
  nome: string;
  tipo: TipoCampanha;
  objetivo: string | null;
  pode_ofertar: boolean;
  status: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  rascunho: "bg-gray-100 text-gray-800",
  agendada: "bg-blue-100 text-blue-800",
  ativa: "bg-green-100 text-green-800",
  pausada: "bg-yellow-100 text-yellow-800",
  concluida: "bg-purple-100 text-purple-800",
};

export default function CampanhasPage() {
  const [campanhas, setCampanhas] = useState<Campanha[]>([]);
  const [loading, setLoading] = useState(true);
  const [wizardOpen, setWizardOpen] = useState(false);

  useEffect(() => {
    async function carregarCampanhas() {
      try {
        const res = await fetch("/api/campanhas");
        const data = await res.json();
        setCampanhas(data);
      } catch (error) {
        console.error("Erro ao carregar campanhas:", error);
      } finally {
        setLoading(false);
      }
    }

    carregarCampanhas();
  }, []);

  const handleStatusChange = async (id: string, novoStatus: string) => {
    try {
      await fetch(`/api/campanhas/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: novoStatus }),
      });

      setCampanhas((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: novoStatus } : c))
      );
    } catch (error) {
      console.error("Erro ao atualizar status:", error);
    }
  };

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Campanhas</h1>
          <p className="text-muted-foreground">
            Gerencie campanhas de contato com médicos
          </p>
        </div>

        <Button onClick={() => setWizardOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Campanha
        </Button>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Objetivo</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Criada em</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  Carregando...
                </TableCell>
              </TableRow>
            ) : campanhas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  Nenhuma campanha encontrada
                </TableCell>
              </TableRow>
            ) : (
              campanhas.map((campanha) => {
                const tipoInfo = getTipoInfo(campanha.tipo);
                return (
                  <TableRow key={campanha.id}>
                    <TableCell className="font-medium">
                      {campanha.nome}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {tipoInfo?.icon}
                        <span>{tipoInfo?.titulo}</span>
                        {campanha.pode_ofertar && (
                          <Badge variant="outline" className="text-xs">
                            Ofertar
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">
                      {campanha.objetivo || "-"}
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[campanha.status]}>
                        {campanha.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {new Date(campanha.created_at).toLocaleDateString("pt-BR")}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          {campanha.status === "rascunho" && (
                            <DropdownMenuItem
                              onClick={() =>
                                handleStatusChange(campanha.id, "ativa")
                              }
                            >
                              <Play className="h-4 w-4 mr-2" />
                              Ativar
                            </DropdownMenuItem>
                          )}
                          {campanha.status === "ativa" && (
                            <DropdownMenuItem
                              onClick={() =>
                                handleStatusChange(campanha.id, "pausada")
                              }
                            >
                              <Pause className="h-4 w-4 mr-2" />
                              Pausar
                            </DropdownMenuItem>
                          )}
                          {campanha.status === "pausada" && (
                            <DropdownMenuItem
                              onClick={() =>
                                handleStatusChange(campanha.id, "ativa")
                              }
                            >
                              <Play className="h-4 w-4 mr-2" />
                              Retomar
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem className="text-red-600">
                            <Trash2 className="h-4 w-4 mr-2" />
                            Excluir
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <CriarCampanhaWizard open={wizardOpen} onOpenChange={setWizardOpen} />
    </div>
  );
}
```

---

### T6: Criar testes (30min)

**Arquivo:** `dashboard/__tests__/campanhas/criar-campanha.test.tsx`

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CriarCampanhaWizard } from "@/components/campanhas/criar-campanha-wizard";

describe("CriarCampanhaWizard", () => {
  it("renders tipo selector on first step", () => {
    render(<CriarCampanhaWizard open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByText("Discovery")).toBeInTheDocument();
    expect(screen.getByText("Oferta")).toBeInTheDocument();
    expect(screen.getByText("Follow-up")).toBeInTheDocument();
  });

  it("disables next button until tipo is selected", () => {
    render(<CriarCampanhaWizard open={true} onOpenChange={vi.fn()} />);

    const nextButton = screen.getByText("Próximo");
    expect(nextButton).toBeDisabled();

    fireEvent.click(screen.getByText("Discovery"));
    expect(nextButton).not.toBeDisabled();
  });

  it("shows escopo step only for oferta tipo", async () => {
    render(<CriarCampanhaWizard open={true} onOpenChange={vi.fn()} />);

    // Select discovery
    fireEvent.click(screen.getByText("Discovery"));
    fireEvent.click(screen.getByText("Próximo"));

    // Fill nome
    fireEvent.change(screen.getByPlaceholderText(/Ex: Discovery/), {
      target: { value: "Test Campaign" },
    });
    fireEvent.click(screen.getByText("Próximo"));

    // Should skip to review (no escopo for discovery)
    fireEvent.click(screen.getByText("Próximo")); // Skip regras

    await waitFor(() => {
      expect(screen.getByText("Resumo da campanha")).toBeInTheDocument();
    });
  });

  it("requires escopo for oferta campaigns", async () => {
    render(<CriarCampanhaWizard open={true} onOpenChange={vi.fn()} />);

    // Select oferta
    fireEvent.click(screen.getByText("Oferta"));
    fireEvent.click(screen.getByText("Próximo"));

    // Fill nome
    fireEvent.change(screen.getByPlaceholderText(/Ex: Discovery/), {
      target: { value: "Test Oferta" },
    });
    fireEvent.click(screen.getByText("Próximo"));

    // Skip regras
    fireEvent.click(screen.getByText("Próximo"));

    // Should be on escopo step
    expect(
      screen.getByText(/Defina o escopo de vagas/)
    ).toBeInTheDocument();
  });
});
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Wizard de criação com 5 steps
- [ ] Seleção de tipo com cards visuais
- [ ] Editor de regras com sugestões padrão
- [ ] Editor de escopo para campanhas de oferta
- [ ] Validação de vagas em tempo real no escopo
- [ ] Listagem com novos campos (tipo, objetivo, pode_ofertar)

### UI/UX
- [ ] Progress bar mostrando step atual
- [ ] Steps condicionais (escopo só para oferta)
- [ ] Preview antes de criar
- [ ] Feedback visual de sucesso/erro

### Testes
- [ ] Testes de seleção de tipo
- [ ] Testes de navegação entre steps
- [ ] Testes de validação de campos
- [ ] Testes de criação via API

### Verificação Manual

1. **Criar campanha discovery:**
   - Selecionar tipo "Discovery"
   - Preencher nome
   - Verificar que step de escopo não aparece
   - Criar e verificar no banco

2. **Criar campanha oferta:**
   - Selecionar tipo "Oferta"
   - Preencher nome
   - Definir escopo (especialidade, período)
   - Verificar contador de vagas
   - Criar e verificar que `escopo_vagas` foi salvo

3. **Listar campanhas:**
   - Verificar que tipo aparece com ícone
   - Verificar badge "Ofertar" para campanhas de oferta

---

## Notas para Dev

1. **TypeScript strict:** Garantir que todos os tipos estão definidos
2. **Acessibilidade:** Cards devem ser navegáveis por teclado
3. **Mobile:** Wizard deve funcionar bem em telas pequenas
4. **Validação backend:** API deve validar regras (discovery não pode ter pode_ofertar)
5. **Consultar docs:** Ver `docs/best-practices/nextjs-typescript-rules.md`

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Campanhas criadas pelo wizard | > 90% |
| Erros de validação em produção | < 1% |
| Tempo de criação de campanha | < 2 min |
