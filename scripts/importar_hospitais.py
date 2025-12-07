"""
Script para importar hospitais por região.
"""
import sys
import asyncio
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.supabase import supabase
from app.config.regioes import REGIOES


async def importar_hospitais_regiao(regiao: str, hospitais: list[dict]):
    """
    Importa lista de hospitais para uma região.

    Formato esperado:
    [{
        "nome": "Hospital ABC",
        "endereco": "Rua X, 123",
        "cidade": "Santo André",
        "cnpj": "00.000.000/0001-00",
        "contato": "contato@hospital.com",
        "especialidades": ["anestesiologia", "cardiologia"]
    }]
    """
    if regiao not in REGIOES:
        print(f"❌ Região '{regiao}' não encontrada")
        return
    
    print(f"Importando hospitais para região: {REGIOES[regiao]['nome']}")
    
    for hosp in hospitais:
        # Verificar se já existe
        existente_resp = (
            supabase.table("hospitais")
            .select("id")
            .eq("cnpj", hosp.get("cnpj"))
            .execute()
        )
        
        if existente_resp.data:
            print(f"⚠️  Hospital já existe: {hosp['nome']}")
            continue
        
        # Inserir hospital
        hospital_resp = (
            supabase.table("hospitais")
            .insert({
                "nome": hosp["nome"],
                "endereco": hosp.get("endereco"),
                "cidade": hosp["cidade"],
                "estado": "SP",
                "cnpj": hosp.get("cnpj"),
                "contato_email": hosp.get("contato"),
                "regiao": regiao,
                "status": "ativo"
            })
            .execute()
        )
        
        if not hospital_resp.data:
            print(f"❌ Erro ao inserir: {hosp['nome']}")
            continue
        
        hospital = hospital_resp.data[0]
        
        # Associar especialidades
        for esp_nome in hosp.get("especialidades", []):
            especialidade_resp = (
                supabase.table("especialidades")
                .select("id")
                .eq("nome", esp_nome)
                .single()
                .execute()
            )
            
            if especialidade_resp.data:
                # Verificar se já existe associação
                assoc_resp = (
                    supabase.table("hospital_especialidades")
                    .select("id")
                    .eq("hospital_id", hospital["id"])
                    .eq("especialidade_id", especialidade_resp.data["id"])
                    .execute()
                )
                
                if not assoc_resp.data:
                    supabase.table("hospital_especialidades").insert({
                        "hospital_id": hospital["id"],
                        "especialidade_id": especialidade_resp.data["id"]
                    }).execute()
        
        print(f"✅ Importado: {hosp['nome']}")


async def main():
    """Exemplo de uso."""
    # Exemplo de hospitais para ABC
    hospitais_abc = [
        {
            "nome": "Hospital Brasil",
            "endereco": "Av. Brasil, 1000",
            "cidade": "Santo André",
            "cnpj": "12.345.678/0001-90",
            "contato": "contato@hospitalbrasil.com.br",
            "especialidades": ["anestesiologia", "cardiologia", "clinica_medica"]
        },
        # Adicionar mais hospitais aqui
    ]
    
    print("Importando hospitais...")
    await importar_hospitais_regiao("abc", hospitais_abc)
    print("\n✅ Importação concluída")


if __name__ == "__main__":
    asyncio.run(main())

