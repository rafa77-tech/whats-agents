# E09: Gestor Comanda Julia (Linguagem Natural)

**Fase:** 3 - Interação Gestor
**Estimativa:** 8h
**Prioridade:** Alta
**Dependências:** E08 (Canal de Ajuda)

---

## Objetivo

Permitir que o gestor comande Julia via Slack usando linguagem natural. Opus interpreta o comando, apresenta plano, e Haiku executa após confirmação.

## Fluxo

```
Gestor: "Julia, entra em contato com todos os cardiologistas
        que responderam positivo no último mês mas não fecharam"

Julia (Opus): "Entendi! Só pra confirmar:
              - Cardiologistas que responderam interesse
              - No último mês (dezembro/janeiro)
              - Que não fecharam nenhuma vaga

              Encontrei 23 médicos nesse perfil. Faço um followup
              perguntando se ainda têm interesse?"

Gestor: "Isso, mas menciona que temos vagas novas em fevereiro"

Julia (Opus): "Perfeito! Vou:
              1. Contatar os 23 médicos
              2. Perguntar se ainda têm interesse
              3. Mencionar vagas de fevereiro

              Posso começar?"

Gestor: "Vai"

Julia (Haiku): [Executa os 23 contatos]
```

---

## Tarefas

### T1: Criar tabela comandos_gestor (30min)

**Migration:** `create_comandos_gestor_table`

```sql
-- Migration: create_comandos_gestor_table
-- Sprint 32 E09: Comandos do gestor via Slack

CREATE TABLE IF NOT EXISTS comandos_gestor (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Comando original
    comando_texto TEXT NOT NULL,
    gestor_id TEXT NOT NULL,  -- ID do usuário Slack

    -- Interpretação (Opus)
    interpretacao JSONB,  -- Resultado da análise do Opus
    plano_proposto TEXT,  -- Plano em texto para o gestor
    medicos_encontrados INT,
    filtros_aplicados JSONB,

    -- Status
    status TEXT NOT NULL DEFAULT 'interpretando',
    -- interpretando | aguardando_confirmacao | confirmado | executando | concluido | cancelado | erro

    -- Confirmação
    confirmado_em TIMESTAMPTZ,
    ajustes_gestor TEXT,  -- Modificações pedidas pelo gestor

    -- Execução
    execucao_iniciada_em TIMESTAMPTZ,
    execucao_concluida_em TIMESTAMPTZ,
    resultado_execucao JSONB,

    -- Erro
    erro TEXT,

    -- Slack
    slack_channel TEXT,
    slack_thread_ts TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_comando_status CHECK (
        status IN ('interpretando', 'aguardando_confirmacao', 'confirmado', 'executando', 'concluido', 'cancelado', 'erro')
    )
);

-- Índices
CREATE INDEX idx_comandos_gestor_status
ON comandos_gestor (status, created_at);

CREATE INDEX idx_comandos_gestor_slack
ON comandos_gestor (slack_thread_ts);

-- Comentários
COMMENT ON TABLE comandos_gestor IS 'Comandos do gestor interpretados e executados por Julia';
```

### T2: Criar serviço de interpretação de comandos (90min)

**Arquivo:** `app/services/comando_gestor/interpretador.py`

```python
"""
Interpretador de comandos do gestor usando Opus.

Sprint 32 E09 - Gestor comanda Julia em linguagem natural.
"""
import logging
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase
from app.services.llm import chamar_llm_opus

logger = logging.getLogger(__name__)


@dataclass
class InterpretacaoComando:
    """Resultado da interpretação de um comando."""
    tipo_acao: str  # contatar | criar_campanha | atualizar | consultar | outro
    filtros_medicos: dict
    quantidade_estimada: int
    tipo_campanha: Optional[str]  # discovery | oferta | followup | etc.
    objetivo: str
    regras_especificas: list[str]
    plano_texto: str
    confianca: float  # 0-1, quão certo Opus está


PROMPT_INTERPRETADOR = """
Você é um assistente que interpreta comandos de gestores para a Julia (escalista virtual).

COMANDO DO GESTOR:
{comando}

CONTEXTO ATUAL:
- Data de hoje: {data_hoje}
- Médicos na base: {total_medicos}
- Campanhas ativas: {campanhas_ativas}

TAREFA:
Analise o comando e extraia:
1. TIPO_ACAO: contatar | criar_campanha | atualizar | consultar | outro
2. FILTROS_MEDICOS: Critérios para selecionar médicos (especialidade, região, status, período, etc.)
3. TIPO_CAMPANHA: Se for contato, qual tipo (discovery, oferta, followup, feedback, reativacao)
4. OBJETIVO: O que Julia deve fazer/dizer
5. REGRAS_ESPECIFICAS: Instruções extras do gestor

RESPONDA EM JSON:
{{
    "tipo_acao": "...",
    "filtros_medicos": {{...}},
    "tipo_campanha": "..." ou null,
    "objetivo": "...",
    "regras_especificas": ["...", "..."],
    "plano_resumido": "...",
    "confianca": 0.0-1.0,
    "perguntas_clarificacao": ["..."] // Se algo não ficou claro
}}
"""


async def interpretar_comando(
    comando: str,
    gestor_id: str,
) -> InterpretacaoComando:
    """
    Interpreta comando do gestor usando Opus.

    Args:
        comando: Texto do comando em linguagem natural
        gestor_id: ID do gestor no Slack

    Returns:
        InterpretacaoComando com análise
    """
    from datetime import datetime

    # Buscar contexto atual
    total_medicos = (
        supabase.table("clientes")
        .select("id", count="exact")
        .eq("opt_out", False)
        .execute()
    ).count or 0

    campanhas_ativas = (
        supabase.table("campanhas")
        .select("id", count="exact")
        .eq("status", "ativa")
        .execute()
    ).count or 0

    # Montar prompt
    prompt = PROMPT_INTERPRETADOR.format(
        comando=comando,
        data_hoje=datetime.now().strftime("%d/%m/%Y"),
        total_medicos=total_medicos,
        campanhas_ativas=campanhas_ativas,
    )

    # Chamar Opus para interpretação
    resposta = await chamar_llm_opus(
        prompt=prompt,
        json_mode=True,
    )

    # Parsear resposta
    import json
    try:
        dados = json.loads(resposta)
    except json.JSONDecodeError:
        logger.error(f"Erro ao parsear resposta do Opus: {resposta}")
        raise ValueError("Não consegui interpretar o comando")

    # Estimar quantidade de médicos
    quantidade = await _estimar_quantidade_medicos(dados.get("filtros_medicos", {}))

    return InterpretacaoComando(
        tipo_acao=dados.get("tipo_acao", "outro"),
        filtros_medicos=dados.get("filtros_medicos", {}),
        quantidade_estimada=quantidade,
        tipo_campanha=dados.get("tipo_campanha"),
        objetivo=dados.get("objetivo", ""),
        regras_especificas=dados.get("regras_especificas", []),
        plano_texto=dados.get("plano_resumido", ""),
        confianca=dados.get("confianca", 0.5),
    )


async def _estimar_quantidade_medicos(filtros: dict) -> int:
    """Estima quantidade de médicos que serão afetados."""
    query = (
        supabase.table("clientes")
        .select("id", count="exact")
        .eq("opt_out", False)
        .eq("status_telefone", "validado")
    )

    if filtros.get("especialidade"):
        query = query.eq("especialidade", filtros["especialidade"])

    if filtros.get("regiao"):
        query = query.eq("regiao", filtros["regiao"])

    # Outros filtros podem ser adicionados

    result = query.execute()
    return result.count or 0


async def gerar_plano_detalhado(
    interpretacao: InterpretacaoComando,
) -> str:
    """
    Gera plano detalhado para apresentar ao gestor.
    """
    plano = f"""📋 *Entendi o seguinte:*

*Ação:* {interpretacao.tipo_acao.title()}
*Tipo:* {interpretacao.tipo_campanha or 'Geral'}

*Filtros aplicados:*
"""

    for chave, valor in interpretacao.filtros_medicos.items():
        plano += f"• {chave}: {valor}\n"

    plano += f"""
*Médicos encontrados:* {interpretacao.quantidade_estimada}

*O que Julia vai fazer:*
{interpretacao.objetivo}
"""

    if interpretacao.regras_especificas:
        plano += "\n*Regras específicas:*\n"
        for regra in interpretacao.regras_especificas:
            plano += f"• {regra}\n"

    plano += "\n_Confirma que posso começar?_"

    return plano
```

### T3: Criar serviço de execução de comandos (60min)

**Arquivo:** `app/services/comando_gestor/executor.py`

```python
"""
Executor de comandos do gestor usando Haiku.

Sprint 32 E09 - Executa plano confirmado pelo gestor.
"""
import logging
from datetime import datetime, timezone

from app.services.supabase import supabase
from app.services.comando_gestor.interpretador import InterpretacaoComando

logger = logging.getLogger(__name__)


async def executar_comando(
    comando_id: str,
    interpretacao: InterpretacaoComando,
) -> dict:
    """
    Executa comando confirmado pelo gestor.

    Args:
        comando_id: ID do comando no banco
        interpretacao: Interpretação aprovada

    Returns:
        Resultado da execução
    """
    # Marcar como executando
    supabase.table("comandos_gestor").update({
        "status": "executando",
        "execucao_iniciada_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", comando_id).execute()

    resultado = {
        "sucesso": True,
        "medicos_processados": 0,
        "campanhas_criadas": 0,
        "erros": [],
    }

    try:
        if interpretacao.tipo_acao == "contatar":
            resultado = await _executar_contatar(interpretacao)

        elif interpretacao.tipo_acao == "criar_campanha":
            resultado = await _executar_criar_campanha(interpretacao)

        elif interpretacao.tipo_acao == "consultar":
            resultado = await _executar_consulta(interpretacao)

        else:
            resultado["sucesso"] = False
            resultado["erros"].append(f"Tipo de ação não suportado: {interpretacao.tipo_acao}")

        # Marcar como concluído
        supabase.table("comandos_gestor").update({
            "status": "concluido",
            "execucao_concluida_em": datetime.now(timezone.utc).isoformat(),
            "resultado_execucao": resultado,
        }).eq("id", comando_id).execute()

    except Exception as e:
        logger.error(f"Erro ao executar comando {comando_id}: {e}")

        supabase.table("comandos_gestor").update({
            "status": "erro",
            "erro": str(e),
        }).eq("id", comando_id).execute()

        resultado["sucesso"] = False
        resultado["erros"].append(str(e))

    return resultado


async def _executar_contatar(interpretacao: InterpretacaoComando) -> dict:
    """Executa comando de contatar médicos."""
    resultado = {
        "sucesso": True,
        "medicos_processados": 0,
        "mensagens_enfileiradas": 0,
        "erros": [],
    }

    # Buscar médicos com os filtros
    medicos = await _buscar_medicos_com_filtros(interpretacao.filtros_medicos)

    if not medicos:
        resultado["erros"].append("Nenhum médico encontrado com os filtros")
        return resultado

    # Criar campanha
    campanha = supabase.table("campanhas").insert({
        "nome": f"Comando Gestor - {datetime.now().strftime('%d/%m %H:%M')}",
        "tipo": interpretacao.tipo_campanha or "followup",
        "objetivo": interpretacao.objetivo,
        "regras": interpretacao.regras_especificas,
        "status": "ativa",
    }).execute()

    if not campanha.data:
        resultado["erros"].append("Falha ao criar campanha")
        return resultado

    campanha_id = campanha.data[0]["id"]
    resultado["campanha_id"] = campanha_id

    # Enfileirar mensagens
    for medico in medicos:
        try:
            supabase.table("fila_mensagens").insert({
                "cliente_id": medico["id"],
                "campaign_id": campanha_id,
                "send_type": interpretacao.tipo_campanha or "followup",
                "queue_status": "queued",
                "metadata": {
                    "origem": "comando_gestor",
                    "objetivo": interpretacao.objetivo,
                },
            }).execute()

            resultado["mensagens_enfileiradas"] += 1

        except Exception as e:
            resultado["erros"].append(f"Erro ao enfileirar {medico['id']}: {e}")

        resultado["medicos_processados"] += 1

    logger.info(
        f"Comando executado: {resultado['mensagens_enfileiradas']} mensagens enfileiradas"
    )

    return resultado


async def _buscar_medicos_com_filtros(filtros: dict) -> list[dict]:
    """Busca médicos aplicando filtros dinâmicos."""
    query = (
        supabase.table("clientes")
        .select("id, nome, telefone, especialidade, regiao")
        .eq("opt_out", False)
        .eq("status_telefone", "validado")
    )

    if filtros.get("especialidade"):
        query = query.eq("especialidade", filtros["especialidade"])

    if filtros.get("regiao"):
        query = query.eq("regiao", filtros["regiao"])

    if filtros.get("respondeu_positivo"):
        # Filtro complexo - médicos que responderam positivo
        # Isso requer join com interacoes ou tabela de status
        pass  # Implementar conforme necessidade

    if filtros.get("nao_fechou"):
        # Médicos que não fecharam plantão
        pass  # Implementar conforme necessidade

    response = query.limit(filtros.get("limite", 100)).execute()

    return response.data or []


async def _executar_criar_campanha(interpretacao: InterpretacaoComando) -> dict:
    """Cria campanha sem enviar imediatamente."""
    # Similar ao contatar, mas só cria a campanha
    campanha = supabase.table("campanhas").insert({
        "nome": f"Campanha - {datetime.now().strftime('%d/%m %H:%M')}",
        "tipo": interpretacao.tipo_campanha or "custom",
        "objetivo": interpretacao.objetivo,
        "regras": interpretacao.regras_especificas,
        "filtros_medicos": interpretacao.filtros_medicos,
        "status": "rascunho",  # Não ativa imediatamente
    }).execute()

    return {
        "sucesso": bool(campanha.data),
        "campanha_id": campanha.data[0]["id"] if campanha.data else None,
    }


async def _executar_consulta(interpretacao: InterpretacaoComando) -> dict:
    """Executa consulta e retorna dados."""
    medicos = await _buscar_medicos_com_filtros(interpretacao.filtros_medicos)

    return {
        "sucesso": True,
        "total_encontrados": len(medicos),
        "medicos": [
            {"id": m["id"], "nome": m.get("nome"), "especialidade": m.get("especialidade")}
            for m in medicos[:20]  # Limitar resposta
        ],
    }
```

### T4: Integrar com handler do Slack (45min)

**Arquivo:** `app/api/routes/slack.py`

**Adicionar handler para comandos:**

```python
from app.services.comando_gestor.interpretador import (
    interpretar_comando,
    gerar_plano_detalhado,
)
from app.services.comando_gestor.executor import executar_comando

# Padrões que indicam comando para Julia
PADROES_COMANDO = [
    "julia,",
    "julia ",
    "@julia",
    "hey julia",
    "oi julia",
]


async def _processar_mensagem_canal(event: dict):
    """Processa mensagem no canal (pode ser comando)."""
    texto = event.get("text", "").lower()
    user_id = event.get("user")
    channel = event.get("channel")
    ts = event.get("ts")

    # Verificar se é comando para Julia
    eh_comando = any(p in texto for p in PADROES_COMANDO)

    if not eh_comando:
        return

    # Registrar comando no banco
    comando = supabase.table("comandos_gestor").insert({
        "comando_texto": event.get("text"),
        "gestor_id": user_id,
        "status": "interpretando",
        "slack_channel": channel,
        "slack_thread_ts": ts,
    }).execute()

    comando_id = comando.data[0]["id"]

    try:
        # Interpretar comando com Opus
        interpretacao = await interpretar_comando(
            comando=event.get("text"),
            gestor_id=user_id,
        )

        # Salvar interpretação
        supabase.table("comandos_gestor").update({
            "status": "aguardando_confirmacao",
            "interpretacao": {
                "tipo_acao": interpretacao.tipo_acao,
                "filtros": interpretacao.filtros_medicos,
                "tipo_campanha": interpretacao.tipo_campanha,
                "objetivo": interpretacao.objetivo,
            },
            "medicos_encontrados": interpretacao.quantidade_estimada,
            "filtros_aplicados": interpretacao.filtros_medicos,
        }).eq("id", comando_id).execute()

        # Gerar e enviar plano
        plano = await gerar_plano_detalhado(interpretacao)

        await slack_client.enviar_mensagem(
            canal=channel,
            texto=plano,
            thread_ts=ts,
        )

    except Exception as e:
        logger.error(f"Erro ao interpretar comando: {e}")

        supabase.table("comandos_gestor").update({
            "status": "erro",
            "erro": str(e),
        }).eq("id", comando_id).execute()

        await slack_client.enviar_mensagem(
            canal=channel,
            texto=f"❌ Não consegui entender o comando: {e}",
            thread_ts=ts,
        )


async def _processar_confirmacao_comando(event: dict):
    """Processa confirmação do gestor na thread do comando."""
    thread_ts = event.get("thread_ts")
    texto = event.get("text", "").lower()

    # Buscar comando pela thread
    comando = (
        supabase.table("comandos_gestor")
        .select("*")
        .eq("slack_thread_ts", thread_ts)
        .eq("status", "aguardando_confirmacao")
        .single()
        .execute()
    )

    if not comando.data:
        return

    # Verificar se é confirmação
    confirmacoes = ["sim", "vai", "pode", "confirmo", "ok", "go", "bora"]
    cancelamentos = ["não", "cancela", "para", "aborta"]

    if any(c in texto for c in confirmacoes):
        # Confirmar e executar
        from app.services.comando_gestor.interpretador import InterpretacaoComando

        interpretacao = InterpretacaoComando(
            tipo_acao=comando.data["interpretacao"]["tipo_acao"],
            filtros_medicos=comando.data["interpretacao"]["filtros"],
            quantidade_estimada=comando.data["medicos_encontrados"],
            tipo_campanha=comando.data["interpretacao"]["tipo_campanha"],
            objetivo=comando.data["interpretacao"]["objetivo"],
            regras_especificas=[],
            plano_texto="",
            confianca=1.0,
        )

        supabase.table("comandos_gestor").update({
            "status": "confirmado",
            "confirmado_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", comando.data["id"]).execute()

        await slack_client.enviar_mensagem(
            canal=event.get("channel"),
            texto="✅ Confirmado! Iniciando execução...",
            thread_ts=thread_ts,
        )

        # Executar em background
        resultado = await executar_comando(comando.data["id"], interpretacao)

        # Reportar resultado
        if resultado["sucesso"]:
            await slack_client.enviar_mensagem(
                canal=event.get("channel"),
                texto=(
                    f"✅ *Execução concluída!*\n\n"
                    f"• Médicos processados: {resultado.get('medicos_processados', 0)}\n"
                    f"• Mensagens enfileiradas: {resultado.get('mensagens_enfileiradas', 0)}"
                ),
                thread_ts=thread_ts,
            )
        else:
            await slack_client.enviar_mensagem(
                canal=event.get("channel"),
                texto=f"❌ Erro na execução: {resultado.get('erros', [])}",
                thread_ts=thread_ts,
            )

    elif any(c in texto for c in cancelamentos):
        supabase.table("comandos_gestor").update({
            "status": "cancelado",
        }).eq("id", comando.data["id"]).execute()

        await slack_client.enviar_mensagem(
            canal=event.get("channel"),
            texto="❌ Comando cancelado.",
            thread_ts=thread_ts,
        )
```

### T5: Criar testes (45min)

**Arquivo:** `tests/unit/test_comando_gestor.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.comando_gestor.interpretador import (
    interpretar_comando,
    InterpretacaoComando,
)
from app.services.comando_gestor.executor import executar_comando


class TestInterpretador:
    """Testes para interpretador de comandos."""

    @pytest.mark.asyncio
    async def test_interpreta_comando_contatar(self):
        """Deve interpretar comando de contatar médicos."""
        with patch("app.services.comando_gestor.interpretador.chamar_llm_opus") as mock_llm:
            mock_llm.return_value = '''
            {
                "tipo_acao": "contatar",
                "filtros_medicos": {"especialidade": "cardiologia"},
                "tipo_campanha": "followup",
                "objetivo": "Perguntar se ainda tem interesse",
                "regras_especificas": ["Mencionar vagas de fevereiro"],
                "plano_resumido": "Contatar cardiologistas",
                "confianca": 0.9
            }
            '''

            with patch("app.services.comando_gestor.interpretador.supabase") as mock_sb:
                mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.count = 100

                resultado = await interpretar_comando(
                    comando="Julia, entre em contato com os cardiologistas",
                    gestor_id="U123",
                )

                assert resultado.tipo_acao == "contatar"
                assert resultado.tipo_campanha == "followup"
                assert "cardiologia" in str(resultado.filtros_medicos)


class TestExecutor:
    """Testes para executor de comandos."""

    @pytest.mark.asyncio
    async def test_executa_comando_contatar(self):
        """Deve executar comando e enfileirar mensagens."""
        interpretacao = InterpretacaoComando(
            tipo_acao="contatar",
            filtros_medicos={"especialidade": "cardiologia"},
            quantidade_estimada=10,
            tipo_campanha="followup",
            objetivo="Perguntar interesse",
            regras_especificas=[],
            plano_texto="",
            confianca=1.0,
        )

        with patch("app.services.comando_gestor.executor.supabase") as mock_sb:
            # Mock update status
            mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

            # Mock criar campanha
            mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": 123}]

            # Mock buscar médicos
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                {"id": "med-1", "nome": "Dr João"},
                {"id": "med-2", "nome": "Dra Maria"},
            ]

            resultado = await executar_comando("cmd-1", interpretacao)

            assert resultado["sucesso"] is True
            assert resultado["medicos_processados"] == 2
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Tabela comandos_gestor criada**
  - [ ] Migration aplicada
  - [ ] Índices funcionando

- [ ] **Interpretação funciona**
  - [ ] Opus interpreta comandos em linguagem natural
  - [ ] Extrai tipo de ação, filtros, objetivo
  - [ ] Estima quantidade de médicos

- [ ] **Fluxo de confirmação funciona**
  - [ ] Plano é apresentado ao gestor
  - [ ] Gestor pode confirmar ou cancelar
  - [ ] Ajustes são aceitos

- [ ] **Execução funciona**
  - [ ] Comando confirmado é executado
  - [ ] Campanha é criada
  - [ ] Mensagens são enfileiradas
  - [ ] Resultado é reportado

- [ ] **Integração Slack funciona**
  - [ ] Detecta comandos no canal
  - [ ] Respostas em thread
  - [ ] Confirmação funciona

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_comando_gestor.py -v` = OK

---

## Notas para o Desenvolvedor

1. **Opus vs Haiku:**
   - Opus interpreta (custo maior, mais preciso)
   - Haiku executa (custo menor, mais rápido)

2. **Segurança:**
   - Sempre pedir confirmação antes de executar
   - Limitar quantidade de médicos por execução
   - Logar todas as ações

3. **Filtros complexos:**
   - "respondeu positivo" requer análise de interações
   - Pode precisar de RPCs no banco
