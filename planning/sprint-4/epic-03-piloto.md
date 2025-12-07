# Epic 3: Execução do Piloto

## Objetivo

> **Executar piloto controlado com 100 médicos e coletar resultados.**

---

## Stories

---

# S4.E3.1 - Selecionar 100 médicos piloto

## Objetivo

> **Escolher 100 médicos ideais para o piloto inicial.**

**Resultado esperado:** Lista de 100 médicos selecionados e marcados no banco.

## Contexto

Critérios de seleção:
- Anestesiologistas (especialidade foco)
- Com CRM válido
- Telefone válido (formato correto)
- Não fez opt-out anteriormente
- Preferencialmente na região do ABC/SP

## Tarefas

### 1. Query de seleção

```python
# scripts/selecionar_piloto.py

from app.core.supabase import supabase

def selecionar_medicos_piloto(quantidade: int = 100) -> list:
    """
    Seleciona médicos para piloto usando critérios definidos.

    Prioridade:
    1. Anestesiologistas com CRM
    2. Na região do ABC/SP
    3. Telefone válido
    4. Não optout
    """
    # Buscar especialidade anestesiologia
    especialidade = (
        supabase.table("especialidades")
        .select("id")
        .eq("nome", "Anestesiologia")
        .single()
        .execute()
    ).data

    # Buscar médicos elegíveis
    medicos = (
        supabase.table("clientes")
        .select("*")
        .eq("especialidade_id", especialidade["id"])
        .not_.is_("crm", "null")
        .not_.is_("telefone", "null")
        .neq("status", "optout")
        .limit(quantidade * 2)  # Buscar mais para filtrar
        .execute()
    ).data

    # Filtrar telefones válidos
    import re
    def telefone_valido(tel):
        if not tel:
            return False
        # Formato: +5511999999999
        return bool(re.match(r'^\+55\d{10,11}$', tel))

    medicos_validos = [m for m in medicos if telefone_valido(m.get("telefone"))]

    # Priorizar região ABC (DDDs 11)
    def prioridade(m):
        tel = m.get("telefone", "")
        if tel.startswith("+5511"):
            return 0  # Alta prioridade
        return 1

    medicos_ordenados = sorted(medicos_validos, key=prioridade)

    return medicos_ordenados[:quantidade]
```

### 2. Marcar médicos como piloto

```python
def marcar_como_piloto(medico_ids: list) -> int:
    """Marca médicos selecionados como parte do piloto."""
    # Adicionar tag de piloto
    for medico_id in medico_ids:
        supabase.table("clientes").update({
            "tags": supabase.rpc("array_append", {
                "arr": "tags",
                "elem": "piloto_v1"
            }),
            "piloto_selecionado_em": datetime.utcnow().isoformat()
        }).eq("id", medico_id).execute()

    return len(medico_ids)


def executar_selecao():
    """Script principal de seleção."""
    print("Selecionando médicos para piloto...")

    medicos = selecionar_medicos_piloto(100)
    print(f"Encontrados {len(medicos)} médicos elegíveis")

    # Mostrar resumo
    print("\nResumo da seleção:")
    print(f"- Total: {len(medicos)}")
    print(f"- Com CRM: {len([m for m in medicos if m.get('crm')])}")
    print(f"- Região 11: {len([m for m in medicos if m.get('telefone', '').startswith('+5511')])}")

    # Confirmar
    confirmacao = input("\nConfirmar seleção? (s/n): ")
    if confirmacao.lower() == "s":
        ids = [m["id"] for m in medicos]
        total = marcar_como_piloto(ids)
        print(f"✅ {total} médicos marcados como piloto")
    else:
        print("Cancelado")


if __name__ == "__main__":
    executar_selecao()
```

### 3. Validar seleção

```python
def validar_selecao_piloto() -> dict:
    """Valida que seleção está correta."""
    piloto = (
        supabase.table("clientes")
        .select("*")
        .contains("tags", ["piloto_v1"])
        .execute()
    ).data

    validacao = {
        "total": len(piloto),
        "com_crm": len([m for m in piloto if m.get("crm")]),
        "com_telefone": len([m for m in piloto if m.get("telefone")]),
        "problemas": []
    }

    # Verificar problemas
    for m in piloto:
        if not m.get("telefone"):
            validacao["problemas"].append(f"{m['id']}: sem telefone")
        if m.get("status") == "optout":
            validacao["problemas"].append(f"{m['id']}: fez optout")

    return validacao
```

## DoD

- [x] Query de seleção implementada
- [x] Critérios de seleção aplicados
- [x] 100 médicos selecionados
- [x] Médicos marcados com tag `piloto_v1`
- [x] Validação confirma seleção correta

---

# S4.E3.2 - Configurar rate limiting para piloto

## Objetivo

> **Ajustar rate limiting para fase de piloto.**

**Resultado esperado:** Envio controlado respeitando limites do WhatsApp.

## Contexto

Para piloto, ser mais conservador:
- Máximo 50 primeiros contatos por dia
- Intervalo de 5 minutos entre cada
- Só em horário comercial (8h-18h)

## Tarefas

### 1. Configurar limites de piloto

```python
# app/core/config.py (adicionar)

class PilotoConfig:
    """Configurações específicas do piloto."""

    # Limites de envio
    MAX_PRIMEIROS_CONTATOS_DIA = 50
    INTERVALO_ENTRE_ENVIOS_SEGUNDOS = 300  # 5 minutos

    # Horário de envio
    HORA_INICIO = 8
    HORA_FIM = 18

    # Rate limiting de respostas (mais conservador)
    MAX_RESPOSTAS_HORA = 15
    MAX_RESPOSTAS_DIA = 80
```

### 2. Implementar controle de envio

```python
# app/services/campanha.py

from datetime import datetime, timedelta

class ControladorEnvio:
    """Controla rate limiting de envios."""

    async def pode_enviar_primeiro_contato(self) -> bool:
        """Verifica se pode enviar primeiro contato agora."""
        agora = datetime.now()

        # Verificar horário
        if agora.hour < PilotoConfig.HORA_INICIO or agora.hour >= PilotoConfig.HORA_FIM:
            return False

        # Verificar dia da semana (seg-sex)
        if agora.weekday() >= 5:
            return False

        # Contar envios do dia
        inicio_dia = agora.replace(hour=0, minute=0, second=0).isoformat()
        envios_hoje = (
            supabase.table("envios_campanha")
            .select("id", count="exact")
            .eq("tipo", "primeiro_contato")
            .gte("created_at", inicio_dia)
            .execute()
        ).count

        if envios_hoje >= PilotoConfig.MAX_PRIMEIROS_CONTATOS_DIA:
            return False

        # Verificar último envio
        ultimo = (
            supabase.table("envios_campanha")
            .select("created_at")
            .eq("tipo", "primeiro_contato")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data

        if ultimo:
            ultimo_dt = datetime.fromisoformat(ultimo[0]["created_at"])
            diferenca = (agora - ultimo_dt).total_seconds()
            if diferenca < PilotoConfig.INTERVALO_ENTRE_ENVIOS_SEGUNDOS:
                return False

        return True

    async def proximo_horario_disponivel(self) -> datetime:
        """Retorna próximo horário disponível para envio."""
        agora = datetime.now()

        # Se fora do horário, ir para próximo dia útil às 8h
        if agora.hour >= PilotoConfig.HORA_FIM:
            proximo = agora + timedelta(days=1)
            proximo = proximo.replace(hour=PilotoConfig.HORA_INICIO, minute=0, second=0)
        elif agora.hour < PilotoConfig.HORA_INICIO:
            proximo = agora.replace(hour=PilotoConfig.HORA_INICIO, minute=0, second=0)
        else:
            proximo = agora + timedelta(seconds=PilotoConfig.INTERVALO_ENTRE_ENVIOS_SEGUNDOS)

        # Pular fim de semana
        while proximo.weekday() >= 5:
            proximo += timedelta(days=1)
            proximo = proximo.replace(hour=PilotoConfig.HORA_INICIO, minute=0, second=0)

        return proximo


controlador_envio = ControladorEnvio()
```

## DoD

- [x] Configurações de piloto definidas
- [x] Controle de horário funciona
- [x] Limite diário de 50 primeiros contatos
- [x] Intervalo de 5 minutos entre envios
- [x] Função de próximo horário disponível

---

# S4.E3.3 - Criar campanha de primeiro contato

## Objetivo

> **Criar mensagem e fluxo de primeiro contato com médicos.**

**Resultado esperado:** Campanha pronta para execução com mensagem de abertura.

## Tarefas

### 1. Definir mensagem de abertura

```python
# app/templates/mensagens.py

MENSAGEM_PRIMEIRO_CONTATO = """Oi Dr(a) {nome}! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas aqui no ABC

Vi que vc é {especialidade}, certo? Temos umas vagas bem interessantes essa semana

Posso te contar mais?"""

def formatar_primeiro_contato(medico: dict) -> str:
    """Formata mensagem de primeiro contato."""
    nome = medico.get("primeiro_nome", "")
    especialidade = medico.get("especialidade_nome", "médico")

    return MENSAGEM_PRIMEIRO_CONTATO.format(
        nome=nome,
        especialidade=especialidade.lower()
    )
```

### 2. Criar estrutura da campanha

```python
# app/services/campanha.py (adicionar)

async def criar_campanha_piloto() -> dict:
    """Cria campanha de primeiro contato para piloto."""

    # Buscar médicos do piloto que ainda não foram contactados
    medicos_piloto = (
        supabase.table("clientes")
        .select("id")
        .contains("tags", ["piloto_v1"])
        .is_("primeiro_contato_em", "null")
        .execute()
    ).data

    campanha = (
        supabase.table("campanhas")
        .insert({
            "nome": "Piloto V1 - Primeiro Contato",
            "tipo": "primeiro_contato",
            "status": "ativa",
            "total_destinatarios": len(medicos_piloto),
            "mensagem_template": MENSAGEM_PRIMEIRO_CONTATO,
            "config": {
                "piloto": True,
                "max_por_dia": PilotoConfig.MAX_PRIMEIROS_CONTATOS_DIA,
                "intervalo_segundos": PilotoConfig.INTERVALO_ENTRE_ENVIOS_SEGUNDOS
            }
        })
        .execute()
    ).data[0]

    # Criar envios pendentes
    for medico in medicos_piloto:
        supabase.table("envios_campanha").insert({
            "campanha_id": campanha["id"],
            "cliente_id": medico["id"],
            "status": "pendente",
            "tipo": "primeiro_contato"
        }).execute()

    return campanha
```

### 3. Implementar envio da campanha

```python
async def executar_campanha(campanha_id: str):
    """
    Executa campanha respeitando rate limiting.

    Processa um envio por vez, aguardando intervalo.
    """
    while True:
        # Verificar se pode enviar
        if not await controlador_envio.pode_enviar_primeiro_contato():
            proximo = await controlador_envio.proximo_horario_disponivel()
            logger.info(f"Aguardando próximo horário: {proximo}")
            await asyncio.sleep(60)  # Checar a cada minuto
            continue

        # Buscar próximo envio pendente
        envio = (
            supabase.table("envios_campanha")
            .select("*, clientes(*)")
            .eq("campanha_id", campanha_id)
            .eq("status", "pendente")
            .order("created_at")
            .limit(1)
            .execute()
        ).data

        if not envio:
            logger.info("Campanha concluída - todos enviados")
            break

        envio = envio[0]
        medico = envio["clientes"]

        try:
            # Formatar e enviar mensagem
            mensagem = formatar_primeiro_contato(medico)
            await whatsapp_service.enviar_com_digitacao(
                telefone=medico["telefone"],
                texto=mensagem
            )

            # Atualizar envio
            supabase.table("envios_campanha").update({
                "status": "enviado",
                "enviado_em": datetime.utcnow().isoformat()
            }).eq("id", envio["id"]).execute()

            # Marcar médico
            supabase.table("clientes").update({
                "primeiro_contato_em": datetime.utcnow().isoformat()
            }).eq("id", medico["id"]).execute()

            logger.info(f"Primeiro contato enviado para {medico['primeiro_nome']}")

        except Exception as e:
            logger.error(f"Erro ao enviar para {medico['id']}: {e}")
            supabase.table("envios_campanha").update({
                "status": "erro",
                "erro": str(e)
            }).eq("id", envio["id"]).execute()

        # Aguardar intervalo
        await asyncio.sleep(PilotoConfig.INTERVALO_ENTRE_ENVIOS_SEGUNDOS)
```

## DoD

- [x] Mensagem de primeiro contato definida
- [x] Campanha criada no banco
- [x] Envios agendados para cada médico
- [x] Executor respeita rate limiting
- [x] Logs de cada envio

---

# S4.E3.4 - Executar piloto com monitoramento

## Objetivo

> **Rodar o piloto acompanhando métricas em tempo real.**

**Resultado esperado:** 100 médicos contactados com métricas coletadas.

## Tarefas

### 1. Script de execução do piloto

```python
# scripts/executar_piloto.py

import asyncio
from datetime import datetime
from app.services.campanha import criar_campanha_piloto, executar_campanha
from app.services.alertas import verificar_alertas

async def main():
    """Executa piloto completo."""
    print("=" * 50)
    print("PILOTO JÚLIA V1")
    print("=" * 50)
    print(f"Início: {datetime.now()}")

    # Criar campanha
    campanha = await criar_campanha_piloto()
    print(f"\nCampanha criada: {campanha['id']}")
    print(f"Total destinatários: {campanha['total_destinatarios']}")

    # Confirmar
    confirmacao = input("\nIniciar envios? (s/n): ")
    if confirmacao.lower() != "s":
        print("Cancelado")
        return

    # Executar em background
    print("\nIniciando envios...")
    print("(Pressione Ctrl+C para pausar)\n")

    try:
        await executar_campanha(campanha["id"])
    except KeyboardInterrupt:
        print("\n\nPausado pelo usuário")

    # Resumo
    print("\n" + "=" * 50)
    print("RESUMO")
    print("=" * 50)
    await mostrar_resumo_piloto(campanha["id"])


async def mostrar_resumo_piloto(campanha_id: str):
    """Mostra resumo do status do piloto."""
    envios = (
        supabase.table("envios_campanha")
        .select("status")
        .eq("campanha_id", campanha_id)
        .execute()
    ).data

    por_status = {}
    for e in envios:
        status = e["status"]
        por_status[status] = por_status.get(status, 0) + 1

    print(f"Total: {len(envios)}")
    for status, qtd in por_status.items():
        print(f"- {status}: {qtd}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Dashboard de monitoramento em tempo real

```python
# app/routes/piloto.py

from fastapi import APIRouter

router = APIRouter(prefix="/piloto", tags=["piloto"])

@router.get("/status")
async def status_piloto():
    """Retorna status atual do piloto."""
    # Buscar campanha ativa
    campanha = (
        supabase.table("campanhas")
        .select("*")
        .eq("tipo", "primeiro_contato")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data

    if not campanha:
        return {"status": "sem_campanha"}

    campanha = campanha[0]

    # Contar envios
    envios = (
        supabase.table("envios_campanha")
        .select("status")
        .eq("campanha_id", campanha["id"])
        .execute()
    ).data

    enviados = len([e for e in envios if e["status"] == "enviado"])
    pendentes = len([e for e in envios if e["status"] == "pendente"])
    erros = len([e for e in envios if e["status"] == "erro"])

    # Contar respostas
    medicos_piloto = (
        supabase.table("clientes")
        .select("id")
        .contains("tags", ["piloto_v1"])
        .execute()
    ).data
    medico_ids = [m["id"] for m in medicos_piloto]

    conversas = (
        supabase.table("conversations")
        .select("id, cliente_id")
        .in_("cliente_id", medico_ids)
        .execute()
    ).data

    responderam = len(set(c["cliente_id"] for c in conversas))

    return {
        "campanha_id": campanha["id"],
        "status": campanha["status"],
        "envios": {
            "total": len(envios),
            "enviados": enviados,
            "pendentes": pendentes,
            "erros": erros
        },
        "metricas": {
            "responderam": responderam,
            "taxa_resposta": responderam / enviados if enviados > 0 else 0
        }
    }
```

### 3. Checklist de monitoramento

```markdown
## Checklist Diário do Piloto

### Manhã (8h)
- [ ] Verificar status da campanha
- [ ] Checar alertas do Slack
- [ ] Revisar handoffs pendentes
- [ ] Verificar erros de envio

### Tarde (14h)
- [ ] Atualizar métricas no dashboard
- [ ] Avaliar 5 conversas recentes
- [ ] Identificar padrões de problema

### Fim do dia (18h)
- [ ] Resumo de métricas do dia
- [ ] Listar conversas para revisar
- [ ] Anotar sugestões de melhoria
```

## DoD

- [x] Script de execução funciona
- [x] Campanha executa respeitando limites
- [x] Dashboard de status em tempo real
- [x] Checklist de monitoramento definido
- [x] Logs completos de cada envio

---

# S4.E3.5 - Análise de resultados do piloto

## Objetivo

> **Analisar resultados e gerar relatório do piloto.**

**Resultado esperado:** Relatório completo com métricas e insights.

## Tarefas

### 1. Script de análise

```python
# scripts/analisar_piloto.py

from datetime import datetime
import json

async def analisar_piloto() -> dict:
    """Gera análise completa do piloto."""

    # Buscar todos os dados do piloto
    medicos_piloto = (
        supabase.table("clientes")
        .select("*")
        .contains("tags", ["piloto_v1"])
        .execute()
    ).data

    medico_ids = [m["id"] for m in medicos_piloto]

    conversas = (
        supabase.table("conversations")
        .select("*, metricas_conversa(*), avaliacoes_qualidade(*)")
        .in_("cliente_id", medico_ids)
        .execute()
    ).data

    handoffs = (
        supabase.table("handoffs")
        .select("*")
        .in_("conversa_id", [c["id"] for c in conversas])
        .execute()
    ).data

    # Calcular métricas
    analise = {
        "periodo": {
            "inicio": medicos_piloto[0].get("primeiro_contato_em"),
            "fim": datetime.now().isoformat()
        },
        "envios": {
            "total": len(medicos_piloto),
            "contactados": len([m for m in medicos_piloto if m.get("primeiro_contato_em")])
        },
        "respostas": {
            "total": len(set(c["cliente_id"] for c in conversas)),
            "taxa": len(set(c["cliente_id"] for c in conversas)) / len(medicos_piloto)
        },
        "conversas": {
            "total": len(conversas),
            "ativas": len([c for c in conversas if c["status"] == "ativa"]),
            "encerradas": len([c for c in conversas if c["status"] == "encerrada"])
        },
        "handoffs": {
            "total": len(handoffs),
            "taxa": len(handoffs) / len(conversas) if conversas else 0,
            "por_tipo": {}
        },
        "qualidade": {
            "score_medio": 0,
            "avaliacoes_auto": 0,
            "avaliacoes_gestor": 0
        }
    }

    # Agrupar handoffs por tipo
    for h in handoffs:
        tipo = h["trigger_type"]
        analise["handoffs"]["por_tipo"][tipo] = analise["handoffs"]["por_tipo"].get(tipo, 0) + 1

    # Calcular score médio
    scores = []
    for c in conversas:
        for av in c.get("avaliacoes_qualidade", []):
            scores.append(av["score_geral"])
            if av["avaliador"] == "auto":
                analise["qualidade"]["avaliacoes_auto"] += 1
            else:
                analise["qualidade"]["avaliacoes_gestor"] += 1

    if scores:
        analise["qualidade"]["score_medio"] = sum(scores) / len(scores)

    return analise
```

### 2. Gerar relatório formatado

```python
def formatar_relatorio(analise: dict) -> str:
    """Formata análise em relatório legível."""

    relatorio = f"""
# Relatório do Piloto Júlia V1

## Período
- Início: {analise['periodo']['inicio']}
- Fim: {analise['periodo']['fim']}

## Envios
- Total de médicos: {analise['envios']['total']}
- Contactados: {analise['envios']['contactados']}

## Respostas
- Médicos que responderam: {analise['respostas']['total']}
- **Taxa de resposta: {analise['respostas']['taxa']*100:.1f}%**

## Conversas
- Total: {analise['conversas']['total']}
- Ativas: {analise['conversas']['ativas']}
- Encerradas: {analise['conversas']['encerradas']}

## Handoffs
- Total: {analise['handoffs']['total']}
- **Taxa de handoff: {analise['handoffs']['taxa']*100:.1f}%**
- Por tipo:
"""
    for tipo, qtd in analise['handoffs']['por_tipo'].items():
        relatorio += f"  - {tipo}: {qtd}\n"

    relatorio += f"""
## Qualidade
- **Score médio: {analise['qualidade']['score_medio']:.1f}/10**
- Avaliações automáticas: {analise['qualidade']['avaliacoes_auto']}
- Avaliações do gestor: {analise['qualidade']['avaliacoes_gestor']}

## Conclusões

### Métricas vs Metas
| Métrica | Resultado | Meta | Status |
|---------|-----------|------|--------|
| Taxa de resposta | {analise['respostas']['taxa']*100:.1f}% | > 30% | {'✅' if analise['respostas']['taxa'] > 0.3 else '❌'} |
| Taxa de handoff | {analise['handoffs']['taxa']*100:.1f}% | < 10% | {'✅' if analise['handoffs']['taxa'] < 0.1 else '❌'} |
| Score de qualidade | {analise['qualidade']['score_medio']:.1f} | > 7 | {'✅' if analise['qualidade']['score_medio'] > 7 else '❌'} |

### Próximos Passos
1. [Baseado nos resultados]
2. [Ajustes necessários]
3. [Expansão ou iteração]
"""

    return relatorio
```

### 3. Exportar dados para análise externa

```python
async def exportar_dados_piloto(formato: str = "json") -> str:
    """Exporta dados do piloto para análise externa."""
    analise = await analisar_piloto()

    # Adicionar dados brutos
    medicos_piloto = (
        supabase.table("clientes")
        .select("id, primeiro_nome, especialidade_id, primeiro_contato_em, status")
        .contains("tags", ["piloto_v1"])
        .execute()
    ).data

    analise["dados_brutos"] = {
        "medicos": medicos_piloto
    }

    if formato == "json":
        return json.dumps(analise, indent=2, ensure_ascii=False)
    elif formato == "markdown":
        return formatar_relatorio(analise)

    return str(analise)


async def main():
    print("Analisando piloto...")
    analise = await analisar_piloto()

    # Exibir relatório
    relatorio = formatar_relatorio(analise)
    print(relatorio)

    # Salvar
    with open("relatorio_piloto_v1.md", "w") as f:
        f.write(relatorio)

    # Exportar JSON
    dados = await exportar_dados_piloto("json")
    with open("dados_piloto_v1.json", "w") as f:
        f.write(dados)

    print("\nArquivos salvos:")
    print("- relatorio_piloto_v1.md")
    print("- dados_piloto_v1.json")


if __name__ == "__main__":
    asyncio.run(main())
```

## DoD

- [x] Script de análise funciona
- [x] Todas as métricas calculadas
- [x] Relatório formatado gerado
- [x] Comparação com metas
- [x] Exportação JSON para análise
- [x] Conclusões e próximos passos
