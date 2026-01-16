# E20 - Toggle Modo Piloto no Dashboard

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 5 - Dashboard
**Dependências:** E03 (Modo Piloto - Backend)
**Estimativa:** 2h

---

## Objetivo

Adicionar toggle no dashboard para ativar/desativar **Modo Piloto** - flag que controla se Julia age autonomamente ou apenas responde comandos.

---

## Contexto

O backend (E03) implementa:
- Flag `PILOT_MODE` em config
- Guard decorators para funções autônomas
- Endpoint para consultar status

Falta interface visual para gestores controlarem.

---

## Impacto do Modo Piloto

| Funcionalidade | Piloto ON | Piloto OFF |
|----------------|-----------|------------|
| Campanhas manuais | Funciona | Funciona |
| Respostas a médicos | Funciona | Funciona |
| Canal de ajuda | Funciona | Funciona |
| Comandos Slack | Funciona | Funciona |
| **Discovery automático** | Desabilitado | Funciona |
| **Oferta automática** | Desabilitado | Funciona |
| **Reativação automática** | Desabilitado | Funciona |
| **Feedback automático** | Desabilitado | Funciona |

---

## Tasks

### T1: Criar componente de configuração do sistema (1h)

**Arquivo:** `dashboard/app/sistema/page.tsx`

```tsx
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
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  Shield,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
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
          ? "Julia não executará ações autônomas."
          : "Julia agora age autonomamente!",
      });

      setConfirmDialog(null);
      carregarStatus();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erro",
        description: "Não foi possível alterar o modo piloto.",
      });
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center py-8">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Sistema</h1>
        <p className="text-muted-foreground">
          Configurações e controles do sistema Julia
        </p>
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
                Julia está em modo piloto. Ações autônomas estão desabilitadas.
                Ela só responde quando acionada por campanhas manuais ou mensagens
                de médicos.
              </p>
            </div>
          ) : (
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-green-800 mb-2">
                <Zap className="h-5 w-5" />
                <span className="font-medium">Julia autônoma</span>
              </div>
              <p className="text-sm text-green-700">
                Julia está operando de forma autônoma. Ela identifica oportunidades
                e age proativamente conforme as regras configuradas.
              </p>
            </div>
          )}

          {/* Status das features autônomas */}
          <div className="grid grid-cols-2 gap-4 pt-4">
            <FeatureStatus
              title="Discovery Automático"
              description="Conhecer médicos não-enriquecidos"
              enabled={status?.autonomous_features.discovery_automatico || false}
            />
            <FeatureStatus
              title="Oferta Automática"
              description="Ofertar vagas com furo de escala"
              enabled={status?.autonomous_features.oferta_automatica || false}
            />
            <FeatureStatus
              title="Reativação Automática"
              description="Retomar contato com inativos"
              enabled={status?.autonomous_features.reativacao_automatica || false}
            />
            <FeatureStatus
              title="Feedback Automático"
              description="Pedir feedback pós-plantão"
              enabled={status?.autonomous_features.feedback_automatico || false}
            />
          </div>

          {/* Última alteração */}
          {status?.last_changed_at && (
            <p className="text-xs text-muted-foreground pt-4">
              Última alteração: {new Date(status.last_changed_at).toLocaleString("pt-BR")}
              {status.last_changed_by && ` por ${status.last_changed_by}`}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Outros cards de configuração */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Rate Limiting</CardTitle>
            <CardDescription>Limites de envio de mensagens</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Mensagens por hora</span>
                <span className="font-medium">20</span>
              </div>
              <div className="flex justify-between">
                <span>Mensagens por dia</span>
                <span className="font-medium">100</span>
              </div>
              <div className="flex justify-between">
                <span>Intervalo entre mensagens</span>
                <span className="font-medium">45-180s</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Horário de Operação</CardTitle>
            <CardDescription>Quando Julia pode enviar mensagens</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Horário</span>
                <span className="font-medium">08h às 20h</span>
              </div>
              <div className="flex justify-between">
                <span>Dias</span>
                <span className="font-medium">Segunda a Sexta</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dialogs de confirmação */}
      <AlertDialog
        open={confirmDialog === "enable"}
        onOpenChange={() => setConfirmDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ativar Modo Piloto?</AlertDialogTitle>
            <AlertDialogDescription>
              Julia deixará de agir autonomamente. As seguintes funcionalidades
              serão desabilitadas:
              <ul className="list-disc list-inside mt-2">
                <li>Discovery automático</li>
                <li>Oferta automática por furo de escala</li>
                <li>Reativação automática</li>
                <li>Feedback automático</li>
              </ul>
              <br />
              Julia ainda responderá mensagens de médicos e campanhas manuais.
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
            <AlertDialogDescription>
              <div className="flex items-center gap-2 text-yellow-600 mb-4">
                <AlertTriangle className="h-5 w-5" />
                <span className="font-medium">Atenção: ação significativa</span>
              </div>
              Julia passará a agir autonomamente:
              <ul className="list-disc list-inside mt-2">
                <li>Iniciará Discovery com médicos não-enriquecidos</li>
                <li>Ofertará vagas quando houver furo de escala</li>
                <li>Reativará médicos inativos</li>
                <li>Pedirá feedback após plantões</li>
              </ul>
              <br />
              Certifique-se de que as configurações estão corretas antes de prosseguir.
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
```

---

### T2: Criar API routes (30min)

**Arquivo:** `dashboard/app/api/sistema/status/route.ts`

```tsx
import { NextResponse } from "next/server";

export async function GET() {
  try {
    // Chamar backend Python para obter status
    const res = await fetch(`${process.env.API_URL}/sistema/status`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET}`,
      },
    });

    if (!res.ok) throw new Error("Erro ao buscar status");

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    // Fallback se backend não disponível
    return NextResponse.json({
      pilot_mode: true,
      autonomous_features: {
        discovery_automatico: false,
        oferta_automatica: false,
        reativacao_automatica: false,
        feedback_automatico: false,
      },
    });
  }
}
```

**Arquivo:** `dashboard/app/api/sistema/pilot-mode/route.ts`

```tsx
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies });

  // Verificar autenticação e permissão (admin)
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  // Verificar role admin
  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  if (profile?.role !== "admin") {
    return NextResponse.json(
      { error: "Permissão negada. Apenas admins podem alterar." },
      { status: 403 }
    );
  }

  const body = await request.json();
  const { pilot_mode } = body;

  try {
    // Chamar backend Python para alterar
    const res = await fetch(`${process.env.API_URL}/sistema/pilot-mode`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.API_SECRET}`,
      },
      body: JSON.stringify({
        pilot_mode,
        changed_by: user.email,
      }),
    });

    if (!res.ok) throw new Error("Erro ao alterar");

    const data = await res.json();

    // Log de auditoria
    await supabase.from("audit_log").insert({
      user_id: user.id,
      action: pilot_mode ? "enable_pilot_mode" : "disable_pilot_mode",
      resource: "sistema",
      details: { pilot_mode },
    });

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Erro ao alterar modo piloto" },
      { status: 500 }
    );
  }
}
```

---

### T3: Criar endpoint no backend Python (30min)

**Arquivo:** `app/api/routes/sistema.py`

```python
"""
Endpoints de configuração do sistema.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.core.logging import get_logger
from app.services.supabase import supabase
from datetime import datetime

router = APIRouter(prefix="/sistema", tags=["sistema"])
logger = get_logger(__name__)


class StatusResponse(BaseModel):
    pilot_mode: bool
    autonomous_features: dict


class PilotModeRequest(BaseModel):
    pilot_mode: bool
    changed_by: str | None = None


@router.get("/status", response_model=StatusResponse)
async def get_sistema_status():
    """
    Retorna status atual do sistema.
    """
    return StatusResponse(
        pilot_mode=settings.is_pilot_mode,
        autonomous_features=settings.autonomous_features_status
    )


@router.post("/pilot-mode")
async def set_pilot_mode(request: PilotModeRequest):
    """
    Altera modo piloto.

    NOTA: Esta implementação usa banco de dados para persistir.
    Em produção, considerar usar env var via Railway ou similar.
    """
    try:
        # Salvar em tabela de configuração
        supabase.table("system_config").upsert({
            "key": "PILOT_MODE",
            "value": str(request.pilot_mode).lower(),
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": request.changed_by
        }, on_conflict="key").execute()

        # Atualizar settings em memória
        settings.PILOT_MODE = request.pilot_mode

        logger.info(
            f"Modo piloto alterado para {request.pilot_mode} "
            f"por {request.changed_by}"
        )

        return {
            "success": True,
            "pilot_mode": request.pilot_mode,
            "autonomous_features": settings.autonomous_features_status
        }

    except Exception as e:
        logger.error(f"Erro ao alterar modo piloto: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Página de sistema no dashboard
- [ ] Toggle visual para modo piloto
- [ ] Confirmação antes de alterar
- [ ] Status das features autônomas
- [ ] Persistência da configuração
- [ ] Log de auditoria

### Segurança
- [ ] Apenas admins podem alterar
- [ ] Confirmação explícita para desativar piloto
- [ ] Log de quem alterou e quando

### Testes
- [ ] Testes de renderização
- [ ] Testes de permissão
- [ ] Testes de toggle

### Verificação Manual

1. **Verificar status inicial:**
   - Acessar /sistema
   - Verificar que mostra status correto
   - Features autônomas devem refletir PILOT_MODE

2. **Ativar modo piloto:**
   - Clicar no switch
   - Confirmar no dialog
   - Verificar que features ficam desabilitadas

3. **Desativar modo piloto:**
   - Clicar no switch
   - Verificar warning no dialog
   - Confirmar e verificar features habilitadas

4. **Verificar persistência:**
   - Alterar modo piloto
   - Fazer deploy/restart
   - Verificar que configuração persiste

---

## Notas para Dev

1. **Persistência:** Usar tabela `system_config` ou env var via Railway
2. **Recarregamento:** Settings em memória precisam ser atualizados
3. **Auditoria:** Sempre logar quem alterou e quando
4. **RBAC:** Verificar role admin antes de permitir alteração

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Alterações via dashboard | > 80% |
| Tempo para alteração | < 5s |
| Erros de permissão | 0 (bem documentado) |
