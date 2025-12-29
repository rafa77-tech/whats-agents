# E04: Modo Fora do Horario

**Epico:** Ack Imediato + Processamento Diferido
**Estimativa:** 5h
**Dependencias:** E01 (Migrations), E02 (Classificador), E03 (Delay Engine)

---

## Objetivo

Implementar comportamento inteligente fora do horario comercial: reconhecer a mensagem imediatamente (ack) mas diferir acoes para o horario comercial.

---

## Comportamento Atual vs Novo

| Aspecto | Atual | Novo |
|---------|-------|------|
| Mensagem fora horario | Silencio total | Ack imediato |
| Processamento | Enfileira tudo | Separa ack de acao |
| Retomada | Segunda 08h | Primeiro horario util |
| Percepção medico | "Nao sei se fui atendido" | "Recebi, vou resolver" |

---

## Escopo

### Incluido

- [x] Detector de horario comercial
- [x] Templates de ack fora horario
- [x] Armazenamento de mensagens para retomada
- [x] Job de processamento as 08h
- [x] Retomada com contexto

### Excluido

- [ ] Mudancas no horario comercial (continua 08-20)
- [ ] Processamento de fins de semana (mantém igual)

---

## Templates de Ack

### Mensagem Generica

```
Oi Dr(a) {nome}! Recebi sua mensagem.

Vou verificar isso pra voce e te retorno assim que
o horario operacional abrir, tudo bem?

Qualquer urgencia, me avisa!
```

### Mensagem sobre Vaga

```
Oi Dr(a) {nome}! Vi que vc mandou msg sobre vaga.

Deixa comigo! Vou checar as opcoes e te retorno
logo cedo, ok?
```

### Mensagem de Confirmacao

```
Oi Dr(a) {nome}! Anotei aqui.

Amanha cedo ja te confirmo tudo certinho!
```

---

## Tarefas

### T01: Servico fora_horario.py

**Arquivo:** `app/services/fora_horario.py`

```python
"""
Servico de tratamento de mensagens fora do horario.

Sprint 22 - Responsividade Inteligente
"""
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings
from app.services.supabase import supabase
from app.services.message_context_classifier import ContextClassification, ContextType
from app.services.delay_engine import pode_enviar_fora_horario

logger = logging.getLogger(__name__)

# Configuracao de horario comercial
HORARIO_INICIO = time(8, 0)   # 08:00
HORARIO_FIM = time(20, 0)     # 20:00
DIAS_UTEIS = [0, 1, 2, 3, 4]  # Segunda a Sexta (0=Monday)


@dataclass
class AckTemplate:
    """Template de ack para fora do horario."""
    tipo: str
    mensagem: str


ACK_TEMPLATES = {
    "generico": AckTemplate(
        tipo="generico",
        mensagem="""Oi Dr(a) {nome}! Recebi sua mensagem.

Vou verificar isso pra voce e te retorno assim que o horario operacional abrir, tudo bem?

Qualquer urgencia, me avisa!"""
    ),
    "vaga": AckTemplate(
        tipo="vaga",
        mensagem="""Oi Dr(a) {nome}! Vi que vc mandou msg sobre vaga.

Deixa comigo! Vou checar as opcoes e te retorno logo cedo, ok?"""
    ),
    "confirmacao": AckTemplate(
        tipo="confirmacao",
        mensagem="""Oi Dr(a) {nome}! Anotei aqui.

Amanha cedo ja te confirmo tudo certinho!"""
    ),
}


def eh_horario_comercial(dt: Optional[datetime] = None) -> bool:
    """
    Verifica se um datetime esta dentro do horario comercial.

    Args:
        dt: Datetime a verificar (default: agora)

    Returns:
        True se dentro do horario comercial
    """
    dt = dt or datetime.now()

    # Verificar dia da semana
    if dt.weekday() not in DIAS_UTEIS:
        return False

    # Verificar hora
    hora_atual = dt.time()
    return HORARIO_INICIO <= hora_atual <= HORARIO_FIM


def proximo_horario_comercial(dt: Optional[datetime] = None) -> datetime:
    """
    Calcula o proximo horario comercial.

    Args:
        dt: Datetime de referencia (default: agora)

    Returns:
        Proximo datetime em horario comercial
    """
    dt = dt or datetime.now()

    # Se ja esta em horario comercial, retorna agora
    if eh_horario_comercial(dt):
        return dt

    # Comecar do proximo dia as 08:00
    proximo = datetime.combine(dt.date(), HORARIO_INICIO)

    # Se ainda nao passou das 08:00 hoje e eh dia util
    if dt.time() < HORARIO_INICIO and dt.weekday() in DIAS_UTEIS:
        return proximo

    # Avancar para proximo dia util
    proximo = proximo + timedelta(days=1)
    while proximo.weekday() not in DIAS_UTEIS:
        proximo = proximo + timedelta(days=1)

    return proximo


def selecionar_template_ack(
    classificacao: ContextClassification,
    contexto: Optional[dict] = None
) -> AckTemplate:
    """
    Seleciona template de ack apropriado.

    Args:
        classificacao: Classificacao de contexto
        contexto: Contexto adicional da conversa

    Returns:
        AckTemplate apropriado
    """
    contexto = contexto or {}

    # Se eh sobre vaga
    if contexto.get("oferta_pendente") or contexto.get("busca_vaga"):
        return ACK_TEMPLATES["vaga"]

    # Se eh confirmacao
    if classificacao.tipo == ContextType.CONFIRMACAO:
        return ACK_TEMPLATES["confirmacao"]

    # Default
    return ACK_TEMPLATES["generico"]


async def salvar_mensagem_fora_horario(
    cliente_id: str,
    mensagem: str,
    conversa_id: Optional[str] = None,
    contexto: Optional[dict] = None
) -> str:
    """
    Salva mensagem para processamento posterior.

    Args:
        cliente_id: ID do cliente
        mensagem: Texto da mensagem
        conversa_id: ID da conversa (opcional)
        contexto: Contexto para retomada

    Returns:
        ID do registro criado
    """
    try:
        result = supabase.table("mensagens_fora_horario").insert({
            "cliente_id": cliente_id,
            "conversa_id": conversa_id,
            "mensagem": mensagem,
            "recebida_em": datetime.now().isoformat(),
            "contexto": contexto or {},
        }).execute()

        registro_id = result.data[0]["id"]
        logger.info(f"Mensagem fora horario salva: {registro_id}")
        return registro_id

    except Exception as e:
        logger.error(f"Erro ao salvar mensagem fora horario: {e}")
        raise


async def marcar_ack_enviado(registro_id: str, mensagem_id: str) -> None:
    """
    Marca que o ack foi enviado.

    Args:
        registro_id: ID do registro em mensagens_fora_horario
        mensagem_id: ID da mensagem no WhatsApp
    """
    try:
        supabase.table("mensagens_fora_horario").update({
            "ack_enviado": True,
            "ack_enviado_em": datetime.now().isoformat(),
            "ack_mensagem_id": mensagem_id,
        }).eq("id", registro_id).execute()

        logger.debug(f"Ack marcado como enviado: {registro_id}")

    except Exception as e:
        logger.error(f"Erro ao marcar ack: {e}")


async def buscar_mensagens_pendentes() -> list[dict]:
    """
    Busca mensagens fora do horario pendentes de processamento.

    Returns:
        Lista de registros pendentes
    """
    try:
        result = supabase.table("mensagens_fora_horario").select(
            "*, clientes(nome, telefone)"
        ).eq(
            "processada", False
        ).order(
            "recebida_em"
        ).execute()

        return result.data

    except Exception as e:
        logger.error(f"Erro ao buscar mensagens pendentes: {e}")
        return []


async def marcar_processada(
    registro_id: str,
    resultado: str = "sucesso"
) -> None:
    """
    Marca mensagem como processada.

    Args:
        registro_id: ID do registro
        resultado: Resultado do processamento
    """
    try:
        supabase.table("mensagens_fora_horario").update({
            "processada": True,
            "processada_em": datetime.now().isoformat(),
            "processada_resultado": resultado,
        }).eq("id", registro_id).execute()

        logger.info(f"Mensagem processada: {registro_id} ({resultado})")

    except Exception as e:
        logger.error(f"Erro ao marcar processada: {e}")


async def processar_mensagem_fora_horario(
    cliente_id: str,
    mensagem: str,
    classificacao: ContextClassification,
    nome_cliente: str,
    contexto: Optional[dict] = None
) -> dict:
    """
    Processa mensagem recebida fora do horario.

    1. Salva para processamento posterior
    2. Seleciona template de ack
    3. Retorna ack para envio imediato

    Args:
        cliente_id: ID do cliente
        mensagem: Texto recebido
        classificacao: Classificacao de contexto
        nome_cliente: Nome do cliente para personalizacao
        contexto: Contexto da conversa

    Returns:
        Dict com ack_mensagem e registro_id
    """
    # 1. Verificar se pode responder fora do horario
    if not pode_enviar_fora_horario(classificacao):
        logger.info(f"Tipo {classificacao.tipo} nao permitido fora do horario")
        return {"ack_mensagem": None, "registro_id": None}

    # 2. Salvar para processamento posterior
    registro_id = await salvar_mensagem_fora_horario(
        cliente_id=cliente_id,
        mensagem=mensagem,
        contexto=contexto
    )

    # 3. Selecionar template
    template = selecionar_template_ack(classificacao, contexto)

    # 4. Formatar mensagem
    ack_mensagem = template.mensagem.format(
        nome=nome_cliente.split()[0] if nome_cliente else ""
    )

    logger.info(f"Ack preparado para cliente {cliente_id} (template={template.tipo})")

    return {
        "ack_mensagem": ack_mensagem,
        "registro_id": registro_id,
        "template_tipo": template.tipo,
    }
```

**DoD:**
- [ ] Arquivo criado
- [ ] Funcoes de horario comercial funcionando
- [ ] Templates de ack definidos
- [ ] Salvamento em mensagens_fora_horario

---

### T02: Job de Retomada

**Arquivo:** `app/workers/retomada_fora_horario.py`

```python
"""
Job para processar mensagens fora do horario.

Roda as 08:00 de dias uteis.

Sprint 22 - Responsividade Inteligente
"""
import logging
from datetime import datetime

from app.services.fora_horario import (
    buscar_mensagens_pendentes,
    marcar_processada,
    eh_horario_comercial,
)
from app.services.agente import processar_mensagem_retomada

logger = logging.getLogger(__name__)


async def processar_retomadas() -> dict:
    """
    Processa todas as mensagens fora do horario pendentes.

    Returns:
        Estatisticas de processamento
    """
    if not eh_horario_comercial():
        logger.info("Fora do horario comercial, pulando retomadas")
        return {"processadas": 0, "erro": 0, "motivo": "fora_horario"}

    pendentes = await buscar_mensagens_pendentes()

    if not pendentes:
        logger.info("Nenhuma mensagem fora do horario pendente")
        return {"processadas": 0, "erro": 0}

    logger.info(f"Processando {len(pendentes)} mensagens fora do horario")

    stats = {"processadas": 0, "erro": 0, "ignoradas": 0}

    for registro in pendentes:
        try:
            # Formatar mensagem de retomada
            cliente = registro.get("clientes", {})
            nome = cliente.get("nome", "").split()[0]

            mensagem_retomada = f"""Bom dia Dr(a) {nome}!

Sobre sua mensagem de ontem, ja verifiquei aqui.

"""
            # Processar a mensagem original com contexto
            await processar_mensagem_retomada(
                cliente_id=registro["cliente_id"],
                mensagem_original=registro["mensagem"],
                contexto=registro.get("contexto", {}),
                prefixo=mensagem_retomada
            )

            await marcar_processada(registro["id"], "sucesso")
            stats["processadas"] += 1

        except Exception as e:
            logger.error(f"Erro ao processar retomada {registro['id']}: {e}")
            await marcar_processada(registro["id"], f"erro: {str(e)}")
            stats["erro"] += 1

    logger.info(f"Retomadas concluidas: {stats}")
    return stats
```

**DoD:**
- [ ] Job criado
- [ ] Processa mensagens pendentes
- [ ] Retomada com contexto
- [ ] Estatisticas de processamento

---

### T03: Integracao no Webhook

**Arquivo:** Modificar `app/api/routes/webhook.py` ou `app/services/agente.py`

```python
from app.services.fora_horario import (
    eh_horario_comercial,
    processar_mensagem_fora_horario,
)

# No processamento de mensagem:
async def processar(mensagem, cliente_id, ...):
    # Classificar contexto
    classificacao = await classificar_contexto(...)

    # Verificar horario comercial
    if not eh_horario_comercial():
        # Processar fora do horario
        resultado = await processar_mensagem_fora_horario(
            cliente_id=cliente_id,
            mensagem=mensagem,
            classificacao=classificacao,
            nome_cliente=cliente.nome,
            contexto=contexto
        )

        if resultado["ack_mensagem"]:
            # Enviar ack imediato (sem delay)
            await enviar_mensagem(
                telefone=cliente.telefone,
                mensagem=resultado["ack_mensagem"]
            )
            await marcar_ack_enviado(
                resultado["registro_id"],
                mensagem_id
            )

        return  # Nao processa mais

    # Processamento normal...
```

**DoD:**
- [ ] Webhook detecta fora do horario
- [ ] Ack enviado imediatamente
- [ ] Mensagem salva para retomada
- [ ] Processamento normal bloqueado

---

### T04: Endpoint e Scheduler

**Arquivo:** Modificar `app/api/routes/jobs.py` e `app/workers/scheduler.py`

```python
# jobs.py
@router.post("/processar-retomadas")
async def job_processar_retomadas():
    """Processa mensagens fora do horario pendentes."""
    from app.workers.retomada_fora_horario import processar_retomadas

    stats = await processar_retomadas()
    return JSONResponse(stats)

# scheduler.py - adicionar job
{
    "name": "processar_retomadas",
    "endpoint": "/jobs/processar-retomadas",
    "schedule": "0 8 * * 1-5",  # 08:00 seg-sex
}
```

**DoD:**
- [ ] Endpoint criado
- [ ] Job agendado para 08:00 seg-sex
- [ ] Retomadas processadas automaticamente

---

## Validacao

### Testes Manuais

```python
# Testar horario comercial
from app.services.fora_horario import eh_horario_comercial
from datetime import datetime

# Testar 21:00 de terça
dt = datetime(2025, 12, 30, 21, 0)
assert eh_horario_comercial(dt) == False

# Testar 10:00 de terça
dt = datetime(2025, 12, 30, 10, 0)
assert eh_horario_comercial(dt) == True

# Testar domingo
dt = datetime(2025, 12, 28, 10, 0)
assert eh_horario_comercial(dt) == False
```

### Queries

```sql
-- Mensagens fora do horario hoje
SELECT
    COUNT(*) FILTER (WHERE ack_enviado) as com_ack,
    COUNT(*) FILTER (WHERE processada) as processadas,
    COUNT(*) FILTER (WHERE NOT processada) as pendentes
FROM mensagens_fora_horario
WHERE recebida_em >= CURRENT_DATE;
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Servico `fora_horario.py` implementado
- [ ] Deteccao de horario comercial funcionando
- [ ] Templates de ack definidos
- [ ] Mensagens salvas em `mensagens_fora_horario`
- [ ] Job de retomada as 08:00
- [ ] Integracao no webhook

### Qualidade

- [ ] Ack enviado em < 3s
- [ ] Retomada com contexto preservado
- [ ] Logs estruturados
- [ ] Testes unitarios

### Experiencia

- [ ] Medico recebe ack imediato
- [ ] Mensagem de retomada personalizada
- [ ] Nao parece robotico

---

*Epico criado em 29/12/2025*
