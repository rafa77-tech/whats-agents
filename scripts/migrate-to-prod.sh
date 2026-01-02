#!/bin/bash
# Script de migração DEV -> PROD
# IMPORTANTE: Não commitar este arquivo com senhas!

# Caminhos dos certificados (renomeados para remover espaços)
CERT_DEV="/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data/supabase-dev.crt"
CERT_PROD="/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data/supabase-prod.crt"

# ============================================
# SENHAS URL-ENCODED (caracteres especiais escapados)
# @ -> %40, ! -> %21, ? -> %3F
# ============================================
# DEV: NerBr.LFcpfQN?9 (? encoded)
DEV_PASSWORD_ENCODED="NerBr.LFcpfQN%3F9"
# PROD: h@@_rP6nB!y7d2_ (@ e ! encoded)
PROD_PASSWORD_ENCODED="h%40%40_rP6nB%21y7d2_"

# Connection strings - CONEXÃO DIRETA (mais confiável para pg_dump)
DEV_DB="postgresql://postgres:${DEV_PASSWORD_ENCODED}@db.ofpnronthwcsybfxnxgj.supabase.co:5432/postgres?sslmode=require"
PROD_DB="postgresql://postgres:${PROD_PASSWORD_ENCODED}@db.jyqgbzhqavgpxqacduoi.supabase.co:5432/postgres?sslmode=require"

# Diretório para dumps
DUMP_DIR="/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data/migration"
mkdir -p "$DUMP_DIR"

echo "=========================================="
echo "Migração Supabase DEV -> PROD"
echo "=========================================="

# Função para testar conexão
test_connection() {
    echo "Testando conexão $1..."
    psql "$2" -c "SELECT 'Conexão OK' as status, current_database() as db, count(*) as clientes FROM clientes;" 2>&1
}

# Função para exportar tabela
export_table() {
    local table=$1
    echo "Exportando tabela: $table"
    pg_dump "$DEV_DB" \
        --table="$table" \
        --data-only \
        --column-inserts \
        --on-conflict-do-nothing \
        > "$DUMP_DIR/${table}.sql" 2>&1

    if [ $? -eq 0 ]; then
        local lines=$(wc -l < "$DUMP_DIR/${table}.sql")
        echo "  ✓ Exportado: $lines linhas"
    else
        echo "  ✗ Erro ao exportar $table"
        return 1
    fi
}

# Função para importar tabela
import_table() {
    local table=$1
    echo "Importando tabela: $table"
    psql "$PROD_DB" -f "$DUMP_DIR/${table}.sql" 2>&1

    if [ $? -eq 0 ]; then
        echo "  ✓ Importado com sucesso"
    else
        echo "  ✗ Erro ao importar $table"
        return 1
    fi
}

# Menu de opções
case "${1:-menu}" in
    test)
        echo ""
        echo "=== Testando DEV ==="
        test_connection "DEV" "$DEV_DB"
        echo ""
        echo "=== Testando PROD ==="
        test_connection "PROD" "$PROD_DB"
        ;;

    export)
        echo "Exportando tabelas do DEV..."
        export_table "clientes"
        export_table "vagas"
        export_table "conhecimento_julia"
        export_table "diretrizes"
        export_table "prompts"
        export_table "julia_status"
        export_table "campanhas"
        echo "Exportação concluída!"
        ;;

    import)
        echo "Importando tabelas no PROD..."
        import_table "clientes"
        import_table "vagas"
        import_table "conhecimento_julia"
        import_table "diretrizes"
        import_table "prompts"
        import_table "julia_status"
        import_table "campanhas"
        echo "Importação concluída!"
        ;;

    migrate)
        $0 export && $0 import
        ;;

    *)
        echo "Uso: $0 {test|export|import|migrate}"
        echo ""
        echo "  test    - Testa conexão com DEV e PROD"
        echo "  export  - Exporta tabelas do DEV"
        echo "  import  - Importa tabelas no PROD"
        echo "  migrate - Exporta e importa (migração completa)"
        ;;
esac
