"""
Warmer Engine - Sistema de aquecimento de chips WhatsApp.

Componentes:
- trust_score: Calculo multiparametrico de confianca
- human_simulator: Simulacao de comportamento humano
- conversation_generator: Geracao de conversas naturais
- pairing_engine: Pareamento de chips para warmup
- scheduler: Agendamento de atividades
- orchestrator: Orquestracao do ciclo de warming
- early_warning: Deteccao precoce de problemas
- meta_rag: RAG de politicas Meta/WhatsApp
"""

from app.services.warmer.trust_score import (
    TrustScoreEngine,
    TrustLevel,
    TrustFactors,
    Permissoes,
    calcular_trust_score,
    obter_trust_score_cached,
    obter_permissoes,
)

# Nota: HumanSimulator não é usado pelo warming pipeline (executor envia direto).
# É usado por app.services.group_entry.worker para delays naturais em grupos.
from app.services.warmer.human_simulator import (
    HumanSimulator,
    HumanProfile,
    TypingSpeed,
    get_simulator,
    simular_envio_natural,
)

from app.services.warmer.conversation_generator import (
    ConversationGenerator,
    TipoConversa,
    TipoMidia,
    MensagemGerada,
    gerar_mensagem_inicial,
)

from app.services.warmer.pairing_engine import (
    PairingEngine,
    ParInfo,
    ChipInfo,
    encontrar_par,
    criar_pares,
)

from app.services.warmer.scheduler import (
    WarmingScheduler,
    AtividadeAgendada,
    TipoAtividade,
    planejar_dia_chip,
    obter_proximas,
)

from app.services.warmer.orchestrator import (
    WarmingOrchestrator,
    FaseWarmup,
    CriteriosTransicao,
    iniciar_warmup,
    pausar_warmup,
    executar_ciclo,
    status_pool,
)

from app.services.warmer.early_warning import (
    EarlyWarningSystem,
    Alerta,
    TipoAlerta,
    SeveridadeAlerta,
    analisar_chip,
    monitorar_pool,
    obter_alertas,
)

from app.services.warmer.meta_rag import (
    seed_politicas,
    consultar_politicas,
    verificar_conformidade,
    listar_categorias,
    buscar_por_categoria,
)

__all__ = [
    # Trust Score
    "TrustScoreEngine",
    "TrustLevel",
    "TrustFactors",
    "Permissoes",
    "calcular_trust_score",
    "obter_trust_score_cached",
    "obter_permissoes",
    # Human Simulator
    "HumanSimulator",
    "HumanProfile",
    "TypingSpeed",
    "get_simulator",
    "simular_envio_natural",
    # Conversation Generator
    "ConversationGenerator",
    "TipoConversa",
    "TipoMidia",
    "MensagemGerada",
    "gerar_mensagem_inicial",
    # Pairing Engine
    "PairingEngine",
    "ParInfo",
    "ChipInfo",
    "encontrar_par",
    "criar_pares",
    # Scheduler
    "WarmingScheduler",
    "AtividadeAgendada",
    "TipoAtividade",
    "planejar_dia_chip",
    "obter_proximas",
    # Orchestrator
    "WarmingOrchestrator",
    "FaseWarmup",
    "CriteriosTransicao",
    "iniciar_warmup",
    "pausar_warmup",
    "executar_ciclo",
    "status_pool",
    # Early Warning
    "EarlyWarningSystem",
    "Alerta",
    "TipoAlerta",
    "SeveridadeAlerta",
    "analisar_chip",
    "monitorar_pool",
    "obter_alertas",
    # Meta RAG
    "seed_politicas",
    "consultar_politicas",
    "verificar_conformidade",
    "listar_categorias",
    "buscar_por_categoria",
]
