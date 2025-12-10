#!/usr/bin/env python3
"""
Script de Teste Manual - Sprint 8
Testa validacao de output e aberturas via API

Uso:
    uv run python scripts/teste_manual_sprint8.py
"""

import httpx
import asyncio
from datetime import datetime


BASE_URL = "http://localhost:8000"


# Cores para output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def ok(msg: str) -> str:
    return f"{Colors.GREEN}✓{Colors.RESET} {msg}"


def fail(msg: str) -> str:
    return f"{Colors.RED}✗{Colors.RESET} {msg}"


def warn(msg: str) -> str:
    return f"{Colors.YELLOW}⚠{Colors.RESET} {msg}"


def info(msg: str) -> str:
    return f"{Colors.BLUE}ℹ{Colors.RESET} {msg}"


def header(msg: str) -> str:
    return f"\n{Colors.BOLD}{'='*60}\n{msg}\n{'='*60}{Colors.RESET}"


async def check_health(client: httpx.AsyncClient) -> bool:
    """Verifica se API esta rodando"""
    try:
        r = await client.get(f"{BASE_URL}/health")
        return r.status_code == 200
    except Exception:
        return False


async def test_validacao_endpoint(client: httpx.AsyncClient) -> dict:
    """Testa endpoint de validacao"""
    results = {"passed": 0, "failed": 0, "tests": []}

    casos = [
        # Deve passar
        {"texto": "Oi Dr Carlos! Tudo bem? Sou a Julia da Revoluna", "esperado_valido": True},
        {"texto": "Que bom! Deixa eu ver o que tenho pra vc", "esperado_valido": True},
        {"texto": "Show! Reservei pra vc entao", "esperado_valido": True},

        # Deve falhar - revelacao IA
        {"texto": "Sou uma inteligencia artificial treinada pela Anthropic", "esperado_valido": False},
        {"texto": "Como assistente virtual, posso ajudar", "esperado_valido": False},
        {"texto": "Sou a Julia, um bot da Revoluna", "esperado_valido": False},

        # Deve falhar - formato proibido
        {"texto": "Prezado Dr. Silva, venho por meio desta informar", "esperado_valido": False},
        {"texto": "• Vaga 1\n• Vaga 2\n• Vaga 3", "esperado_valido": False},
        {"texto": "**Vagas disponiveis:**\n- Hospital A\n- Hospital B", "esperado_valido": False},

        # Deve falhar - linguagem robotica
        {"texto": "Solicitacao recebida com sucesso. Aguarde processamento.", "esperado_valido": False},
        {"texto": "Atenciosamente, Julia - Equipe Revoluna", "esperado_valido": False},
    ]

    print(header("TESTE: Endpoint /admin/validacao/testar"))

    for caso in casos:
        try:
            r = await client.post(
                f"{BASE_URL}/admin/validacao/testar",
                json={"texto": caso["texto"]}
            )

            if r.status_code == 200:
                data = r.json()
                # A estrutura e: {"validacao": {"valido": bool, ...}, ...}
                valido = data.get("validacao", {}).get("valido", False)

                passou = valido == caso["esperado_valido"]

                texto_preview = caso["texto"][:50] + "..." if len(caso["texto"]) > 50 else caso["texto"]

                if passou:
                    results["passed"] += 1
                    status = ok(f"'{texto_preview}'")
                else:
                    results["failed"] += 1
                    status = fail(f"'{texto_preview}' (esperado={caso['esperado_valido']}, got={valido})")

                results["tests"].append({
                    "texto": caso["texto"],
                    "esperado": caso["esperado_valido"],
                    "resultado": valido,
                    "passou": passou,
                    "detalhes": data
                })

                print(f"  {status}")
            else:
                results["failed"] += 1
                print(fail(f"HTTP {r.status_code}"))

        except Exception as e:
            results["failed"] += 1
            print(fail(f"Erro: {e}"))

    return results


async def test_padroes_endpoint(client: httpx.AsyncClient) -> dict:
    """Testa endpoint de estatisticas de padroes"""
    results = {"passed": 0, "failed": 0}

    print(header("TESTE: Endpoint /admin/validacao/padroes"))

    try:
        r = await client.get(f"{BASE_URL}/admin/validacao/padroes")

        if r.status_code == 200:
            data = r.json()

            # Verificar estrutura
            if "categorias" in data:
                print(ok(f"Retornou {len(data['categorias'])} categorias"))
                results["passed"] += 1

                for cat, info in data["categorias"].items():
                    print(f"    - {cat}: {info.get('total', 0)} padroes")
            else:
                print(fail("Faltando campo 'categorias'"))
                results["failed"] += 1

            if "total_padroes" in data:
                print(ok(f"Total de padroes: {data['total_padroes']}"))
                results["passed"] += 1
            else:
                print(fail("Faltando campo 'total_padroes'"))
                results["failed"] += 1
        else:
            print(fail(f"HTTP {r.status_code}"))
            results["failed"] += 1

    except Exception as e:
        print(fail(f"Erro: {e}"))
        results["failed"] += 1

    return results


async def test_aberturas_endpoint(client: httpx.AsyncClient) -> dict:
    """Testa endpoint de aberturas"""
    results = {"passed": 0, "failed": 0}

    print(header("TESTE: Endpoint /admin/aberturas/variacao"))

    medico_teste = {
        "nome": "Dr. Teste Silva",
        "especialidade": "Anestesiologia",
        "regiao": "ABC",
        "crm": "123456-SP"
    }

    try:
        r = await client.post(
            f"{BASE_URL}/admin/aberturas/variacao",
            json=medico_teste
        )

        if r.status_code == 200:
            data = r.json()

            # Verificar campos
            if "mensagem" in data:
                msg = data["mensagem"]
                print(ok(f"Gerou abertura: '{msg[:60]}...'"))
                results["passed"] += 1

                # Validar formato da abertura
                checks = [
                    ("Informal (usa 'vc' ou similar)", any(x in msg.lower() for x in ["vc", "voce", "você"])),
                    ("Menciona Revoluna", "revoluna" in msg.lower()),
                    ("Nao usa bullets", "•" not in msg and "- " not in msg.split("\n")[0]),
                ]

                for check_name, passou in checks:
                    if passou:
                        print(f"    {ok(check_name)}")
                        results["passed"] += 1
                    else:
                        print(f"    {warn(check_name)}")
                        # Nao conta como falha, apenas warning
            else:
                print(fail("Faltando campo 'mensagem'"))
                results["failed"] += 1

            if "categoria" in data:
                print(ok(f"Categoria: {data['categoria']}")  )
                results["passed"] += 1

        else:
            print(fail(f"HTTP {r.status_code}"))
            results["failed"] += 1

    except Exception as e:
        print(fail(f"Erro: {e}"))
        results["failed"] += 1

    return results


async def test_aberturas_multiplas(client: httpx.AsyncClient) -> dict:
    """Testa variacao de aberturas (nao deve repetir)"""
    results = {"passed": 0, "failed": 0}

    print(header("TESTE: Variacao de Aberturas (5 geracoes)"))

    medico_teste = {
        "nome": "Dr. Teste",
        "especialidade": "Cardiologia",
    }

    aberturas = []
    categorias = set()

    try:
        for i in range(5):
            r = await client.post(
                f"{BASE_URL}/admin/aberturas/variacao",
                json=medico_teste
            )

            if r.status_code == 200:
                data = r.json()
                msg = data.get("mensagem", "")
                cat = data.get("categoria", "")

                aberturas.append(msg)
                categorias.add(cat)
                print(f"  {i+1}. [{cat}] {msg[:50]}...")
            else:
                print(fail(f"  {i+1}. HTTP {r.status_code}"))
                results["failed"] += 1

        # Verificar variacao
        unique = len(set(aberturas))
        if unique >= 3:
            print(ok(f"Boa variacao: {unique}/5 unicas"))
            results["passed"] += 1
        else:
            print(warn(f"Pouca variacao: {unique}/5 unicas"))

        if len(categorias) >= 2:
            print(ok(f"Categorias variadas: {categorias}"))
            results["passed"] += 1
        else:
            print(warn(f"Poucas categorias: {categorias}"))

    except Exception as e:
        print(fail(f"Erro: {e}"))
        results["failed"] += 1

    return results


async def test_correcao_automatica(client: httpx.AsyncClient) -> dict:
    """Testa correcao automatica de mensagens"""
    results = {"passed": 0, "failed": 0}

    print(header("TESTE: Correcao Automatica"))

    casos = [
        {
            "texto": "• Vaga 1: Hospital A\n• Vaga 2: Hospital B",
            "descricao": "Bullets -> texto corrido"
        },
        {
            "texto": "Prezado Dr. Silva, gostaria de informar que temos vagas disponíveis.",
            "descricao": "Formal -> informal"
        },
    ]

    for caso in casos:
        try:
            r = await client.post(
                f"{BASE_URL}/admin/validacao/corrigir",
                json={"texto": caso["texto"]}
            )

            if r.status_code == 200:
                data = r.json()
                corrigido = data.get("texto_corrigido", "")
                original = caso["texto"]

                # Verificar se mudou
                if corrigido != original:
                    print(ok(f"{caso['descricao']}"))
                    print(f"    Original:  {original[:50]}...")
                    print(f"    Corrigido: {corrigido[:50]}...")
                    results["passed"] += 1
                else:
                    print(warn(f"{caso['descricao']} - sem mudanca"))

            elif r.status_code == 404:
                print(warn(f"Endpoint /admin/validacao/corrigir nao existe"))
            else:
                print(fail(f"HTTP {r.status_code}"))
                results["failed"] += 1

        except Exception as e:
            print(fail(f"Erro: {e}"))
            results["failed"] += 1

    return results


async def main():
    print(f"\n{Colors.BOLD}TESTES MANUAIS - SPRINT 8{Colors.RESET}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Verificar API
        print(header("PRE-REQUISITO: API Health"))

        if not await check_health(client):
            print(fail("API nao esta respondendo!"))
            print(info("Execute: uv run uvicorn app.main:app --reload --port 8000"))
            return

        print(ok("API respondendo"))

        # Executar testes
        total_passed = 0
        total_failed = 0

        # Teste 1: Validacao
        r1 = await test_validacao_endpoint(client)
        total_passed += r1["passed"]
        total_failed += r1["failed"]

        # Teste 2: Padroes
        r2 = await test_padroes_endpoint(client)
        total_passed += r2["passed"]
        total_failed += r2["failed"]

        # Teste 3: Aberturas
        r3 = await test_aberturas_endpoint(client)
        total_passed += r3["passed"]
        total_failed += r3["failed"]

        # Teste 4: Variacao
        r4 = await test_aberturas_multiplas(client)
        total_passed += r4["passed"]
        total_failed += r4["failed"]

        # Teste 5: Correcao
        r5 = await test_correcao_automatica(client)
        total_passed += r5["passed"]
        total_failed += r5["failed"]

        # Resumo
        print(header("RESUMO"))
        print(f"  {ok(f'Passou: {total_passed}')}")
        print(f"  {fail(f'Falhou: {total_failed}') if total_failed > 0 else f'  Falhou: {total_failed}'}")

        if total_failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}TODOS OS TESTES PASSARAM!{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}Alguns testes falharam. Verifique os endpoints.{Colors.RESET}")


if __name__ == "__main__":
    asyncio.run(main())
