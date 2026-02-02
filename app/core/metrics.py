"""
Sistema de coleta de métricas de performance.
"""
import time
import logging
from functools import wraps
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

from app.core.timezone import agora_utc

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Coletor de métricas de performance."""
    
    def __init__(self):
        self.tempos: Dict[str, List[Dict]] = defaultdict(list)
        self.contadores: Dict[str, int] = defaultdict(int)
        self.erros: Dict[str, int] = defaultdict(int)

    def medir_tempo(self, nome: str):
        """Decorator para medir tempo de execução."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                inicio = time.time()
                try:
                    resultado = await func(*args, **kwargs)
                    self.registrar_tempo(nome, time.time() - inicio)
                    self.incrementar(f"{nome}_sucesso")
                    return resultado
                except Exception as e:
                    self.registrar_erro(nome, str(e))
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                inicio = time.time()
                try:
                    resultado = func(*args, **kwargs)
                    self.registrar_tempo(nome, time.time() - inicio)
                    self.incrementar(f"{nome}_sucesso")
                    return resultado
                except Exception as e:
                    self.registrar_erro(nome, str(e))
                    raise
            
            # Retornar wrapper apropriado
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
                return async_wrapper
            return sync_wrapper
        return decorator

    def registrar_tempo(self, nome: str, tempo: float):
        """Registra tempo de execução."""
        self.tempos[nome].append({
            "tempo": tempo,
            "timestamp": agora_utc().isoformat()
        })
        # Manter apenas últimos 1000
        if len(self.tempos[nome]) > 1000:
            self.tempos[nome] = self.tempos[nome][-1000:]

    def incrementar(self, nome: str):
        """Incrementa contador."""
        self.contadores[nome] += 1

    def registrar_erro(self, nome: str, erro: str):
        """Registra erro."""
        self.erros[nome] += 1
        self.incrementar(f"{nome}_erro")

    def obter_resumo(self) -> Dict[str, Any]:
        """Retorna resumo das métricas."""
        resumo: Dict[str, Any] = {
            "tempos": {},
            "contadores": dict(self.contadores),
            "erros": dict(self.erros)
        }

        for nome, tempos in self.tempos.items():
            valores = [t["tempo"] for t in tempos[-100:]]  # Últimos 100
            if valores:
                resumo["tempos"][nome] = {
                    "media_ms": sum(valores) / len(valores) * 1000,
                    "max_ms": max(valores) * 1000,
                    "min_ms": min(valores) * 1000,
                    "total": len(tempos),
                    "p95_ms": sorted(valores)[int(len(valores) * 0.95)] * 1000 if len(valores) > 20 else None
                }

        return resumo

    def limpar(self):
        """Limpa métricas antigas."""
        # Manter apenas últimos 1000 registros por métrica
        for nome in list(self.tempos.keys()):
            if len(self.tempos[nome]) > 1000:
                self.tempos[nome] = self.tempos[nome][-1000:]


# Instância global
metrics = MetricsCollector()

