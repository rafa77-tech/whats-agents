"""
Pacote de Bounded Contexts do Projeto Julia.

Este pacote organiza o código por contexto de domínio, seguindo os
princípios do Domain-Driven Design (DDD). Cada subpacote representa
um Bounded Context com suas próprias camadas de:

- domain.py: Modelos de domínio, Entidades e Value Objects
- application.py: Application Services (orquestração de casos de uso)
- repositories.py: Repositórios (acesso à persistência)

Referência: ADR-006 (Bounded Contexts) e ADR-007 (Sem SQL em Rotas)
"""
