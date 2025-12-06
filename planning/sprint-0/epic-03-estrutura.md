# Epic 3: Estrutura do Projeto

## Objetivo do Epic

> **Criar a estrutura base do projeto FastAPI com todos os clientes de integração.**

Este epic estabelece a fundação de código sobre a qual as próximas sprints serão construídas.

---

## Stories

1. [S0.E3.1 - Criar estrutura FastAPI](#s0e31---criar-estrutura-fastapi)
2. [S0.E3.2 - Configurar cliente Supabase](#s0e32---configurar-cliente-supabase)
3. [S0.E3.3 - Configurar cliente Anthropic](#s0e33---configurar-cliente-anthropic)
4. [S0.E3.4 - Configurar cliente Evolution](#s0e34---configurar-cliente-evolution)
5. [S0.E3.5 - Criar arquivo .env completo](#s0e35---criar-arquivo-env-completo)

---

# S0.E3.1 - Criar estrutura FastAPI

## Objetivo

> **Criar a estrutura de diretórios e arquivos base do projeto FastAPI.**

Esta é a fundação do código. Uma estrutura bem organizada facilita o desenvolvimento nas próximas sprints.

**Resultado esperado:** Projeto FastAPI rodando localmente com endpoint de health check.

---

## Contexto

- Usamos FastAPI por ser async e ter boa documentação automática
- Estrutura modular para facilitar manutenção
- Cada módulo (agente, whatsapp, etc) em seu diretório

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Python 3.13+ instalado
- [ ] uv instalado (`pip install uv`)
- [ ] Repositório clonado

---

## Tarefas

### 1. Criar estrutura de diretórios

```bash
cd /Users/rafaelpivovar/Documents/Projetos/whatsapp-api

# Criar diretórios
mkdir -p app/{api,core,services,models,schemas}
mkdir -p app/api/routes
mkdir -p tests

# Criar arquivos __init__.py
touch app/__init__.py
touch app/api/__init__.py
touch app/api/routes/__init__.py
touch app/core/__init__.py
touch app/services/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch tests/__init__.py
```

### 2. Criar arquivo principal (main.py)

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/main.py << 'EOF'
"""
Agente Júlia - API Principal
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação."""
    # Startup
    print(f"🚀 Iniciando {settings.APP_NAME}...")
    yield
    # Shutdown
    print(f"👋 Encerrando {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Agente Júlia - Escalista Virtual para Staffing Médico",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health.router, tags=["Health"])


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }
EOF
```

### 3. Criar configuração (config.py)

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/core/config.py << 'EOF'
"""
Configurações da aplicação.
Carrega variáveis de ambiente.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configurações carregadas do .env"""

    # App
    APP_NAME: str = "Agente Júlia"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-3-5-haiku-20241022"
    LLM_MODEL_COMPLEX: str = "claude-sonnet-4-20250514"

    # Evolution API
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "julia"

    # Chatwoot
    CHATWOOT_URL: str = "http://localhost:3000"
    CHATWOOT_API_KEY: str = ""
    CHATWOOT_ACCOUNT_ID: int = 1
    CHATWOOT_INBOX_ID: int = 1

    # Slack
    SLACK_WEBHOOK_URL: str = ""
    SLACK_CHANNEL: str = "#julia-gestao"

    # Rate Limiting
    MAX_MSGS_POR_HORA: int = 20
    MAX_MSGS_POR_DIA: int = 100
    HORARIO_INICIO: str = "08:00"
    HORARIO_FIM: str = "20:00"

    # Empresa
    NOME_EMPRESA: str = "Revoluna"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


settings = get_settings()
EOF
```

### 4. Criar rota de health check

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/health.py << 'EOF'
"""
Rotas de health check.
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Verifica se a API está funcionando.
    Usado para monitoramento e load balancers.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "julia-api",
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Verifica se a API está pronta para receber requests.
    Pode incluir verificações de dependências.
    """
    # TODO: Adicionar verificações de Supabase, Evolution, etc.
    return {
        "status": "ready",
        "checks": {
            "database": "ok",  # TODO: verificar conexão real
            "evolution": "ok",  # TODO: verificar conexão real
        },
    }
EOF
```

### 5. Atualizar pyproject.toml

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/pyproject.toml << 'EOF'
[project]
name = "julia-agent"
version = "0.1.0"
description = "Agente Júlia - Escalista Virtual para Staffing Médico"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.26.0",
    "supabase>=2.3.0",
    "anthropic>=0.18.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.black]
line-length = 100
target-version = ["py313"]
EOF
```

### 6. Instalar dependências

```bash
cd /Users/rafaelpivovar/Documents/Projetos/whatsapp-api
uv sync
```

### 7. Criar script de execução

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/run.sh << 'EOF'
#!/bin/bash
# Script para rodar a aplicação

# Carregar variáveis de ambiente
set -a
source .env
set +a

# Rodar com uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF

chmod +x /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/run.sh
```

### 8. Testar a aplicação

```bash
cd /Users/rafaelpivovar/Documents/Projetos/whatsapp-api

# Criar .env mínimo para teste
cat > .env << 'EOF'
APP_NAME=Agente Júlia
ENVIRONMENT=development
DEBUG=true
EOF

# Rodar
uv run uvicorn app.main:app --reload --port 8000
```

Em outro terminal:

```bash
# Testar endpoints
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# Acessar docs
open http://localhost:8000/docs
```

---

## Como Testar

1. `curl http://localhost:8000/` → retorna JSON com status
2. `curl http://localhost:8000/health` → retorna `{"status": "healthy"}`
3. `http://localhost:8000/docs` → mostra Swagger UI

---

## DoD (Definition of Done)

- [ ] Diretórios criados: `app/`, `app/api/`, `app/core/`, `app/services/`, `app/models/`
- [ ] Arquivo `app/main.py` criado e funcional
- [ ] Arquivo `app/core/config.py` criado
- [ ] Arquivo `app/api/routes/health.py` criado
- [ ] `pyproject.toml` atualizado com dependências
- [ ] Dependências instaladas (`uv sync`)
- [ ] Aplicação roda sem erros (`uvicorn app.main:app`)
- [ ] Endpoint `/health` retorna status healthy
- [ ] Swagger UI acessível em `/docs`

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `ModuleNotFoundError` | Import errado | Verificar estrutura de pastas e `__init__.py` |
| `pydantic_settings not found` | Dependência faltando | `uv sync` |
| Porta em uso | Outro processo | Usar outra porta: `--port 8001` |

---
---

# S0.E3.2 - Configurar cliente Supabase

## Objetivo

> **Criar módulo de conexão com Supabase para operações de banco de dados.**

O Supabase é nossa fonte de verdade para todos os dados.

**Resultado esperado:** Cliente Supabase funcionando, conseguimos fazer queries.

---

## Contexto

- Supabase usa biblioteca Python oficial
- Conexão via URL + Service Key
- Todas as operações de banco passam por este cliente

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Story S0.E3.1 completa (estrutura FastAPI)
- [ ] Supabase URL e Service Key disponíveis

---

## Tarefas

### 1. Criar módulo do cliente Supabase

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/supabase.py << 'EOF'
"""
Cliente Supabase para operações de banco de dados.
"""
from supabase import create_client, Client
from functools import lru_cache

from app.core.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Retorna cliente Supabase cacheado.
    Usa service key para acesso completo.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios")

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )


# Instância global (use via dependency injection quando possível)
supabase = get_supabase_client()


# Funções auxiliares para operações comuns
async def get_medico_by_telefone(telefone: str) -> dict | None:
    """Busca médico pelo telefone."""
    response = supabase.table("clientes").select("*").eq("telefone", telefone).execute()
    return response.data[0] if response.data else None


async def get_medico_by_id(medico_id: str) -> dict | None:
    """Busca médico pelo ID."""
    response = supabase.table("clientes").select("*").eq("id", medico_id).execute()
    return response.data[0] if response.data else None


async def get_vagas_disponiveis(especialidade_id: str, limit: int = 10) -> list:
    """Busca vagas abertas para uma especialidade."""
    response = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*)")
        .eq("especialidade_id", especialidade_id)
        .eq("status", "aberta")
        .gte("data_plantao", "now()")
        .order("prioridade", desc=True)
        .order("data_plantao")
        .limit(limit)
        .execute()
    )
    return response.data


async def criar_conversa(cliente_id: str, origem: str = "prospecção") -> dict:
    """Cria nova conversa para um médico."""
    response = (
        supabase.table("conversations")
        .insert({
            "cliente_id": cliente_id,
            "status": "aberta",
            "controlled_by": "ai",
            "origem": origem,
        })
        .execute()
    )
    return response.data[0] if response.data else None


async def salvar_interacao(
    conversa_id: str,
    tipo: str,
    conteudo: str,
    remetente: str
) -> dict:
    """Salva uma interação (mensagem) na conversa."""
    response = (
        supabase.table("interacoes")
        .insert({
            "conversation_id": conversa_id,
            "tipo": tipo,
            "conteudo": conteudo,
            "remetente": remetente,
        })
        .execute()
    )
    return response.data[0] if response.data else None
EOF
```

### 2. Criar rota de teste

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/test_db.py << 'EOF'
"""
Rotas de teste para validar conexão com banco.
Remover em produção.
"""
from fastapi import APIRouter, HTTPException

from app.services.supabase import supabase

router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/db/connection")
async def test_db_connection():
    """Testa conexão com Supabase."""
    try:
        # Tentar uma query simples
        response = supabase.table("especialidades").select("count").execute()
        return {
            "status": "connected",
            "message": "Conexão com Supabase OK",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")


@router.get("/db/medicos/count")
async def count_medicos():
    """Conta médicos na base."""
    try:
        response = supabase.table("clientes").select("id", count="exact").execute()
        return {
            "total_medicos": response.count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.get("/db/medicos/piloto")
async def get_medicos_piloto():
    """Lista médicos do grupo piloto."""
    try:
        response = (
            supabase.table("clientes")
            .select("id, primeiro_nome, sobrenome, crm, telefone")
            .eq("grupo_piloto", True)
            .limit(10)
            .execute()
        )
        return {
            "count": len(response.data),
            "sample": response.data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
EOF
```

### 3. Registrar rota no main.py

Adicione no `app/main.py`:

```python
from app.api.routes import health, test_db

# ...

app.include_router(health.router, tags=["Health"])
app.include_router(test_db.router)  # Adicionar esta linha
```

### 4. Testar conexão

```bash
# Certifique-se que .env tem SUPABASE_URL e SUPABASE_SERVICE_KEY

curl http://localhost:8000/test/db/connection
# Deve retornar: {"status": "connected", ...}

curl http://localhost:8000/test/db/medicos/count
# Deve retornar: {"total_medicos": 29645}
```

---

## Como Testar

1. `GET /test/db/connection` → `{"status": "connected"}`
2. `GET /test/db/medicos/count` → retorna número de médicos
3. `GET /test/db/medicos/piloto` → retorna amostra (se piloto marcado)

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/supabase.py` criado
- [ ] Funções auxiliares implementadas (`get_medico_by_telefone`, etc)
- [ ] Rota de teste `/test/db/connection` funciona
- [ ] Consegue contar médicos na base
- [ ] Nenhum erro de conexão

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `ValueError: SUPABASE_URL` | Variáveis não configuradas | Verificar `.env` |
| `AuthApiError` | Service key inválida | Verificar key no Supabase |
| `relation does not exist` | Tabela não existe | Verificar migrations |

---
---

# S0.E3.3 - Configurar cliente Anthropic

## Objetivo

> **Criar módulo de conexão com Claude API para geração de respostas.**

O Anthropic Claude é o cérebro da Júlia.

**Resultado esperado:** Cliente Anthropic funcionando, conseguimos gerar respostas.

---

## Contexto

- Usamos biblioteca oficial `anthropic`
- Modelo principal: Claude 3.5 Haiku (barato e rápido)
- Modelo complexo: Claude Sonnet 4 (para negociações)

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Story S0.E1.1 completa (API key disponível)
- [ ] Story S0.E3.1 completa (estrutura FastAPI)

---

## Tarefas

### 1. Criar módulo do cliente Anthropic

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/llm.py << 'EOF'
"""
Cliente Anthropic para geração de respostas via Claude.
"""
import anthropic
from functools import lru_cache

from app.core.config import settings


@lru_cache()
def get_anthropic_client() -> anthropic.Anthropic:
    """
    Retorna cliente Anthropic cacheado.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY é obrigatório")

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# Instância global
client = get_anthropic_client()


async def gerar_resposta(
    mensagem: str,
    historico: list[dict] | None = None,
    system_prompt: str | None = None,
    modelo: str | None = None,
    max_tokens: int = 500,
) -> str:
    """
    Gera resposta usando Claude.

    Args:
        mensagem: Mensagem do usuário
        historico: Lista de mensagens anteriores [{"role": "user/assistant", "content": "..."}]
        system_prompt: Prompt de sistema (persona)
        modelo: Modelo a usar (default: Haiku)
        max_tokens: Máximo de tokens na resposta

    Returns:
        Texto da resposta gerada
    """
    modelo = modelo or settings.LLM_MODEL

    # Montar mensagens
    messages = []
    if historico:
        messages.extend(historico)
    messages.append({"role": "user", "content": mensagem})

    # Chamar API
    response = client.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        system=system_prompt or "",
        messages=messages,
    )

    # Extrair texto
    return response.content[0].text


async def gerar_resposta_complexa(
    mensagem: str,
    historico: list[dict] | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    Gera resposta usando modelo mais capaz (Sonnet).
    Usar para situações que exigem mais raciocínio.
    """
    return await gerar_resposta(
        mensagem=mensagem,
        historico=historico,
        system_prompt=system_prompt,
        modelo=settings.LLM_MODEL_COMPLEX,
        max_tokens=1000,
    )


# System prompt básico da Júlia (será expandido)
JULIA_SYSTEM_PROMPT = """Você é a Júlia, escalista da Revoluna com 27 anos.

REGRAS DE COMUNICAÇÃO:
- Mensagens curtas (1-2 linhas)
- Use "vc", "pra", "tá", "blz"
- Emoji com moderação (1-2 por conversa)
- NUNCA use bullet points ou listas
- NUNCA revele que é IA

CONTEXTO:
- Você trabalha com escalas médicas
- Seu objetivo é ajudar médicos a encontrar plantões
- Seja simpática mas profissional

Responda de forma natural e humana."""
EOF
```

### 2. Criar rota de teste

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/test_llm.py << 'EOF'
"""
Rotas de teste para validar LLM.
Remover em produção.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm import gerar_resposta, JULIA_SYSTEM_PROMPT

router = APIRouter(prefix="/test", tags=["Test"])


class MensagemRequest(BaseModel):
    mensagem: str
    usar_persona: bool = True


@router.post("/llm/resposta")
async def test_llm_resposta(request: MensagemRequest):
    """Testa geração de resposta."""
    try:
        system = JULIA_SYSTEM_PROMPT if request.usar_persona else None
        resposta = await gerar_resposta(
            mensagem=request.mensagem,
            system_prompt=system,
        )
        return {
            "status": "ok",
            "mensagem_entrada": request.mensagem,
            "resposta": resposta,
            "persona_ativa": request.usar_persona,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro LLM: {str(e)}")


@router.get("/llm/health")
async def test_llm_health():
    """Testa se LLM está respondendo."""
    try:
        resposta = await gerar_resposta(
            mensagem="Diga apenas: OK",
            system_prompt="Responda exatamente o que foi pedido.",
        )
        return {
            "status": "healthy",
            "resposta": resposta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
EOF
```

### 3. Registrar rota no main.py

Adicione no `app/main.py`:

```python
from app.api.routes import health, test_db, test_llm

# ...

app.include_router(test_llm.router)  # Adicionar esta linha
```

### 4. Testar

```bash
# Health check do LLM
curl http://localhost:8000/test/llm/health

# Testar resposta com persona
curl -X POST http://localhost:8000/test/llm/resposta \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Oi, tudo bem?", "usar_persona": true}'

# Testar resposta sem persona
curl -X POST http://localhost:8000/test/llm/resposta \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Qual a capital do Brasil?", "usar_persona": false}'
```

---

## Como Testar

1. `GET /test/llm/health` → `{"status": "healthy"}`
2. `POST /test/llm/resposta` com persona → resposta informal
3. Verificar que resposta usa "vc", "pra", etc quando persona ativa

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/llm.py` criado
- [ ] Função `gerar_resposta()` implementada
- [ ] Função `gerar_resposta_complexa()` implementada
- [ ] `JULIA_SYSTEM_PROMPT` básico definido
- [ ] Rota `/test/llm/health` funciona
- [ ] Rota `/test/llm/resposta` gera respostas
- [ ] Resposta com persona usa linguagem informal

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `ValueError: ANTHROPIC_API_KEY` | Key não configurada | Verificar `.env` |
| `AuthenticationError` | Key inválida | Verificar key no Anthropic |
| `RateLimitError` | Muitas requisições | Esperar ou aumentar limite |

---
---

# S0.E3.4 - Configurar cliente Evolution

## Objetivo

> **Criar módulo de conexão com Evolution API para enviar/receber mensagens WhatsApp.**

A Evolution é nossa ponte com o WhatsApp.

**Resultado esperado:** Cliente Evolution funcionando, conseguimos enviar mensagens.

---

## Contexto

- Evolution API é REST
- Autenticação via header `apikey`
- Instância "julia" já deve estar criada e conectada

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Story S0.E1.3 e S0.E1.4 completas (Evolution configurado e testado)
- [ ] Story S0.E3.1 completa (estrutura FastAPI)

---

## Tarefas

### 1. Criar módulo do cliente Evolution

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/whatsapp.py << 'EOF'
"""
Cliente Evolution API para WhatsApp.
"""
import httpx
from typing import Literal

from app.core.config import settings


class EvolutionClient:
    """Cliente para Evolution API."""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

        if not self.api_key:
            raise ValueError("EVOLUTION_API_KEY é obrigatório")

    @property
    def headers(self) -> dict:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def enviar_mensagem(self, telefone: str, texto: str) -> dict:
        """
        Envia mensagem de texto para um número.

        Args:
            telefone: Número no formato 5511999999999
            texto: Texto da mensagem

        Returns:
            Resposta da API
        """
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": telefone,
            "text": texto,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def enviar_presenca(
        self,
        telefone: str,
        presenca: Literal["available", "composing", "recording", "paused"]
    ) -> dict:
        """
        Envia status de presença (online, digitando, etc).

        Args:
            telefone: Número do destinatário
            presenca: Tipo de presença
        """
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"
        payload = {
            "number": telefone,
            "presence": presenca,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def marcar_como_lida(self, telefone: str, message_id: str) -> dict:
        """Marca mensagem como lida."""
        url = f"{self.base_url}/chat/markMessageAsRead/{self.instance}"
        payload = {
            "number": telefone,
            "messageId": message_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def verificar_conexao(self) -> dict:
        """Verifica status da conexão WhatsApp."""
        url = f"{self.base_url}/instance/connectionState/{self.instance}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()


# Instância global
evolution = EvolutionClient()


# Funções de conveniência
async def enviar_whatsapp(telefone: str, texto: str) -> dict:
    """Função de conveniência para enviar mensagem."""
    return await evolution.enviar_mensagem(telefone, texto)


async def mostrar_digitando(telefone: str) -> dict:
    """Mostra 'digitando...' para o contato."""
    return await evolution.enviar_presenca(telefone, "composing")


async def mostrar_online(telefone: str) -> dict:
    """Mostra status online para o contato."""
    return await evolution.enviar_presenca(telefone, "available")
EOF
```

### 2. Criar rota de teste

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/test_whatsapp.py << 'EOF'
"""
Rotas de teste para validar WhatsApp.
Remover em produção.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.whatsapp import evolution, enviar_whatsapp, mostrar_digitando

router = APIRouter(prefix="/test", tags=["Test"])


class MensagemWhatsAppRequest(BaseModel):
    telefone: str
    texto: str


@router.get("/whatsapp/status")
async def test_whatsapp_status():
    """Verifica status da conexão WhatsApp."""
    try:
        status = await evolution.verificar_conexao()
        return {
            "status": "ok",
            "conexao": status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/whatsapp/enviar")
async def test_enviar_mensagem(request: MensagemWhatsAppRequest):
    """
    Envia mensagem de teste.
    CUIDADO: Isso envia mensagem real!
    """
    try:
        # Mostrar digitando primeiro
        await mostrar_digitando(request.telefone)

        # Enviar mensagem
        resultado = await enviar_whatsapp(request.telefone, request.texto)

        return {
            "status": "enviado",
            "telefone": request.telefone,
            "resultado": resultado,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
EOF
```

### 3. Registrar rota no main.py

Adicione no `app/main.py`:

```python
from app.api.routes import health, test_db, test_llm, test_whatsapp

# ...

app.include_router(test_whatsapp.router)  # Adicionar
```

### 4. Testar

```bash
# Verificar conexão
curl http://localhost:8000/test/whatsapp/status

# Enviar mensagem (CUIDADO: envia de verdade!)
curl -X POST http://localhost:8000/test/whatsapp/enviar \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999", "texto": "Teste via API FastAPI!"}'
```

---

## Como Testar

1. `GET /test/whatsapp/status` → `{"status": "ok", "conexao": {"state": "open"}}`
2. Enviar mensagem de teste → mensagem chega no WhatsApp

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/whatsapp.py` criado
- [ ] Classe `EvolutionClient` implementada
- [ ] Métodos: `enviar_mensagem`, `enviar_presenca`, `marcar_como_lida`, `verificar_conexao`
- [ ] Funções de conveniência: `enviar_whatsapp`, `mostrar_digitando`
- [ ] Rota `/test/whatsapp/status` funciona
- [ ] Consegue enviar mensagem real (testado com número de teste)

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `Connection refused` | Evolution não está rodando | `docker compose up evolution-api` |
| `401 Unauthorized` | API key errada | Verificar `EVOLUTION_API_KEY` |
| `404 Not Found` | Instância não existe | Criar instância "julia" primeiro |

---
---

# S0.E3.5 - Criar arquivo .env completo

## Objetivo

> **Consolidar todas as variáveis de ambiente em um arquivo .env funcional.**

Todas as configurações em um só lugar, pronto para rodar.

**Resultado esperado:** Arquivo .env com todas as variáveis necessárias, aplicação roda completamente.

---

## Contexto

- `.env` não é commitado (está no .gitignore)
- `.env.example` é commitado como template
- Cada ambiente (dev, prod) tem seu próprio .env

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Todas as outras stories do Epic 1 completas (APIs configuradas)
- [ ] Todas as chaves/URLs disponíveis

---

## Tarefas

### 1. Atualizar .env.example

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/.env.example << 'EOF'
# ==============================================
# CONFIGURAÇÃO DO AGENTE JÚLIA
# ==============================================
# Copie este arquivo para .env e preencha os valores
# NUNCA commite o arquivo .env!

# ----------------------------------------------
# APP
# ----------------------------------------------
APP_NAME=Agente Júlia
ENVIRONMENT=development
DEBUG=true

# ----------------------------------------------
# SUPABASE (Banco de Dados)
# ----------------------------------------------
# URL do projeto Supabase
SUPABASE_URL=https://xxx.supabase.co

# Service Key (tem acesso total, não expor!)
SUPABASE_SERVICE_KEY=eyJ...

# ----------------------------------------------
# ANTHROPIC (Claude LLM)
# ----------------------------------------------
# API Key da Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Modelos
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# ----------------------------------------------
# EVOLUTION API (WhatsApp)
# ----------------------------------------------
# URL da Evolution API
EVOLUTION_API_URL=http://localhost:8080

# API Key (gerada no painel Evolution)
EVOLUTION_API_KEY=xxx

# Nome da instância WhatsApp
EVOLUTION_INSTANCE=julia

# ----------------------------------------------
# CHATWOOT (Supervisão)
# ----------------------------------------------
# URL do Chatwoot
CHATWOOT_URL=http://localhost:3000

# API Key (do perfil do usuário)
CHATWOOT_API_KEY=xxx

# IDs
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# ----------------------------------------------
# SLACK (Notificações)
# ----------------------------------------------
# Webhook URL do Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Canal para reports
SLACK_CHANNEL=#julia-gestao

# ----------------------------------------------
# RATE LIMITING (Crítico!)
# ----------------------------------------------
# Limites para evitar ban do WhatsApp
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100

# Horário de funcionamento
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# ----------------------------------------------
# EMPRESA
# ----------------------------------------------
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999
EOF
```

### 2. Criar .env real (com valores)

Copie o exemplo e preencha com valores reais:

```bash
cp .env.example .env
```

Edite `.env` e preencha:
- SUPABASE_URL e SUPABASE_SERVICE_KEY
- ANTHROPIC_API_KEY
- EVOLUTION_API_KEY
- CHATWOOT_API_KEY
- SLACK_WEBHOOK_URL

### 3. Verificar que .env está no .gitignore

```bash
cat .gitignore | grep -E "^\.env$"
# Deve mostrar: .env

# Se não estiver, adicionar:
echo ".env" >> .gitignore
```

### 4. Criar script de verificação

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/scripts/check_env.py << 'EOF'
#!/usr/bin/env python3
"""
Verifica se todas as variáveis de ambiente necessárias estão configuradas.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Variáveis obrigatórias
REQUIRED = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "ANTHROPIC_API_KEY",
    "EVOLUTION_API_URL",
    "EVOLUTION_API_KEY",
    "EVOLUTION_INSTANCE",
]

# Variáveis opcionais (mas recomendadas)
OPTIONAL = [
    "CHATWOOT_URL",
    "CHATWOOT_API_KEY",
    "SLACK_WEBHOOK_URL",
]

def check():
    print("🔍 Verificando variáveis de ambiente...\n")

    errors = []
    warnings = []

    # Verificar obrigatórias
    print("Obrigatórias:")
    for var in REQUIRED:
        value = os.getenv(var)
        if value:
            # Mascarar valores sensíveis
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✅ {var} = {masked}")
        else:
            print(f"  ❌ {var} = NÃO CONFIGURADA")
            errors.append(var)

    # Verificar opcionais
    print("\nOpcionais:")
    for var in OPTIONAL:
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✅ {var} = {masked}")
        else:
            print(f"  ⚠️  {var} = não configurada")
            warnings.append(var)

    # Resultado
    print("\n" + "=" * 50)
    if errors:
        print(f"❌ FALHOU: {len(errors)} variáveis obrigatórias faltando")
        print(f"   Faltam: {', '.join(errors)}")
        return False
    elif warnings:
        print(f"⚠️  OK com avisos: {len(warnings)} opcionais faltando")
        return True
    else:
        print("✅ TUDO OK!")
        return True


if __name__ == "__main__":
    import sys
    success = check()
    sys.exit(0 if success else 1)
EOF

chmod +x /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/scripts/check_env.py
```

### 5. Executar verificação

```bash
cd /Users/rafaelpivovar/Documents/Projetos/whatsapp-api
uv run python scripts/check_env.py
```

### 6. Testar aplicação completa

```bash
# Rodar aplicação
uv run uvicorn app.main:app --reload --port 8000

# Em outro terminal, testar todos os endpoints
curl http://localhost:8000/health
curl http://localhost:8000/test/db/connection
curl http://localhost:8000/test/llm/health
curl http://localhost:8000/test/whatsapp/status
```

---

## Como Testar

1. `python scripts/check_env.py` → mostra todas variáveis OK
2. Aplicação inicia sem erros
3. Todos os endpoints `/test/*` funcionam

---

## DoD (Definition of Done)

- [ ] Arquivo `.env.example` atualizado com todas as variáveis
- [ ] Arquivo `.env` criado com valores reais
- [ ] `.env` está no `.gitignore`
- [ ] Script `scripts/check_env.py` criado e funciona
- [ ] Todas as variáveis obrigatórias preenchidas
- [ ] Aplicação roda sem erros de configuração
- [ ] Endpoints de teste de todas as integrações funcionam

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `.env` commitado | Não está no gitignore | Adicionar e remover do git |
| Variável não carrega | Arquivo no lugar errado | Deve estar na raiz do projeto |
| Encoding errado | Caracteres especiais | Usar UTF-8 |
