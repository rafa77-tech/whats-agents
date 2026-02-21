"""
Endpoints para jobs e tarefas agendadas.

Sprint 10 - S10.E3.1: Logica de negocio extraida para app/services/jobs/
Sprint 58 - Epic 1: Decomposicao em sub-routers por dominio.
"""

from fastapi import APIRouter

from .core import router as core_router
from .doctor_state import router as doctor_state_router
from .grupos import router as grupos_router
from .confirmacao import router as confirmacao_router
from .templates import router as templates_router
from .reconciliation import router as reconciliation_router
from .monitoring import router as monitoring_router
from .gatilhos import router as gatilhos_router
from .chips_ops import router as chips_ops_router
from .warming import router as warming_router
from .hospital_cleanup import router as hospital_cleanup_router
from .hospital_llm_review import router as hospital_llm_review_router
from .hospital_enrichment import router as hospital_enrichment_router
from .recovery import router as recovery_router
from .meta_quality import router as meta_quality_router
from .meta_analytics import router as meta_analytics_router
from .meta_mm_lite import router as meta_mm_lite_router
from .meta_catalog import router as meta_catalog_router

router = APIRouter(prefix="/jobs", tags=["Jobs"])
router.include_router(core_router)
router.include_router(doctor_state_router)
router.include_router(grupos_router)
router.include_router(confirmacao_router)
router.include_router(templates_router)
router.include_router(reconciliation_router)
router.include_router(monitoring_router)
router.include_router(gatilhos_router)
router.include_router(chips_ops_router)
router.include_router(warming_router)
router.include_router(hospital_cleanup_router)
router.include_router(hospital_llm_review_router)
router.include_router(hospital_enrichment_router)
router.include_router(recovery_router)
router.include_router(meta_quality_router)
router.include_router(meta_analytics_router)
router.include_router(meta_mm_lite_router)
router.include_router(meta_catalog_router)
