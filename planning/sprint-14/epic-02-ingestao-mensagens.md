# E02 - Ingestão de Mensagens

## Objetivo

Modificar o sistema para capturar e armazenar mensagens de grupos de WhatsApp, em vez de ignorá-las.

## Contexto

Atualmente, o parser em `app/services/parser.py` identifica mensagens de grupo pelo sufixo `@g.us` e as ignora completamente. Este épico modifica esse comportamento para:

1. Continuar NÃO respondendo em grupos (Julia só responde em DMs)
2. MAS salvar as mensagens para processamento posterior

## Stories

### S02.1 - Criar serviço de ingestão de grupos

**Descrição:** Criar módulo `app/services/grupos/ingestor.py` para gerenciar a ingestão.

**Critérios de Aceite:**
- [ ] Módulo criado com funções de ingestão
- [ ] Testes unitários
- [ ] Documentação

**Código:**
```python
# app/services/grupos/ingestor.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.schemas.mensagem import MensagemRecebida

logger = get_logger(__name__)


async def obter_ou_criar_grupo(jid: str, nome: Optional[str] = None) -> UUID:
    """
    Obtém ou cria registro de grupo.

    Args:
        jid: JID do grupo (ex: "123456@g.us")
        nome: Nome do grupo (opcional, do webhook)

    Returns:
        UUID do grupo
    """
    # Tentar buscar existente
    result = supabase.table("grupos_whatsapp").select("id").eq("jid", jid).execute()

    if result.data:
        grupo_id = result.data[0]["id"]
        logger.debug(f"Grupo existente: {grupo_id}")
        return UUID(grupo_id)

    # Criar novo
    novo_grupo = {
        "jid": jid,
        "nome": nome,
        "tipo": "vagas",  # Default
        "ativo": True,
        "monitorar_ofertas": True,
    }

    result = supabase.table("grupos_whatsapp").insert(novo_grupo).execute()
    grupo_id = result.data[0]["id"]

    logger.info(f"Novo grupo criado: {grupo_id} ({jid})")
    return UUID(grupo_id)


async def obter_ou_criar_contato(
    jid: str,
    nome: Optional[str] = None,
    telefone: Optional[str] = None
) -> UUID:
    """
    Obtém ou cria registro de contato.

    Args:
        jid: JID do contato (ex: "5511999999999@s.whatsapp.net")
        nome: Nome do contato (pushName)
        telefone: Número de telefone extraído

    Returns:
        UUID do contato
    """
    # Tentar buscar existente
    result = supabase.table("contatos_grupo").select("id").eq("jid", jid).execute()

    if result.data:
        contato_id = result.data[0]["id"]

        # Atualizar nome se veio novo
        if nome:
            supabase.table("contatos_grupo").update({
                "nome": nome,
                "ultimo_contato": datetime.utcnow().isoformat()
            }).eq("id", contato_id).execute()

        return UUID(contato_id)

    # Criar novo
    novo_contato = {
        "jid": jid,
        "nome": nome,
        "telefone": telefone,
        "tipo": "desconhecido",
        "primeiro_contato": datetime.utcnow().isoformat(),
        "ultimo_contato": datetime.utcnow().isoformat(),
    }

    result = supabase.table("contatos_grupo").insert(novo_contato).execute()
    contato_id = result.data[0]["id"]

    logger.info(f"Novo contato criado: {contato_id} ({jid})")
    return UUID(contato_id)


async def salvar_mensagem_grupo(
    grupo_id: UUID,
    contato_id: UUID,
    mensagem: MensagemRecebida,
    dados_raw: dict
) -> UUID:
    """
    Salva mensagem de grupo no banco.

    Args:
        grupo_id: UUID do grupo
        contato_id: UUID do contato
        mensagem: Mensagem parseada
        dados_raw: Dados originais do webhook

    Returns:
        UUID da mensagem salva
    """
    # Determinar tipo de mídia
    tipo_midia = "texto"
    tem_midia = False

    if mensagem.tipo == "image":
        tipo_midia = "imagem"
        tem_midia = True
    elif mensagem.tipo == "audio":
        tipo_midia = "audio"
        tem_midia = True
    elif mensagem.tipo == "video":
        tipo_midia = "video"
        tem_midia = True
    elif mensagem.tipo == "document":
        tipo_midia = "documento"
        tem_midia = True
    elif mensagem.tipo == "sticker":
        tipo_midia = "sticker"
        tem_midia = True

    # Determinar status inicial
    status = "pendente"
    if tem_midia:
        status = "ignorada_midia"
    elif not mensagem.texto or len(mensagem.texto.strip()) < 5:
        status = "ignorada_curta"

    nova_mensagem = {
        "grupo_id": str(grupo_id),
        "contato_id": str(contato_id),
        "message_id": mensagem.message_id,
        "sender_jid": dados_raw.get("key", {}).get("participant", ""),
        "sender_nome": mensagem.nome_contato,
        "texto": mensagem.texto,
        "tipo_midia": tipo_midia,
        "tem_midia": tem_midia,
        "timestamp_msg": mensagem.timestamp.isoformat() if mensagem.timestamp else None,
        "is_forwarded": dados_raw.get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("isForwarded", False),
        "status": status,
    }

    result = supabase.table("mensagens_grupo").insert(nova_mensagem).execute()
    mensagem_id = result.data[0]["id"]

    logger.debug(f"Mensagem salva: {mensagem_id} (status: {status})")
    return UUID(mensagem_id)


async def atualizar_contadores_grupo(grupo_id: UUID) -> None:
    """Incrementa contador de mensagens do grupo."""
    supabase.rpc("incrementar_mensagens_grupo", {"p_grupo_id": str(grupo_id)}).execute()


async def ingerir_mensagem_grupo(
    mensagem: MensagemRecebida,
    dados_raw: dict
) -> Optional[UUID]:
    """
    Função principal de ingestão.

    Orquestra todo o processo de ingestão de uma mensagem de grupo.

    Args:
        mensagem: Mensagem parseada
        dados_raw: Dados originais do webhook

    Returns:
        UUID da mensagem salva, ou None se não salvou
    """
    try:
        # Extrair JIDs
        key = dados_raw.get("key", {})
        grupo_jid = key.get("remoteJid", "")
        sender_jid = key.get("participant", "")

        if not grupo_jid or not sender_jid:
            logger.warning("JIDs ausentes na mensagem de grupo")
            return None

        # Obter/criar grupo
        grupo_id = await obter_ou_criar_grupo(
            jid=grupo_jid,
            nome=dados_raw.get("groupName")  # Nem sempre vem
        )

        # Obter/criar contato
        contato_id = await obter_ou_criar_contato(
            jid=sender_jid,
            nome=mensagem.nome_contato,
            telefone=mensagem.telefone
        )

        # Salvar mensagem
        mensagem_id = await salvar_mensagem_grupo(
            grupo_id=grupo_id,
            contato_id=contato_id,
            mensagem=mensagem,
            dados_raw=dados_raw
        )

        # Atualizar contadores
        await atualizar_contadores_grupo(grupo_id)

        return mensagem_id

    except Exception as e:
        logger.error(f"Erro ao ingerir mensagem de grupo: {e}", exc_info=True)
        return None
```

**Estimativa:** 2h

---

### S02.2 - Criar função SQL para incrementar contadores

**Descrição:** Criar função RPC para incrementar contadores de forma atômica.

**Critérios de Aceite:**
- [ ] Função criada
- [ ] Migration aplicada

**Schema:**
```sql
-- Função para incrementar contador de mensagens do grupo
CREATE OR REPLACE FUNCTION incrementar_mensagens_grupo(p_grupo_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE grupos_whatsapp
    SET
        total_mensagens = total_mensagens + 1,
        ultima_mensagem_em = now(),
        updated_at = now()
    WHERE id = p_grupo_id;
END;
$$ LANGUAGE plpgsql;

-- Função para incrementar contador de mensagens do contato
CREATE OR REPLACE FUNCTION incrementar_mensagens_contato(p_contato_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE contatos_grupo
    SET
        total_mensagens = total_mensagens + 1,
        ultimo_contato = now(),
        updated_at = now()
    WHERE id = p_contato_id;
END;
$$ LANGUAGE plpgsql;
```

**Estimativa:** 0.5h

---

### S02.3 - Modificar parser.py para chamar ingestor

**Descrição:** Alterar o parser para salvar mensagens de grupo antes de ignorá-las.

**Critérios de Aceite:**
- [ ] Parser modificado
- [ ] Mensagens de grupo sendo salvas
- [ ] Testes atualizados
- [ ] Julia continua NÃO respondendo em grupos

**Modificação em `app/services/parser.py`:**
```python
# Adicionar import
from app.services.grupos.ingestor import ingerir_mensagem_grupo

# Modificar função parsear_mensagem ou onde trata grupos
async def processar_webhook(data: dict) -> Optional[MensagemRecebida]:
    """Processa webhook e decide o que fazer."""
    mensagem = parsear_mensagem(data)

    if not mensagem:
        return None

    # Se é grupo, salvar mas não processar
    if mensagem.is_grupo:
        logger.debug(f"Mensagem de grupo detectada: {mensagem.message_id}")

        # Ingerir para processamento posterior (async, não bloqueia)
        await ingerir_mensagem_grupo(mensagem, data)

        # Retorna None para indicar que não deve responder
        return None

    # Continua processamento normal para DMs...
    return mensagem
```

**Arquivo afetado:** `app/services/parser.py`

**Estimativa:** 1h

---

### S02.4 - Criar pre-processor de ingestão (alternativa)

**Descrição:** Criar pre-processor no pipeline para ingestão de grupos.

**Critérios de Aceite:**
- [ ] Pre-processor criado
- [ ] Integrado ao pipeline
- [ ] Testes

**Código:**
```python
# app/pipeline/pre_processors.py (adicionar)

from app.services.grupos.ingestor import ingerir_mensagem_grupo


class IngestaoGrupoProcessor(PreProcessor):
    """
    Processa mensagens de grupo para ingestão.

    Salva a mensagem para processamento posterior mas
    NÃO permite que o pipeline continue (Julia não responde).

    Prioridade: 5 (antes do ParseMessageProcessor)
    """
    name = "ingestao_grupo"
    priority = 5

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        data = context.mensagem_raw

        # Verificar se é grupo
        remote_jid = data.get("key", {}).get("remoteJid", "")
        if "@g.us" not in remote_jid:
            # Não é grupo, continuar pipeline normal
            return ProcessorResult(success=True, should_continue=True)

        # É grupo - ingerir e parar pipeline
        try:
            from app.services.parser import parsear_mensagem
            mensagem = parsear_mensagem(data)

            if mensagem:
                mensagem_id = await ingerir_mensagem_grupo(mensagem, data)
                return ProcessorResult(
                    success=True,
                    should_continue=False,  # NÃO continua (não responde)
                    metadata={
                        "motivo": "mensagem_grupo_ingerida",
                        "mensagem_id": str(mensagem_id) if mensagem_id else None
                    }
                )
        except Exception as e:
            logger.error(f"Erro na ingestão de grupo: {e}")

        return ProcessorResult(
            success=True,
            should_continue=False,
            metadata={"motivo": "mensagem_grupo_erro_ingestao"}
        )
```

**Estimativa:** 1h

---

### S02.5 - Criar estrutura de diretório do módulo grupos

**Descrição:** Criar estrutura inicial do módulo `app/services/grupos/`.

**Critérios de Aceite:**
- [ ] Diretório criado
- [ ] `__init__.py` com exports
- [ ] Estrutura organizada

**Estrutura:**
```
app/services/grupos/
├── __init__.py
├── ingestor.py          # S02.1
├── classificador.py     # E03
├── extrator.py          # E05
├── normalizador.py      # E06
├── deduplicador.py      # E09
├── importador.py        # E10
└── worker.py            # E11 (orquestração)
```

**Código `__init__.py`:**
```python
"""
Módulo de processamento de mensagens de grupos WhatsApp.

Responsável por:
- Ingestão de mensagens
- Classificação de ofertas
- Extração de dados estruturados
- Normalização com entidades do banco
- Deduplicação de vagas
- Importação para tabela de vagas
"""

from app.services.grupos.ingestor import ingerir_mensagem_grupo

__all__ = [
    "ingerir_mensagem_grupo",
]
```

**Estimativa:** 0.25h

---

### S02.6 - Testes de ingestão

**Descrição:** Criar testes para o módulo de ingestão.

**Critérios de Aceite:**
- [ ] Testes de `obter_ou_criar_grupo`
- [ ] Testes de `obter_ou_criar_contato`
- [ ] Testes de `salvar_mensagem_grupo`
- [ ] Testes de `ingerir_mensagem_grupo`
- [ ] Mocks do Supabase

**Arquivo:** `tests/grupos/test_ingestor.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.grupos.ingestor import (
    obter_ou_criar_grupo,
    obter_ou_criar_contato,
    salvar_mensagem_grupo,
    ingerir_mensagem_grupo,
)
from app.schemas.mensagem import MensagemRecebida


class TestObterOuCriarGrupo:
    """Testes para obter_ou_criar_grupo."""

    @pytest.mark.asyncio
    async def test_grupo_existente(self, mock_supabase):
        """Deve retornar ID de grupo existente."""
        grupo_id = uuid4()
        mock_supabase.table().select().eq().execute.return_value.data = [
            {"id": str(grupo_id)}
        ]

        result = await obter_ou_criar_grupo("123@g.us")

        assert result == grupo_id

    @pytest.mark.asyncio
    async def test_criar_novo_grupo(self, mock_supabase):
        """Deve criar novo grupo se não existir."""
        grupo_id = uuid4()

        # Primeiro select retorna vazio
        mock_supabase.table().select().eq().execute.return_value.data = []
        # Insert retorna novo ID
        mock_supabase.table().insert().execute.return_value.data = [
            {"id": str(grupo_id)}
        ]

        result = await obter_ou_criar_grupo("123@g.us", "Grupo Teste")

        assert result == grupo_id
        mock_supabase.table().insert.assert_called_once()


class TestObterOuCriarContato:
    """Testes para obter_ou_criar_contato."""

    @pytest.mark.asyncio
    async def test_contato_existente_atualiza_nome(self, mock_supabase):
        """Deve atualizar nome de contato existente."""
        contato_id = uuid4()
        mock_supabase.table().select().eq().execute.return_value.data = [
            {"id": str(contato_id)}
        ]

        result = await obter_ou_criar_contato(
            "5511999@s.whatsapp.net",
            "Novo Nome"
        )

        assert result == contato_id
        mock_supabase.table().update.assert_called_once()

    @pytest.mark.asyncio
    async def test_criar_novo_contato(self, mock_supabase):
        """Deve criar novo contato se não existir."""
        contato_id = uuid4()

        mock_supabase.table().select().eq().execute.return_value.data = []
        mock_supabase.table().insert().execute.return_value.data = [
            {"id": str(contato_id)}
        ]

        result = await obter_ou_criar_contato(
            "5511999@s.whatsapp.net",
            "Dr. João",
            "5511999999999"
        )

        assert result == contato_id


class TestSalvarMensagemGrupo:
    """Testes para salvar_mensagem_grupo."""

    @pytest.mark.asyncio
    async def test_salvar_mensagem_texto(self, mock_supabase):
        """Deve salvar mensagem de texto com status pendente."""
        mensagem_id = uuid4()
        mock_supabase.table().insert().execute.return_value.data = [
            {"id": str(mensagem_id)}
        ]

        mensagem = MensagemRecebida(
            telefone="5511999999999",
            message_id="ABC123",
            from_me=False,
            tipo="text",
            texto="Plantão disponível amanhã",
            nome_contato="Dr. João",
            timestamp=datetime.now(),
            is_grupo=True,
        )

        result = await salvar_mensagem_grupo(
            grupo_id=uuid4(),
            contato_id=uuid4(),
            mensagem=mensagem,
            dados_raw={"key": {"participant": "5511999@s.whatsapp.net"}}
        )

        assert result == mensagem_id

        # Verificar dados inseridos
        call_args = mock_supabase.table().insert.call_args
        dados = call_args[0][0]
        assert dados["status"] == "pendente"
        assert dados["tipo_midia"] == "texto"
        assert dados["tem_midia"] == False

    @pytest.mark.asyncio
    async def test_salvar_mensagem_imagem_ignorada(self, mock_supabase):
        """Deve salvar imagem com status ignorada_midia."""
        mensagem_id = uuid4()
        mock_supabase.table().insert().execute.return_value.data = [
            {"id": str(mensagem_id)}
        ]

        mensagem = MensagemRecebida(
            telefone="5511999999999",
            message_id="ABC123",
            from_me=False,
            tipo="image",
            texto=None,
            nome_contato="Dr. João",
            timestamp=datetime.now(),
            is_grupo=True,
        )

        result = await salvar_mensagem_grupo(
            grupo_id=uuid4(),
            contato_id=uuid4(),
            mensagem=mensagem,
            dados_raw={}
        )

        call_args = mock_supabase.table().insert.call_args
        dados = call_args[0][0]
        assert dados["status"] == "ignorada_midia"
        assert dados["tipo_midia"] == "imagem"

    @pytest.mark.asyncio
    async def test_salvar_mensagem_curta_ignorada(self, mock_supabase):
        """Deve ignorar mensagens muito curtas."""
        mensagem_id = uuid4()
        mock_supabase.table().insert().execute.return_value.data = [
            {"id": str(mensagem_id)}
        ]

        mensagem = MensagemRecebida(
            telefone="5511999999999",
            message_id="ABC123",
            from_me=False,
            tipo="text",
            texto="Ok",  # Muito curta
            nome_contato="Dr. João",
            timestamp=datetime.now(),
            is_grupo=True,
        )

        result = await salvar_mensagem_grupo(
            grupo_id=uuid4(),
            contato_id=uuid4(),
            mensagem=mensagem,
            dados_raw={}
        )

        call_args = mock_supabase.table().insert.call_args
        dados = call_args[0][0]
        assert dados["status"] == "ignorada_curta"


class TestIngerirMensagemGrupo:
    """Testes de integração para ingerir_mensagem_grupo."""

    @pytest.mark.asyncio
    async def test_fluxo_completo(self, mock_supabase):
        """Deve executar fluxo completo de ingestão."""
        grupo_id = uuid4()
        contato_id = uuid4()
        mensagem_id = uuid4()

        # Mocks
        mock_supabase.table().select().eq().execute.return_value.data = []
        mock_supabase.table().insert().execute.return_value.data = [
            {"id": str(grupo_id)}
        ]

        mensagem = MensagemRecebida(
            telefone="5511999999999",
            message_id="ABC123",
            from_me=False,
            tipo="text",
            texto="Vaga disponível Hospital São Luiz",
            nome_contato="Escalista",
            timestamp=datetime.now(),
            is_grupo=True,
        )

        dados_raw = {
            "key": {
                "remoteJid": "123456@g.us",
                "participant": "5511999999999@s.whatsapp.net"
            }
        }

        result = await ingerir_mensagem_grupo(mensagem, dados_raw)

        assert result is not None

    @pytest.mark.asyncio
    async def test_jids_ausentes(self, mock_supabase):
        """Deve retornar None se JIDs estiverem ausentes."""
        mensagem = MensagemRecebida(
            telefone="5511999999999",
            message_id="ABC123",
            from_me=False,
            tipo="text",
            texto="Teste",
            is_grupo=True,
        )

        result = await ingerir_mensagem_grupo(mensagem, {})

        assert result is None
```

**Estimativa:** 2h

---

### S02.7 - Fixture de mock do Supabase para testes

**Descrição:** Criar fixture reutilizável para mockar Supabase.

**Critérios de Aceite:**
- [ ] Fixture criada em `conftest.py`
- [ ] Reutilizável em todos os testes do módulo grupos

**Código em `tests/grupos/conftest.py`:**
```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase."""
    with patch("app.services.grupos.ingestor.supabase") as mock:
        # Configurar chain de métodos
        mock.table.return_value = mock
        mock.select.return_value = mock
        mock.insert.return_value = mock
        mock.update.return_value = mock
        mock.eq.return_value = mock
        mock.execute.return_value = MagicMock(data=[])
        mock.rpc.return_value = mock

        yield mock
```

**Estimativa:** 0.5h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S02.1 | Serviço de ingestão | 2h |
| S02.2 | Função SQL contadores | 0.5h |
| S02.3 | Modificar parser.py | 1h |
| S02.4 | Pre-processor (alternativa) | 1h |
| S02.5 | Estrutura diretório | 0.25h |
| S02.6 | Testes de ingestão | 2h |
| S02.7 | Fixture mock Supabase | 0.5h |

**Total:** 7.25h (~1 dia)

## Dependências

- E01 (Modelo de Dados) - Tabelas precisam existir

## Entregáveis

- Módulo `app/services/grupos/`
- Ingestão funcionando
- Testes passando
- Julia continua não respondendo em grupos
