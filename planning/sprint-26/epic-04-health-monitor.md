# Epic 04: Health Monitor

## Objetivo

Implementar **monitoramento proativo** dos chips em producao:
- Detectar problemas antes de virarem criticos
- Alertar automaticamente
- Gerar relatorios de saude
- Sugerir acoes corretivas

## Contexto

O Health Monitor complementa o Orchestrator focando em deteccao precoce:

| Aspecto | Orchestrator | Health Monitor |
|---------|--------------|----------------|
| Foco | Acoes | Deteccao |
| Frequencia | 1 min | 5 min |
| Output | Executa | Alerta |

---

## Story 4.1: Monitor Basico

### Objetivo
Implementar verificacoes de saude.

### Implementacao

**Arquivo:** `app/services/chips/health_monitor.py`

```python
"""
Health Monitor - Monitoramento proativo de chips em producao.

Detecta:
- Taxa de resposta caindo
- Erros aumentando
- Desconexoes prolongadas
- Trust Score degradando
- Padroes suspeitos
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass

from app.services.supabase import supabase
from app.services.notificacoes import notificar_slack

logger = logging.getLogger(__name__)


@dataclass
class HealthAlert:
    """Alerta de saude detectado."""
    chip_id: str
    telefone: str
    tipo: str
    severity: str  # critical, warning, info
    message: str
    details: dict
    acao_sugerida: Optional[str] = None


class HealthMonitor:
    """Monitor de saude dos chips."""

    def __init__(self):
        self._running = False
        self.thresholds = {
            # Taxa de resposta
            "taxa_resposta_minima": 0.15,          # 15%
            "taxa_resposta_alerta": 0.25,          # 25%

            # Erros
            "erros_hora_critico": 5,
            "erros_hora_warning": 2,

            # Trust
            "trust_drop_alerta": 10,               # Queda de 10 pontos em 24h
            "trust_drop_critico": 20,              # Queda de 20 pontos

            # Conexao
            "desconexao_minutos_warning": 15,
            "desconexao_minutos_critico": 30,

            # Proporcao
            "proporcao_maxima": 4.0,               # Max 4:1 enviadas:recebidas
        }

    async def verificar_saude_pool(self) -> List[HealthAlert]:
        """
        Verifica saude de todos os chips ativos.

        Returns:
            Lista de alertas gerados
        """
        result = supabase.table("chips").select("*").in_(
            "status", ["active", "warming"]
        ).execute()

        todos_alertas = []

        for chip in result.data or []:
            alertas = await self._verificar_chip(chip)
            todos_alertas.extend(alertas)

        # Persistir alertas
        for alerta in todos_alertas:
            await self._salvar_alerta(alerta)

        return todos_alertas

    async def _verificar_chip(self, chip: Dict) -> List[HealthAlert]:
        """
        Verifica saude de um chip especifico.

        Args:
            chip: Dados do chip

        Returns:
            Lista de alertas para este chip
        """
        alertas = []

        # 1. Verificar conexao
        alerta_conexao = await self._verificar_conexao(chip)
        if alerta_conexao:
            alertas.append(alerta_conexao)

        # 2. Verificar taxa de resposta
        alerta_resposta = await self._verificar_taxa_resposta(chip)
        if alerta_resposta:
            alertas.append(alerta_resposta)

        # 3. Verificar erros
        alerta_erros = await self._verificar_erros(chip)
        if alerta_erros:
            alertas.append(alerta_erros)

        # 4. Verificar tendencia de Trust
        alerta_trust = await self._verificar_tendencia_trust(chip)
        if alerta_trust:
            alertas.append(alerta_trust)

        # 5. Verificar proporcao enviadas/recebidas
        alerta_proporcao = await self._verificar_proporcao(chip)
        if alerta_proporcao:
            alertas.append(alerta_proporcao)

        return alertas

    async def _verificar_conexao(self, chip: Dict) -> Optional[HealthAlert]:
        """Verifica status de conexao."""
        if chip["evolution_connected"]:
            return None

        # Buscar quanto tempo desconectado
        # (pelo ultimo alerta de conexao ou updated_at)
        updated = datetime.fromisoformat(chip["updated_at"].replace("Z", "+00:00"))
        minutos_desconectado = (datetime.now(timezone.utc) - updated).total_seconds() / 60

        if minutos_desconectado >= self.thresholds["desconexao_minutos_critico"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="connection_lost",
                severity="critical",
                message=f"Chip desconectado ha {int(minutos_desconectado)} minutos",
                details={"minutos": int(minutos_desconectado)},
                acao_sugerida="Verificar QR Code ou reconectar manualmente",
            )
        elif minutos_desconectado >= self.thresholds["desconexao_minutos_warning"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="connection_lost",
                severity="warning",
                message=f"Chip desconectado ha {int(minutos_desconectado)} minutos",
                details={"minutos": int(minutos_desconectado)},
            )

        return None

    async def _verificar_taxa_resposta(self, chip: Dict) -> Optional[HealthAlert]:
        """Verifica taxa de resposta."""
        taxa = float(chip.get("taxa_resposta", 0))

        # Ignorar se poucas mensagens (nao significativo)
        if chip["msgs_enviadas_total"] < 20:
            return None

        if taxa < self.thresholds["taxa_resposta_minima"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="low_response_rate",
                severity="warning",
                message=f"Taxa de resposta muito baixa: {taxa:.1%}",
                details={"taxa": taxa, "threshold": self.thresholds["taxa_resposta_minima"]},
                acao_sugerida="Reduzir velocidade de envio e revisar mensagens",
            )
        elif taxa < self.thresholds["taxa_resposta_alerta"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="low_response_rate",
                severity="info",
                message=f"Taxa de resposta abaixo do ideal: {taxa:.1%}",
                details={"taxa": taxa},
            )

        return None

    async def _verificar_erros(self, chip: Dict) -> Optional[HealthAlert]:
        """Verifica erros nas ultimas horas."""
        # Buscar erros na ultima hora
        uma_hora_atras = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        result = supabase.table("chip_interactions").select(
            "*", count="exact"
        ).eq(
            "chip_id", chip["id"]
        ).not_.is_(
            "erro_codigo", None
        ).gte(
            "created_at", uma_hora_atras
        ).execute()

        erros_hora = result.count or 0

        if erros_hora >= self.thresholds["erros_hora_critico"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="high_error_rate",
                severity="critical",
                message=f"Muitos erros na ultima hora: {erros_hora}",
                details={"erros_hora": erros_hora},
                acao_sugerida="Pausar envios e investigar causa",
            )
        elif erros_hora >= self.thresholds["erros_hora_warning"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="high_error_rate",
                severity="warning",
                message=f"Erros na ultima hora: {erros_hora}",
                details={"erros_hora": erros_hora},
            )

        return None

    async def _verificar_tendencia_trust(self, chip: Dict) -> Optional[HealthAlert]:
        """Verifica tendencia do Trust Score."""
        # Buscar score de 24h atras
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        result = supabase.table("chip_trust_history").select(
            "score"
        ).eq(
            "chip_id", chip["id"]
        ).gte(
            "recorded_at", ontem
        ).order(
            "recorded_at", desc=False
        ).limit(1).execute()

        if not result.data:
            return None

        score_ontem = result.data[0]["score"]
        score_atual = chip["trust_score"]
        queda = score_ontem - score_atual

        if queda >= self.thresholds["trust_drop_critico"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="trust_drop",
                severity="critical",
                message=f"Trust Score caiu {queda} pontos em 24h ({score_ontem} -> {score_atual})",
                details={"queda": queda, "score_anterior": score_ontem, "score_atual": score_atual},
                acao_sugerida="Pausar prospeccao e investigar causa",
            )
        elif queda >= self.thresholds["trust_drop_alerta"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="trust_drop",
                severity="warning",
                message=f"Trust Score caiu {queda} pontos em 24h",
                details={"queda": queda, "score_anterior": score_ontem, "score_atual": score_atual},
            )

        return None

    async def _verificar_proporcao(self, chip: Dict) -> Optional[HealthAlert]:
        """Verifica proporcao enviadas/recebidas."""
        enviadas = chip["msgs_enviadas_total"]
        recebidas = chip["msgs_recebidas_total"]

        if recebidas == 0:
            if enviadas > 50:
                return HealthAlert(
                    chip_id=chip["id"],
                    telefone=chip["telefone"],
                    tipo="bad_ratio",
                    severity="warning",
                    message=f"Nenhuma resposta recebida apos {enviadas} mensagens",
                    details={"enviadas": enviadas, "recebidas": 0},
                    acao_sugerida="Verificar qualidade das mensagens",
                )
            return None

        proporcao = enviadas / recebidas

        if proporcao > self.thresholds["proporcao_maxima"]:
            return HealthAlert(
                chip_id=chip["id"],
                telefone=chip["telefone"],
                tipo="bad_ratio",
                severity="warning",
                message=f"Proporcao enviadas/recebidas muito alta: {proporcao:.1f}:1",
                details={"proporcao": proporcao, "enviadas": enviadas, "recebidas": recebidas},
                acao_sugerida="Reduzir volume de prospeccao",
            )

        return None

    async def _salvar_alerta(self, alerta: HealthAlert):
        """Salva alerta no banco."""
        # Verificar se alerta similar ja existe (nao resolvido)
        existing = supabase.table("chip_alerts").select("id").eq(
            "chip_id", alerta.chip_id
        ).eq(
            "tipo", alerta.tipo
        ).eq(
            "resolved", False
        ).execute()

        if existing.data:
            # Ja existe alerta nao resolvido, apenas atualizar
            supabase.table("chip_alerts").update({
                "severity": alerta.severity,
                "message": alerta.message,
                "details": alerta.details,
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            # Criar novo alerta
            supabase.table("chip_alerts").insert({
                "chip_id": alerta.chip_id,
                "severity": alerta.severity,
                "tipo": alerta.tipo,
                "message": alerta.message,
                "details": alerta.details,
            }).execute()

    async def gerar_relatorio(self) -> Dict:
        """
        Gera relatorio de saude do pool.

        Returns:
            {
                "timestamp": "...",
                "resumo": {
                    "total_chips": N,
                    "saudaveis": N,
                    "atencao": N,
                    "criticos": N
                },
                "alertas_ativos": [...],
                "metricas": {
                    "trust_medio": N,
                    "taxa_resposta_media": N,
                    "msgs_hoje": N
                }
            }
        """
        # Buscar chips
        result = supabase.table("chips").select("*").in_(
            "status", ["active", "warming"]
        ).execute()

        chips = result.data or []

        # Classificar
        saudaveis = [c for c in chips if c["trust_score"] >= 80 and c["evolution_connected"]]
        atencao = [c for c in chips if 60 <= c["trust_score"] < 80 or not c["evolution_connected"]]
        criticos = [c for c in chips if c["trust_score"] < 60]

        # Buscar alertas nao resolvidos
        alertas = supabase.table("chip_alerts").select("*").eq(
            "resolved", False
        ).order("severity").execute()

        # Calcular metricas
        trust_medio = sum(c["trust_score"] for c in chips) / len(chips) if chips else 0
        taxa_media = sum(float(c.get("taxa_resposta", 0)) for c in chips) / len(chips) if chips else 0
        msgs_hoje = sum(c["msgs_enviadas_hoje"] for c in chips)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resumo": {
                "total_chips": len(chips),
                "saudaveis": len(saudaveis),
                "atencao": len(atencao),
                "criticos": len(criticos),
            },
            "alertas_ativos": alertas.data or [],
            "metricas": {
                "trust_medio": round(trust_medio, 1),
                "taxa_resposta_media": round(taxa_media, 3),
                "msgs_hoje": msgs_hoje,
            },
            "chips_criticos": [
                {"telefone": c["telefone"], "trust": c["trust_score"]}
                for c in criticos
            ],
        }

    async def iniciar(self, intervalo_segundos: int = 300):
        """Inicia monitoramento continuo (default 5 min)."""
        self._running = True
        logger.info(f"[HealthMonitor] Iniciando com intervalo de {intervalo_segundos}s")

        while self._running:
            try:
                alertas = await self.verificar_saude_pool()

                # Notificar alertas criticos
                criticos = [a for a in alertas if a.severity == "critical"]
                if criticos:
                    msg = f":rotating_light: *{len(criticos)} alerta(s) critico(s)*\n\n"
                    for a in criticos[:5]:  # Max 5 por notificacao
                        msg += f"*{a.telefone}*: {a.message}\n"
                        if a.acao_sugerida:
                            msg += f"  _Acao: {a.acao_sugerida}_\n"

                    await notificar_slack(msg, canal="alertas")

                # Log resumo
                relatorio = await self.gerar_relatorio()
                logger.info(
                    f"[HealthMonitor] Pool: "
                    f"saudaveis={relatorio['resumo']['saudaveis']}, "
                    f"atencao={relatorio['resumo']['atencao']}, "
                    f"criticos={relatorio['resumo']['criticos']}, "
                    f"alertas={len(relatorio['alertas_ativos'])}"
                )

            except Exception as e:
                logger.error(f"[HealthMonitor] Erro: {e}")

            await asyncio.sleep(intervalo_segundos)

    def parar(self):
        """Para o monitor."""
        self._running = False
        logger.info("[HealthMonitor] Parando...")


# Singleton
health_monitor = HealthMonitor()
```

### DoD

- [ ] Verificacoes implementadas
- [ ] Alertas sendo criados
- [ ] Loop funcionando

---

## Story 4.2: Relatorio Periodico

### Objetivo
Enviar relatorio diario de saude.

### Implementacao

```python
async def enviar_relatorio_diario():
    """
    Envia relatorio diario de saude do pool.

    Roda todos os dias as 9h.
    """
    relatorio = await health_monitor.gerar_relatorio()

    msg = f":bar_chart: *Relatorio Diario - Pool de Chips*\n\n"
    msg += f"*Resumo:*\n"
    msg += f"- Total: {relatorio['resumo']['total_chips']} chips\n"
    msg += f"- Saudaveis: {relatorio['resumo']['saudaveis']}\n"
    msg += f"- Atencao: {relatorio['resumo']['atencao']}\n"
    msg += f"- Criticos: {relatorio['resumo']['criticos']}\n\n"

    msg += f"*Metricas:*\n"
    msg += f"- Trust medio: {relatorio['metricas']['trust_medio']}\n"
    msg += f"- Taxa resposta media: {relatorio['metricas']['taxa_resposta_media']:.1%}\n"
    msg += f"- Msgs enviadas hoje: {relatorio['metricas']['msgs_hoje']}\n\n"

    if relatorio['chips_criticos']:
        msg += f"*Chips criticos:*\n"
        for c in relatorio['chips_criticos']:
            msg += f"- `{c['telefone']}` (Trust: {c['trust']})\n"

    if relatorio['alertas_ativos']:
        msg += f"\n*Alertas ativos:* {len(relatorio['alertas_ativos'])}"

    await notificar_slack(msg, canal="operacoes")

# scheduler.add_job(enviar_relatorio_diario, 'cron', hour=9)
```

### DoD

- [ ] Relatorio funcionando
- [ ] Envio no Slack

---

## Checklist do Epico

- [ ] **E04.1** - Monitor basico
- [ ] **E04.2** - Relatorio periodico
- [ ] Testes de integracao
- [ ] Documentacao

---

## Diagrama: Verificacoes do Health Monitor

```
┌─────────────────────────────────────────────────────────────────┐
│                    HEALTH MONITOR CHECKS                         │
│                      (a cada 5 min)                              │
└─────────────────────────────────────────────────────────────────┘

Para cada chip ativo:

  ┌─────────────────────────────────────────────────────────────┐
  │ 1. CONEXAO                                                  │
  ├─────────────────────────────────────────────────────────────┤
  │ evolution_connected = false?                                │
  │                                                             │
  │ > 30 min → CRITICAL: "Desconectado ha X minutos"           │
  │ > 15 min → WARNING: "Desconectado ha X minutos"            │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ 2. TAXA DE RESPOSTA                                         │
  ├─────────────────────────────────────────────────────────────┤
  │ taxa_resposta < threshold? (min 20 msgs)                    │
  │                                                             │
  │ < 15% → WARNING: "Taxa muito baixa"                         │
  │ < 25% → INFO: "Taxa abaixo do ideal"                        │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ 3. ERROS                                                    │
  ├─────────────────────────────────────────────────────────────┤
  │ erros na ultima hora?                                       │
  │                                                             │
  │ >= 5 erros → CRITICAL: "Muitos erros"                       │
  │ >= 2 erros → WARNING: "Erros detectados"                    │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ 4. TENDENCIA TRUST                                          │
  ├─────────────────────────────────────────────────────────────┤
  │ Trust caiu nas ultimas 24h?                                 │
  │                                                             │
  │ >= 20 pontos → CRITICAL: "Trust caiu drasticamente"         │
  │ >= 10 pontos → WARNING: "Trust caindo"                      │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ 5. PROPORCAO                                                │
  ├─────────────────────────────────────────────────────────────┤
  │ enviadas/recebidas > 4:1?                                   │
  │                                                             │
  │ > 4:1 → WARNING: "Proporcao muito alta"                     │
  │ 0 recebidas + 50 enviadas → WARNING: "Sem respostas"        │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │                    RESULTADO                                │
  ├─────────────────────────────────────────────────────────────┤
  │ Alertas CRITICAL → Notifica Slack #alertas                  │
  │ Alertas WARNING  → Salva no banco                           │
  │ Alertas INFO     → Salva no banco                           │
  └─────────────────────────────────────────────────────────────┘
```
