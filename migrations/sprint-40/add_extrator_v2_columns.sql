-- Sprint 40: Add columns for extrator v2
-- These fields enable atomic vacancy extraction with correct value association

-- Enum for day of week
DO $$ BEGIN
    CREATE TYPE dia_semana_enum AS ENUM (
        'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Enum for period
DO $$ BEGIN
    CREATE TYPE periodo_enum AS ENUM (
        'manha', 'tarde', 'noite', 'diurno', 'noturno', 'cinderela', 'sd', 'sn'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Add new columns
ALTER TABLE vagas_grupo 
ADD COLUMN IF NOT EXISTS dia_semana dia_semana_enum,
ADD COLUMN IF NOT EXISTS periodo periodo_enum,
ADD COLUMN IF NOT EXISTS endereco_raw text,
ADD COLUMN IF NOT EXISTS cidade text,
ADD COLUMN IF NOT EXISTS estado text,
ADD COLUMN IF NOT EXISTS contato_nome text,
ADD COLUMN IF NOT EXISTS contato_whatsapp text;

-- Add comments
COMMENT ON COLUMN vagas_grupo.dia_semana IS 'Sprint 40: Dia da semana para associação de valor (seg-sex vs sab-dom)';
COMMENT ON COLUMN vagas_grupo.periodo IS 'Sprint 40: Período do plantão (manha, tarde, noite, etc)';
COMMENT ON COLUMN vagas_grupo.endereco_raw IS 'Sprint 40: Endereço bruto extraído da mensagem';
COMMENT ON COLUMN vagas_grupo.cidade IS 'Sprint 40: Cidade extraída';
COMMENT ON COLUMN vagas_grupo.estado IS 'Sprint 40: Estado (UF) extraído';
COMMENT ON COLUMN vagas_grupo.contato_nome IS 'Sprint 40: Nome do contato responsável';
COMMENT ON COLUMN vagas_grupo.contato_whatsapp IS 'Sprint 40: WhatsApp do contato responsável';
