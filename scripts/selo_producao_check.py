"""
Selo de Produção - 3 Checks de Validação

Sprint 18.1 P0 - Prova de soberania dos guardrails

A) Prova de bloqueio opted_out
B) Prova de reply permitido em opted_out
C) Prova de auditoria E10
"""
import asyncio
import sys
from datetime import datetime, timezone
from dataclasses import asdict

# Setup path
sys.path.insert(0, "/Users/rafaelpivovar/Documents/Projetos/whatsapp-api")

from app.services.supabase import supabase
from app.services.guardrails import (
    check_outbound_guardrails,
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
)


# Cliente de teste
CLIENTE_ID = "7aa3e833-434e-47f3-a22e-e16441f5d301"
CONVERSA_ID = "487197c2-8e17-4dbc-9ed7-6031d6f1c109"
INTERACAO_ID = 443


async def setup_opted_out():
    """Marca cliente como opted_out para teste."""
    # Verificar se doctor_state existe
    check = supabase.table("doctor_state").select("*").eq("cliente_id", CLIENTE_ID).execute()

    if check.data:
        # Salvar estado atual
        old_state = check.data[0].get("permission_state")
        # Atualizar para opted_out
        supabase.table("doctor_state").update({
            "permission_state": "opted_out"
        }).eq("cliente_id", CLIENTE_ID).execute()
        return old_state
    else:
        # Criar com opted_out
        supabase.table("doctor_state").insert({
            "cliente_id": CLIENTE_ID,
            "permission_state": "opted_out"
        }).execute()
        return None  # Não existia


def teardown_opted_out(old_state):
    """Restaura estado original."""
    if old_state is None:
        # Deletar registro criado
        supabase.table("doctor_state").delete().eq("cliente_id", CLIENTE_ID).execute()
    else:
        # Restaurar valor original
        supabase.table("doctor_state").update({
            "permission_state": old_state
        }).eq("cliente_id", CLIENTE_ID).execute()


async def check_a_bloqueio_opted_out():
    """
    Check A: Prova de bloqueio opted_out

    Contexto: Campanha tentando enviar para opted_out
    Esperado: blocked=True, block_reason=opted_out
    """
    print("\n" + "="*60)
    print("CHECK A: Prova de bloqueio opted_out")
    print("="*60)

    ctx = OutboundContext(
        cliente_id=CLIENTE_ID,
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id="teste_selo_producao",
    )

    print(f"\nContexto de envio:")
    print(f"  actor_type: {ctx.actor_type.value}")
    print(f"  channel: {ctx.channel.value}")
    print(f"  method: {ctx.method.value}")
    print(f"  is_proactive: {ctx.is_proactive}")

    result = await check_outbound_guardrails(ctx)

    print(f"\nResultado:")
    print(f"  decision: {result.decision.value}")
    print(f"  reason_code: {result.reason_code}")
    print(f"  is_blocked: {result.is_blocked}")
    print(f"  human_bypass: {result.human_bypass}")

    # Validar
    passed = result.is_blocked and result.reason_code == "opted_out"

    if passed:
        print(f"\n✅ CHECK A PASSOU: Campanha bloqueada por opted_out")
    else:
        print(f"\n❌ CHECK A FALHOU: Esperado bloqueio por opted_out")

    return passed


async def check_b_reply_permitido():
    """
    Check B: Prova de reply permitido em opted_out

    Contexto: Reply com prova de inbound válida
    Esperado: allowed (mesmo com opted_out)
    """
    print("\n" + "="*60)
    print("CHECK B: Prova de reply permitido em opted_out")
    print("="*60)

    # Prova de inbound: interação recente (simulada como agora)
    now = datetime.now(timezone.utc).isoformat()

    ctx = OutboundContext(
        cliente_id=CLIENTE_ID,
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        is_proactive=False,
        conversation_id=CONVERSA_ID,
        inbound_interaction_id=INTERACAO_ID,
        last_inbound_at=now,  # Inbound agora = válido
    )

    print(f"\nContexto de envio:")
    print(f"  actor_type: {ctx.actor_type.value}")
    print(f"  channel: {ctx.channel.value}")
    print(f"  method: {ctx.method.value}")
    print(f"  is_proactive: {ctx.is_proactive}")
    print(f"  inbound_interaction_id: {ctx.inbound_interaction_id}")
    print(f"  last_inbound_at: {ctx.last_inbound_at[:19]}...")

    result = await check_outbound_guardrails(ctx)

    print(f"\nResultado:")
    print(f"  decision: {result.decision.value}")
    print(f"  reason_code: {result.reason_code}")
    print(f"  is_allowed: {result.is_allowed}")

    # Validar
    passed = result.is_allowed and result.reason_code == "reply_to_opted_out"

    if passed:
        print(f"\n✅ CHECK B PASSOU: Reply permitido mesmo com opted_out")
    else:
        print(f"\n❌ CHECK B FALHOU: Esperado permissão com reason_code=reply_to_opted_out")
        print(f"   (reason_code obtido: {result.reason_code})")

    return passed


async def check_c_auditoria_e10():
    """
    Check C: Prova de auditoria E10

    Funções de invariantes funcionam sem erro
    """
    print("\n" + "="*60)
    print("CHECK C: Prova de auditoria E10")
    print("="*60)

    tests = []

    # C1: get_funnel_invariant_violations
    print("\nC1: get_funnel_invariant_violations(7)...")
    try:
        resp = supabase.rpc("get_funnel_invariant_violations", {"p_days": 7}).execute()
        violations = resp.data or []
        print(f"  Resultado: {len(violations)} violações encontradas")
        tests.append(("get_funnel_invariant_violations", True, None))
    except Exception as e:
        print(f"  ERRO: {e}")
        tests.append(("get_funnel_invariant_violations", False, str(e)))

    # C2: audit_outbound_coverage
    print("\nC2: audit_outbound_coverage(start, end)...")
    try:
        from datetime import timedelta
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        resp = supabase.rpc("audit_outbound_coverage", {
            "p_start": start.isoformat(),
            "p_end": end.isoformat()
        }).execute()
        coverage = resp.data or []
        print(f"  Resultado: {len(coverage)} registros de cobertura")
        if coverage:
            for c in coverage:
                print(f"    - {c.get('layer')}: {c.get('actual_count')}/{c.get('expected_count')} ({c.get('coverage_pct')}%)")
        tests.append(("audit_outbound_coverage", True, None))
    except Exception as e:
        print(f"  ERRO: {e}")
        tests.append(("audit_outbound_coverage", False, str(e)))

    # C3: data_anomalies table existe
    print("\nC3: Tabela data_anomalies acessível...")
    try:
        resp = supabase.table("data_anomalies").select("*").limit(5).execute()
        anomalies = resp.data or []
        print(f"  Resultado: {len(anomalies)} anomalias recentes")
        tests.append(("data_anomalies", True, None))
    except Exception as e:
        print(f"  ERRO: {e}")
        tests.append(("data_anomalies", False, str(e)))

    # Resumo
    passed = all(t[1] for t in tests)

    print(f"\nResumo C:")
    for name, success, error in tests:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    if passed:
        print(f"\n✅ CHECK C PASSOU: Todas as funções de auditoria funcionam")
    else:
        print(f"\n❌ CHECK C FALHOU: Algumas funções de auditoria falharam")

    return passed


async def check_evento_bloqueio():
    """Verifica se evento OUTBOUND_BLOCKED foi emitido."""
    print("\n" + "="*60)
    print("BONUS: Verificar emissão de OUTBOUND_BLOCKED")
    print("="*60)

    # Buscar evento recente
    resp = supabase.table("business_events").select("*").eq(
        "event_type", "outbound_blocked"
    ).eq(
        "cliente_id", CLIENTE_ID
    ).order(
        "ts", desc=True
    ).limit(1).execute()

    if resp.data:
        event = resp.data[0]
        print(f"\nEvento encontrado:")
        print(f"  event_type: {event['event_type']}")
        print(f"  ts: {event['ts']}")
        props = event.get("event_props", {})
        print(f"  channel: {props.get('channel')}")
        print(f"  method: {props.get('method')}")
        print(f"  actor_type: {props.get('actor_type')}")
        print(f"  block_reason: {props.get('block_reason')}")
        print(f"\n✅ BONUS: Evento OUTBOUND_BLOCKED emitido com campos de auditoria")
        return True, event
    else:
        print(f"\n⚠️  Nenhum evento OUTBOUND_BLOCKED encontrado para este cliente")
        print(f"   (pode ser deduplicação se rodou recentemente)")
        return False, None


async def main():
    print("\n" + "#"*60)
    print("# SELO DE PRODUÇÃO - Sprint 18.1 P0")
    print("# 3 Checks de Validação de Guardrails")
    print("#"*60)

    # Setup: marcar como opted_out
    print("\n[SETUP] Marcando cliente como opted_out...")
    old_state = await setup_opted_out()
    print(f"  Estado anterior: {old_state or 'não existia'}")

    try:
        # Executar checks
        result_a = await check_a_bloqueio_opted_out()
        result_b = await check_b_reply_permitido()
        result_c = await check_c_auditoria_e10()

        # Bonus: verificar evento
        result_bonus, event = await check_evento_bloqueio()

        # Resumo final
        print("\n" + "#"*60)
        print("# RESULTADO FINAL")
        print("#"*60)

        all_passed = result_a and result_b and result_c

        print(f"\n  Check A (bloqueio opted_out):      {'✅ PASSOU' if result_a else '❌ FALHOU'}")
        print(f"  Check B (reply em opted_out):      {'✅ PASSOU' if result_b else '❌ FALHOU'}")
        print(f"  Check C (auditoria E10):           {'✅ PASSOU' if result_c else '❌ FALHOU'}")
        print(f"  Bonus (evento emitido):            {'✅ SIM' if result_bonus else '⚠️  N/A'}")

        if all_passed:
            print(f"\n🎖️  SELO DE PRODUÇÃO CONCEDIDO")
            print(f"   Guardrails provados operacionais!")
        else:
            print(f"\n❌ SELO NÃO CONCEDIDO")
            print(f"   Revisar checks que falharam")

        return all_passed, event

    finally:
        # Teardown: restaurar estado
        print("\n[TEARDOWN] Restaurando estado original...")
        teardown_opted_out(old_state)
        print("  Feito!")


if __name__ == "__main__":
    result, event = asyncio.run(main())
    sys.exit(0 if result else 1)
