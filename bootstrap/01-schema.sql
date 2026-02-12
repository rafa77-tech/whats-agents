


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "app_config";


ALTER SCHEMA "app_config" OWNER TO "postgres";


COMMENT ON SCHEMA "app_config" IS 'Configurações seguras da aplicação';



CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA "public";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "unaccent" WITH SCHEMA "public";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "public";






CREATE TYPE "public"."send_outcome" AS ENUM (
    'SENT',
    'BLOCKED_DEV_ALLOWLIST',
    'BLOCKED_OPTED_OUT',
    'BLOCKED_COOLING_OFF',
    'BLOCKED_NEXT_ALLOWED',
    'BLOCKED_CONTACT_CAP',
    'BLOCKED_CAMPAIGNS_DISABLED',
    'BLOCKED_SAFE_MODE',
    'BLOCKED_CAMPAIGN_COOLDOWN',
    'BLOCKED_QUIET_HOURS',
    'DEDUPED',
    'FAILED_PROVIDER',
    'FAILED_VALIDATION',
    'FAILED_BANNED',
    'FAILED_RATE_LIMIT',
    'FAILED_CIRCUIT_OPEN',
    'FAILED_NO_CAPACITY',
    'BYPASS'
);


ALTER TYPE "public"."send_outcome" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "app_config"."get_secret"("secret_name" "text") RETURNS "text"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'app_config'
    AS $$
DECLARE
  secret_value TEXT;
BEGIN
  SELECT value INTO secret_value 
  FROM app_config.secrets 
  WHERE name = secret_name;
  RETURN secret_value;
END;
$$;


ALTER FUNCTION "app_config"."get_secret"("secret_name" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "app_config"."get_secret"("secret_name" "text") IS 'Busca secret de forma segura';



CREATE OR REPLACE FUNCTION "public"."audit_outbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) RETURNS TABLE("source" "text", "expected_count" bigint, "actual_count" bigint, "coverage_pct" numeric, "layer" "text", "notes" "text")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Layer 1: interacoes saida -> doctor_outbound (business_events)
    RETURN QUERY
    WITH outbound_msgs AS (
        SELECT COUNT(*) as cnt FROM interacoes
        WHERE tipo = 'saida' AND created_at >= p_start AND created_at < p_end
    ),
    outbound_events AS (
        SELECT COUNT(*) as cnt FROM business_events
        WHERE event_type = 'doctor_outbound' AND ts >= p_start AND ts < p_end
    )
    SELECT
        'agente_outbound'::TEXT,
        o.cnt,
        e.cnt,
        CASE WHEN o.cnt = 0 THEN 100.0 ELSE ROUND((e.cnt::numeric / o.cnt) * 100, 2) END,
        'business_events'::TEXT,
        'doctor_outbound para cada saida'::TEXT
    FROM outbound_msgs o, outbound_events e;

    -- Layer 2: policy_events com effect_type = message_sent
    RETURN QUERY
    WITH outbound_msgs AS (
        SELECT COUNT(*) as cnt FROM interacoes
        WHERE tipo = 'saida' AND created_at >= p_start AND created_at < p_end
    ),
    policy_evts AS (
        SELECT COUNT(*) as cnt FROM policy_events
        WHERE effect_type = 'message_sent' AND ts >= p_start AND ts < p_end
    )
    SELECT
        'agente_outbound'::TEXT,
        o.cnt,
        p.cnt,
        CASE WHEN o.cnt = 0 THEN 100.0 ELSE ROUND((p.cnt::numeric / o.cnt) * 100, 2) END,
        'policy_events'::TEXT,
        'policy_effect.message_sent para cada saida'::TEXT
    FROM outbound_msgs o, policy_evts p;
END;
$$;


ALTER FUNCTION "public"."audit_outbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."audit_outbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) IS 'Sprint 18 - E10: Audita cobertura de eventos outbound (business_events + policy_events)';



CREATE OR REPLACE FUNCTION "public"."audit_pipeline_inbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) RETURNS TABLE("source" "text", "expected_count" bigint, "actual_count" bigint, "coverage_pct" numeric, "missing_ids" bigint[])
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_expected BIGINT;
    v_actual BIGINT;
    v_missing BIGINT[];
BEGIN
    -- Contar interacoes de entrada no periodo
    SELECT COUNT(*) INTO v_expected
    FROM interacoes
    WHERE tipo = 'entrada'
      AND created_at >= p_start
      AND created_at < p_end;

    -- Contar eventos doctor_inbound no periodo
    SELECT COUNT(*) INTO v_actual
    FROM business_events
    WHERE event_type = 'doctor_inbound'
      AND ts >= p_start
      AND ts < p_end;

    -- Identificar IDs faltantes (interacoes sem evento)
    SELECT ARRAY_AGG(i.id) INTO v_missing
    FROM interacoes i
    LEFT JOIN business_events be ON
        be.event_type = 'doctor_inbound'
        AND be.interaction_id = i.id
        AND be.ts >= p_start AND be.ts < p_end
    WHERE i.tipo = 'entrada'
      AND i.created_at >= p_start
      AND i.created_at < p_end
      AND be.id IS NULL
    LIMIT 100;

    RETURN QUERY SELECT
        'pipeline_inbound'::TEXT,
        v_expected,
        v_actual,
        CASE WHEN v_expected = 0 THEN 100.0
             ELSE ROUND((v_actual::numeric / v_expected) * 100, 2)
        END,
        COALESCE(v_missing, ARRAY[]::BIGINT[]);
END;
$$;


ALTER FUNCTION "public"."audit_pipeline_inbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."audit_pipeline_inbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) IS 'Sprint 18 - E10: Audita cobertura de eventos doctor_inbound para mensagens de entrada';



CREATE OR REPLACE FUNCTION "public"."audit_status_transition_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) RETURNS TABLE("status_from" "text", "status_to" "text", "expected_event" "text", "db_transitions" bigint, "events_found" bigint, "coverage_pct" numeric, "missing_vaga_ids" "uuid"[])
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Transicao: * -> reservada -> offer_accepted
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id, v.updated_at
        FROM vagas v
        WHERE v.status = 'reservada'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'offer_accepted'
          AND ts >= p_start AND ts < p_end
    ),
    missing AS (
        SELECT ARRAY_AGG(t.id) as ids
        FROM transitions t
        LEFT JOIN events e ON e.vaga_id = t.id
        WHERE e.vaga_id IS NULL
    )
    SELECT
        '*'::TEXT,
        'reservada'::TEXT,
        'offer_accepted'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        COALESCE((SELECT ids FROM missing LIMIT 1), ARRAY[]::UUID[]);

    -- Transicao: * -> pendente_confirmacao -> shift_pending_confirmation
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id FROM vagas v
        WHERE v.status = 'pendente_confirmacao'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'shift_pending_confirmation'
          AND ts >= p_start AND ts < p_end
    )
    SELECT
        '*'::TEXT,
        'pendente_confirmacao'::TEXT,
        'shift_pending_confirmation'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        ARRAY[]::UUID[];

    -- Transicao: * -> realizada -> shift_completed
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id FROM vagas v
        WHERE v.status = 'realizada'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'shift_completed'
          AND ts >= p_start AND ts < p_end
    )
    SELECT
        '*'::TEXT,
        'realizada'::TEXT,
        'shift_completed'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        ARRAY[]::UUID[];

    -- Transicao: * -> cancelada -> shift_cancelled
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id FROM vagas v
        WHERE v.status = 'cancelada'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'shift_cancelled'
          AND ts >= p_start AND ts < p_end
    )
    SELECT
        '*'::TEXT,
        'cancelada'::TEXT,
        'shift_cancelled'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        ARRAY[]::UUID[];
END;
$$;


ALTER FUNCTION "public"."audit_status_transition_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."audit_status_transition_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) IS 'Sprint 18 - E10: Audita cobertura de eventos para transicoes de status de vagas';



CREATE OR REPLACE FUNCTION "public"."buscar_alvos_campanha"("p_filtros" "jsonb" DEFAULT '{}'::"jsonb", "p_dias_sem_contato" integer DEFAULT 14, "p_excluir_cooling" boolean DEFAULT true, "p_excluir_em_atendimento" boolean DEFAULT true, "p_contact_cap" integer DEFAULT 5, "p_limite" integer DEFAULT 1000) RETURNS TABLE("id" "uuid", "nome" "text", "telefone" "text", "especialidade_nome" "text", "regiao" "text", "last_outbound_at" timestamp with time zone, "contact_count_7d" integer)
    LANGUAGE "plpgsql" STABLE
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.nome,
        c.telefone,
        c.especialidade_nome,
        c.regiao,
        ds.last_outbound_at,
        COALESCE(ds.contact_count_7d, 0)::INT as contact_count_7d
    FROM clientes c
    LEFT JOIN doctor_state ds ON ds.cliente_id = c.id
    WHERE
        -- Básico: não optout
        c.status IS DISTINCT FROM 'optout'

        -- Tratar doctor_state ausente (COALESCE) - médico novo é elegível
        AND COALESCE(ds.contact_count_7d, 0) < p_contact_cap

        -- Não tocados recentemente
        AND (
            ds.last_outbound_at IS NULL
            OR ds.last_outbound_at < NOW() - (p_dias_sem_contato || ' days')::INTERVAL
        )

        -- Excluir cooling_off (se flag ativa)
        AND (
            NOT p_excluir_cooling
            OR ds.next_allowed_at IS NULL
            OR ds.next_allowed_at < NOW()
        )

        -- Excluir conversas sob humano (NOT EXISTS evita duplicação)
        AND NOT EXISTS (
            SELECT 1 FROM conversations cv
            WHERE cv.cliente_id = c.id
              AND cv.status = 'active'
              AND cv.controlled_by = 'human'
        )

        -- Excluir em atendimento ativo (inbound < 30min)
        AND (
            NOT p_excluir_em_atendimento
            OR ds.last_inbound_at IS NULL
            OR ds.last_inbound_at < NOW() - INTERVAL '30 minutes'
        )

        -- Filtros demográficos dinâmicos
        AND (
            p_filtros->>'especialidade' IS NULL
            OR c.especialidade_nome = p_filtros->>'especialidade'
        )
        AND (
            p_filtros->>'regiao' IS NULL
            OR c.regiao = p_filtros->>'regiao'
        )

    -- Determinismo: prioriza nunca tocados, depois por antiguidade, tie-breaker por id
    ORDER BY ds.last_outbound_at ASC NULLS FIRST, c.id ASC
    LIMIT p_limite;
END;
$$;


ALTER FUNCTION "public"."buscar_alvos_campanha"("p_filtros" "jsonb", "p_dias_sem_contato" integer, "p_excluir_cooling" boolean, "p_excluir_em_atendimento" boolean, "p_contact_cap" integer, "p_limite" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_alvos_campanha"("p_filtros" "jsonb", "p_dias_sem_contato" integer, "p_excluir_cooling" boolean, "p_excluir_em_atendimento" boolean, "p_contact_cap" integer, "p_limite" integer) IS 'Sprint 24 E01: Retorna médicos elegíveis para campanha, já filtrados por regras operacionais';



CREATE OR REPLACE FUNCTION "public"."buscar_candidatos_touch_reconciliation"("p_desde" timestamp with time zone, "p_limite" integer DEFAULT 1000) RETURNS TABLE("id" "uuid", "cliente_id" "uuid", "provider_message_id" "text", "enviada_em" timestamp with time zone, "metadata" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fm.id,
        fm.cliente_id,
        fm.provider_message_id,
        fm.enviada_em,
        fm.metadata
    FROM fila_mensagens fm
    WHERE fm.status = 'enviada'
      AND fm.outcome IN ('SENT', 'BYPASS')
      AND fm.provider_message_id IS NOT NULL
      AND fm.enviada_em IS NOT NULL  -- Safety check
      AND fm.metadata->>'campanha_id' IS NOT NULL
      AND fm.enviada_em >= p_desde
      -- Excluir já processados (join anti-pattern para performance)
      AND NOT EXISTS (
          SELECT 1 
          FROM touch_reconciliation_log trl 
          WHERE trl.provider_message_id = fm.provider_message_id
      )
    ORDER BY fm.enviada_em DESC
    LIMIT p_limite;
END;
$$;


ALTER FUNCTION "public"."buscar_candidatos_touch_reconciliation"("p_desde" timestamp with time zone, "p_limite" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_candidatos_touch_reconciliation"("p_desde" timestamp with time zone, "p_limite" integer) IS 'Sprint 24 P1: Busca candidatos para reconciliação de touches.
Filtros: status=enviada, outcome IN (SENT,BYPASS), provider_message_id NOT NULL, 
enviada_em NOT NULL, campanha_id presente, não processado anteriormente.';



CREATE OR REPLACE FUNCTION "public"."buscar_conhecimento"("query_embedding" "public"."vector", "tipo_filtro" "text" DEFAULT NULL::"text", "subtipo_filtro" "text" DEFAULT NULL::"text", "limite" integer DEFAULT 5, "threshold" double precision DEFAULT 0.65) RETURNS TABLE("id" "uuid", "arquivo" "text", "secao" "text", "conteudo" "text", "tipo" "text", "subtipo" "text", "tags" "text"[], "similaridade" double precision)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.arquivo,
        c.secao,
        c.conteudo,
        c.tipo,
        c.subtipo,
        c.tags,
        (1 - (c.embedding <=> query_embedding))::FLOAT as similaridade
    FROM conhecimento_julia c
    WHERE c.ativo = true
        AND (tipo_filtro IS NULL OR c.tipo = tipo_filtro)
        AND (subtipo_filtro IS NULL OR c.subtipo = subtipo_filtro)
        AND (1 - (c.embedding <=> query_embedding)) >= threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT limite;
END;
$$;


ALTER FUNCTION "public"."buscar_conhecimento"("query_embedding" "public"."vector", "tipo_filtro" "text", "subtipo_filtro" "text", "limite" integer, "threshold" double precision) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_conhecimento"("query_embedding" "public"."vector", "tipo_filtro" "text", "subtipo_filtro" "text", "limite" integer, "threshold" double precision) IS 'Busca semântica de conhecimento por similaridade de embedding';



CREATE OR REPLACE FUNCTION "public"."buscar_especialidade_por_alias"("p_texto" "text") RETURNS TABLE("especialidade_id" "uuid", "nome" character varying, "score" double precision)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_texto_normalizado TEXT;
    v_resultado RECORD;
BEGIN
    v_texto_normalizado := lower(unaccent(p_texto));
    
    -- Primeiro tenta match exato em alias
    SELECT ea.especialidade_id, e.nome, 1.0::FLOAT as score
    INTO v_resultado
    FROM especialidades_alias ea
    JOIN especialidades e ON e.id = ea.especialidade_id
    WHERE ea.alias_normalizado = v_texto_normalizado
    LIMIT 1;
    
    IF FOUND THEN
        -- Atualizar contador de uso
        UPDATE especialidades_alias 
        SET vezes_usado = vezes_usado + 1, ultimo_uso = now()
        WHERE especialidades_alias.especialidade_id = v_resultado.especialidade_id 
          AND alias_normalizado = v_texto_normalizado;
        
        RETURN QUERY SELECT v_resultado.especialidade_id, v_resultado.nome, v_resultado.score;
        RETURN;
    END IF;
    
    -- Se não encontrou, tenta match por similaridade em alias
    SELECT ea.especialidade_id, e.nome, 
           similarity(ea.alias_normalizado, v_texto_normalizado)::FLOAT as score
    INTO v_resultado
    FROM especialidades_alias ea
    JOIN especialidades e ON e.id = ea.especialidade_id
    WHERE ea.alias_normalizado % v_texto_normalizado
    ORDER BY similarity(ea.alias_normalizado, v_texto_normalizado) DESC
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_resultado.especialidade_id, v_resultado.nome, v_resultado.score;
        RETURN;
    END IF;
    
    -- Último recurso: busca no nome da especialidade diretamente
    SELECT e.id, e.nome,
           similarity(lower(unaccent(e.nome::TEXT)), v_texto_normalizado)::FLOAT as score
    INTO v_resultado
    FROM especialidades e
    WHERE lower(unaccent(e.nome::TEXT)) % v_texto_normalizado
    ORDER BY similarity(lower(unaccent(e.nome::TEXT)), v_texto_normalizado) DESC
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_resultado.id, v_resultado.nome, v_resultado.score;
        RETURN;
    END IF;
    
    -- Nada encontrado
    RETURN;
END;
$$;


ALTER FUNCTION "public"."buscar_especialidade_por_alias"("p_texto" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_especialidade_por_alias"("p_texto" "text") IS 'Busca especialidade por nome/alias usando match exato e fuzzy. Retorna especialidade_id, nome e score (0-1)';



CREATE OR REPLACE FUNCTION "public"."buscar_especialidade_por_similaridade"("p_texto" "text", "p_threshold" double precision DEFAULT 0.3) RETURNS TABLE("especialidade_id" "uuid", "nome" "text", "score" double precision, "fonte" "text")
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Primeiro busca em aliases
    RETURN QUERY
    SELECT 
        ea.especialidade_id,
        e.nome::TEXT,
        similarity(ea.alias_normalizado, p_texto)::FLOAT as score,
        'alias'::TEXT as fonte
    FROM especialidades_alias ea
    JOIN especialidades e ON e.id = ea.especialidade_id
    WHERE similarity(ea.alias_normalizado, p_texto) >= p_threshold
    ORDER BY similarity(ea.alias_normalizado, p_texto) DESC
    LIMIT 1;

    -- Se não encontrou em aliases, busca no nome
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            e.id as especialidade_id,
            e.nome::TEXT,
            similarity(lower(e.nome), p_texto)::FLOAT as score,
            'nome'::TEXT as fonte
        FROM especialidades e
        WHERE similarity(lower(e.nome), p_texto) >= p_threshold
        ORDER BY similarity(lower(e.nome), p_texto) DESC
        LIMIT 1;
    END IF;
END;
$$;


ALTER FUNCTION "public"."buscar_especialidade_por_similaridade"("p_texto" "text", "p_threshold" double precision) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."buscar_hospital_por_alias"("p_texto" "text") RETURNS TABLE("hospital_id" "uuid", "nome" "text", "score" double precision)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_texto_normalizado TEXT;
    v_resultado RECORD;
BEGIN
    v_texto_normalizado := lower(unaccent(p_texto));
    
    -- Primeiro tenta match exato em alias
    SELECT ha.hospital_id, h.nome, 1.0::FLOAT as score
    INTO v_resultado
    FROM hospitais_alias ha
    JOIN hospitais h ON h.id = ha.hospital_id
    WHERE ha.alias_normalizado = v_texto_normalizado
    LIMIT 1;
    
    IF FOUND THEN
        -- Atualizar contador de uso
        UPDATE hospitais_alias 
        SET vezes_usado = vezes_usado + 1, ultimo_uso = now()
        WHERE hospitais_alias.hospital_id = v_resultado.hospital_id 
          AND alias_normalizado = v_texto_normalizado;
        
        RETURN QUERY SELECT v_resultado.hospital_id, v_resultado.nome, v_resultado.score;
        RETURN;
    END IF;
    
    -- Se não encontrou, tenta match por similaridade em alias
    SELECT ha.hospital_id, h.nome, 
           similarity(ha.alias_normalizado, v_texto_normalizado)::FLOAT as score
    INTO v_resultado
    FROM hospitais_alias ha
    JOIN hospitais h ON h.id = ha.hospital_id
    WHERE ha.alias_normalizado % v_texto_normalizado
    ORDER BY similarity(ha.alias_normalizado, v_texto_normalizado) DESC
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_resultado.hospital_id, v_resultado.nome, v_resultado.score;
        RETURN;
    END IF;
    
    -- Último recurso: busca no nome do hospital diretamente
    SELECT h.id, h.nome,
           similarity(lower(unaccent(h.nome)), v_texto_normalizado)::FLOAT as score
    INTO v_resultado
    FROM hospitais h
    WHERE lower(unaccent(h.nome)) % v_texto_normalizado
    ORDER BY similarity(lower(unaccent(h.nome)), v_texto_normalizado) DESC
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_resultado.id, v_resultado.nome, v_resultado.score;
        RETURN;
    END IF;
    
    -- Nada encontrado
    RETURN;
END;
$$;


ALTER FUNCTION "public"."buscar_hospital_por_alias"("p_texto" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_hospital_por_alias"("p_texto" "text") IS 'Busca hospital por nome/alias usando match exato e fuzzy. Retorna hospital_id, nome e score (0-1)';



CREATE OR REPLACE FUNCTION "public"."buscar_hospital_por_similaridade"("p_texto" "text", "p_threshold" double precision DEFAULT 0.3) RETURNS TABLE("hospital_id" "uuid", "nome" "text", "score" double precision, "fonte" "text")
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Primeiro busca em aliases
    RETURN QUERY
    SELECT 
        ha.hospital_id,
        h.nome::TEXT,
        similarity(ha.alias_normalizado, p_texto)::FLOAT as score,
        'alias'::TEXT as fonte
    FROM hospitais_alias ha
    JOIN hospitais h ON h.id = ha.hospital_id
    WHERE similarity(ha.alias_normalizado, p_texto) >= p_threshold
    ORDER BY similarity(ha.alias_normalizado, p_texto) DESC
    LIMIT 1;

    -- Se não encontrou em aliases, busca no nome do hospital
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            h.id as hospital_id,
            h.nome::TEXT,
            similarity(lower(h.nome), p_texto)::FLOAT as score,
            'nome'::TEXT as fonte
        FROM hospitais h
        WHERE similarity(lower(h.nome), p_texto) >= p_threshold
        ORDER BY similarity(lower(h.nome), p_texto) DESC
        LIMIT 1;
    END IF;
END;
$$;


ALTER FUNCTION "public"."buscar_hospital_por_similaridade"("p_texto" "text", "p_threshold" double precision) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."buscar_memorias_recentes"("p_cliente_id" "uuid", "p_limite" integer DEFAULT 10, "p_tipo" character varying DEFAULT NULL::character varying) RETURNS TABLE("id" "uuid", "content" "text", "tipo" character varying, "confianca" character varying, "created_at" timestamp with time zone)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.content,
        dc.tipo,
        dc.confianca,
        dc.created_at
    FROM doctor_context dc
    WHERE 
        dc.cliente_id = p_cliente_id
        AND (p_tipo IS NULL OR dc.tipo = p_tipo)
    ORDER BY dc.created_at DESC
    LIMIT p_limite;
END;
$$;


ALTER FUNCTION "public"."buscar_memorias_recentes"("p_cliente_id" "uuid", "p_limite" integer, "p_tipo" character varying) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_memorias_recentes"("p_cliente_id" "uuid", "p_limite" integer, "p_tipo" character varying) IS 'Busca memorias mais recentes do medico (fallback se embedding nao disponivel)';



CREATE OR REPLACE FUNCTION "public"."buscar_memorias_similares"("p_cliente_id" "uuid", "p_embedding" "public"."vector", "p_limite" integer DEFAULT 5, "p_threshold" double precision DEFAULT 0.7) RETURNS TABLE("id" "uuid", "content" "text", "tipo" character varying, "confianca" character varying, "similaridade" double precision, "created_at" timestamp with time zone)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.content,
        dc.tipo,
        dc.confianca,
        1 - (dc.embedding <=> p_embedding) AS similaridade,
        dc.created_at
    FROM doctor_context dc
    WHERE 
        dc.cliente_id = p_cliente_id
        AND dc.embedding IS NOT NULL
        AND 1 - (dc.embedding <=> p_embedding) >= p_threshold
    ORDER BY dc.embedding <=> p_embedding
    LIMIT p_limite;
END;
$$;


ALTER FUNCTION "public"."buscar_memorias_similares"("p_cliente_id" "uuid", "p_embedding" "public"."vector", "p_limite" integer, "p_threshold" double precision) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."buscar_memorias_similares"("p_cliente_id" "uuid", "p_embedding" "public"."vector", "p_limite" integer, "p_threshold" double precision) IS 'Busca memorias do medico por similaridade semantica usando cosine distance';



CREATE OR REPLACE FUNCTION "public"."check_single_active_prompt"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    IF NEW.ativo = true THEN
        UPDATE prompts
        SET ativo = false, updated_at = now()
        WHERE nome = NEW.nome
          AND id != NEW.id
          AND ativo = true;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."check_single_active_prompt"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."cleanup_old_dedupe_entries"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    DELETE FROM outbound_dedupe
    WHERE created_at < NOW() - INTERVAL '24 hours'
      AND status IN ('sent', 'deduped');
END;
$$;


ALTER FUNCTION "public"."cleanup_old_dedupe_entries"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."consolidar_metricas_pipeline"("p_data" "date") RETURNS "void"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    INSERT INTO metricas_pipeline_diarias (
        data,
        grupos_ativos,
        mensagens_total,
        mensagens_processadas,
        vagas_importadas,
        vagas_revisao,
        vagas_duplicadas,
        custo_total_usd
    )
    SELECT
        p_data,
        COUNT(DISTINCT grupo_id),
        COALESCE(SUM(mensagens_total), 0),
        COALESCE(SUM(mensagens_processadas), 0),
        COALESCE(SUM(vagas_importadas), 0),
        COALESCE(SUM(vagas_revisao), 0),
        COALESCE(SUM(vagas_duplicadas), 0),
        COALESCE(SUM(custo_estimado_usd), 0)
    FROM metricas_grupos_diarias
    WHERE data = p_data
    ON CONFLICT (data) DO UPDATE SET
        grupos_ativos = EXCLUDED.grupos_ativos,
        mensagens_total = EXCLUDED.mensagens_total,
        mensagens_processadas = EXCLUDED.mensagens_processadas,
        vagas_importadas = EXCLUDED.vagas_importadas,
        vagas_revisao = EXCLUDED.vagas_revisao,
        vagas_duplicadas = EXCLUDED.vagas_duplicadas,
        custo_total_usd = EXCLUDED.custo_total_usd;
END;
$$;


ALTER FUNCTION "public"."consolidar_metricas_pipeline"("p_data" "date") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."contar_reservadas_vencidas"("limite_ts" timestamp with time zone) RETURNS integer
    LANGUAGE "sql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
SELECT COUNT(*)::INTEGER
FROM vagas
WHERE status = 'reservada'
  AND (
    -- Calcular fim real do plantão
    CASE 
      -- Plantão noturno: hora_fim <= hora_inicio (termina no dia seguinte)
      WHEN hora_fim <= hora_inicio THEN 
        (data + 1)::TIMESTAMP + hora_fim::INTERVAL
      -- Plantão diurno: termina no mesmo dia
      ELSE 
        data::TIMESTAMP + hora_fim::INTERVAL
    END
  ) < limite_ts;
$$;


ALTER FUNCTION "public"."contar_reservadas_vencidas"("limite_ts" timestamp with time zone) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."count_business_events"("p_hours" integer DEFAULT 24, "p_hospital_id" "uuid" DEFAULT NULL::"uuid") RETURNS TABLE("event_type" "text", "count" bigint)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        be.event_type,
        COUNT(*)::BIGINT
    FROM business_events be
    WHERE be.ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR be.hospital_id = p_hospital_id)
    GROUP BY be.event_type
    ORDER BY
        CASE be.event_type
            WHEN 'doctor_outbound' THEN 1
            WHEN 'doctor_inbound' THEN 2
            WHEN 'offer_teaser_sent' THEN 3
            WHEN 'offer_made' THEN 4
            WHEN 'offer_declined' THEN 5
            WHEN 'offer_accepted' THEN 6
            WHEN 'handoff_created' THEN 7
            WHEN 'shift_completed' THEN 8
            ELSE 9
        END;
END;
$$;


ALTER FUNCTION "public"."count_business_events"("p_hours" integer, "p_hospital_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."count_business_events"("p_hours" integer, "p_hospital_id" "uuid") IS 'Sprint 17: Conta eventos de negócio para funil';



CREATE OR REPLACE FUNCTION "public"."emit_offer_accepted"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Só emite se transicionou PARA reservada (não se já era)
    IF NEW.status = 'reservada' AND (OLD.status IS NULL OR OLD.status != 'reservada') THEN
        INSERT INTO business_events (
            cliente_id,
            vaga_id,
            hospital_id,
            event_type,
            event_props,
            source
        ) VALUES (
            NEW.cliente_id,
            NEW.id,
            NEW.hospital_id,
            'offer_accepted',
            jsonb_build_object(
                'status_anterior', COALESCE(OLD.status, 'novo'),
                'data_plantao', NEW.data,
                'valor', NEW.valor
            ),
            'db'
        );
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."emit_offer_accepted"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."emit_offer_accepted"() IS 'Sprint 17: Emite business_event offer_accepted quando vaga vai para reservada';



CREATE OR REPLACE FUNCTION "public"."emit_shift_completed"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Só emite se transicionou de reservada ou fechada (legado) PARA realizada
    IF NEW.status = 'realizada' AND OLD.status IN ('reservada', 'fechada') THEN
        INSERT INTO business_events (
            cliente_id,
            vaga_id,
            hospital_id,
            event_type,
            event_props,
            source
        ) VALUES (
            NEW.cliente_id,
            NEW.id,
            NEW.hospital_id,
            'shift_completed',
            jsonb_build_object(
                'status_anterior', OLD.status,
                'data_plantao', NEW.data,
                'realizada_em', NEW.realizada_em,
                'realizada_por', NEW.realizada_por,
                'valor', NEW.valor
            ),
            'db'
        );
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."emit_shift_completed"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."emit_shift_completed"() IS 'Sprint 17: Emite business_event shift_completed quando vaga vai de reservada/fechada para realizada';



CREATE OR REPLACE FUNCTION "public"."get_conversion_rates"("p_hours" integer DEFAULT 168, "p_hospital_id" "uuid" DEFAULT NULL::"uuid") RETURNS TABLE("segment_type" "text", "segment_value" "text", "offers_made" bigint, "offers_accepted" bigint, "conversion_rate" numeric, "period_hours" integer)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Taxa geral
    RETURN QUERY
    SELECT
        'global'::TEXT,
        'all'::TEXT,
        (SELECT COUNT(*) FROM business_events WHERE event_type = 'offer_made' AND ts >= now() - (p_hours || ' hours')::interval),
        (SELECT COUNT(*) FROM business_events WHERE event_type = 'offer_accepted' AND ts >= now() - (p_hours || ' hours')::interval),
        0::NUMERIC(5,2),
        p_hours;

    -- Por hospital
    RETURN QUERY
    SELECT
        'hospital'::TEXT,
        COALESCE(h.nome, be.hospital_id::TEXT),
        COUNT(*) FILTER (WHERE be.event_type = 'offer_made'),
        COUNT(*) FILTER (WHERE be.event_type = 'offer_accepted'),
        0::NUMERIC(5,2),
        p_hours
    FROM business_events be
    LEFT JOIN hospitais h ON be.hospital_id = h.id
    WHERE be.event_type IN ('offer_made', 'offer_accepted')
      AND be.ts >= now() - (p_hours || ' hours')::interval
      AND be.hospital_id IS NOT NULL
      AND (p_hospital_id IS NULL OR be.hospital_id = p_hospital_id)
    GROUP BY be.hospital_id, h.nome
    HAVING COUNT(*) FILTER (WHERE be.event_type = 'offer_made') >= 5;

END;
$$;


ALTER FUNCTION "public"."get_conversion_rates"("p_hours" integer, "p_hospital_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_conversion_rates"("p_hours" integer, "p_hospital_id" "uuid") IS 'Sprint 18 - E12.1: Taxa de conversao offer_made -> offer_accepted';



CREATE OR REPLACE FUNCTION "public"."get_funnel_invariant_violations"("p_days" integer DEFAULT 7) RETURNS TABLE("invariant_name" "text", "violation_type" "text", "event_id" "uuid", "vaga_id" "uuid", "cliente_id" "uuid", "event_ts" timestamp with time zone, "details" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Invariante 1: offer_accepted deve ter offer_made prévio
    RETURN QUERY
    SELECT
        'offer_accepted_requires_offer_made'::TEXT,
        'aceite_sem_oferta'::TEXT,
        a.id,
        a.vaga_id,
        a.cliente_id,
        a.ts,
        jsonb_build_object(
            'event_type', a.event_type,
            'vaga_id', a.vaga_id
        )
    FROM business_events a
    WHERE a.event_type = 'offer_accepted'
      AND a.ts >= now() - (p_days || ' days')::interval
      AND a.vaga_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM business_events o
          WHERE o.event_type = 'offer_made'
            AND o.vaga_id = a.vaga_id
            AND o.cliente_id = a.cliente_id
            AND o.ts < a.ts
      );

    -- Invariante 2: offer_made específico deve ter vaga_id
    -- FIX: usar alias 'be' para evitar ambiguidade com variável PL/pgSQL
    RETURN QUERY
    SELECT
        'offer_made_requires_vaga_id'::TEXT,
        'oferta_sem_vaga_id'::TEXT,
        be.id,
        NULL::UUID,
        be.cliente_id,
        be.ts,
        jsonb_build_object(
            'event_props', be.event_props,
            'note', 'offer_made sem vaga_id - deveria ser offer_teaser_sent?'
        )
    FROM business_events be
    WHERE be.event_type = 'offer_made'
      AND be.vaga_id IS NULL
      AND be.ts >= now() - (p_days || ' days')::interval;

    -- Invariante 3: shift_completed deve ter offer_accepted prévio
    RETURN QUERY
    SELECT
        'shift_completed_requires_accepted'::TEXT,
        'completado_sem_aceite'::TEXT,
        c.id,
        c.vaga_id,
        c.cliente_id,
        c.ts,
        jsonb_build_object('vaga_id', c.vaga_id)
    FROM business_events c
    WHERE c.event_type = 'shift_completed'
      AND c.ts >= now() - (p_days || ' days')::interval
      AND c.vaga_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM business_events a
          WHERE a.event_type = 'offer_accepted'
            AND a.vaga_id = c.vaga_id
            AND a.ts < c.ts
      );

    -- Invariante 4: handoff_started deve ter conversa ativa
    RETURN QUERY
    SELECT
        'handoff_requires_conversation'::TEXT,
        'handoff_orfao'::TEXT,
        h.id,
        NULL::UUID,
        h.cliente_id,
        h.ts,
        jsonb_build_object('conversation_id', h.conversation_id)
    FROM business_events h
    WHERE h.event_type = 'handoff_started'
      AND h.ts >= now() - (p_days || ' days')::interval
      AND h.conversation_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM conversations conv
          WHERE conv.id = h.conversation_id
      );

END;
$$;


ALTER FUNCTION "public"."get_funnel_invariant_violations"("p_days" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_funnel_invariant_violations"("p_days" integer) IS 'Sprint 18.1: Corrigido ambiguidade cliente_id';



CREATE OR REPLACE FUNCTION "public"."get_funnel_rates"("p_hours" integer DEFAULT 24, "p_hospital_id" "uuid" DEFAULT NULL::"uuid") RETURNS TABLE("metric_name" "text", "numerator" bigint, "denominator" bigint, "rate" numeric)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_outbound BIGINT;
    v_inbound BIGINT;
    v_offer_made BIGINT;
    v_accepted BIGINT;
    v_completed BIGINT;
BEGIN
    -- Contar cada tipo
    SELECT COUNT(*) INTO v_outbound
    FROM business_events
    WHERE event_type = 'doctor_outbound'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_inbound
    FROM business_events
    WHERE event_type = 'doctor_inbound'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_offer_made
    FROM business_events
    WHERE event_type = 'offer_made'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_accepted
    FROM business_events
    WHERE event_type = 'offer_accepted'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_completed
    FROM business_events
    WHERE event_type = 'shift_completed'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    -- Retornar taxas
    RETURN QUERY SELECT
        'response_rate'::TEXT,
        v_inbound,
        v_outbound,
        CASE WHEN v_outbound > 0
            THEN ROUND((v_inbound::NUMERIC / v_outbound) * 100, 2)
            ELSE 0
        END;

    RETURN QUERY SELECT
        'conversion_rate'::TEXT,
        v_accepted,
        v_offer_made,
        CASE WHEN v_offer_made > 0
            THEN ROUND((v_accepted::NUMERIC / v_offer_made) * 100, 2)
            ELSE 0
        END;

    RETURN QUERY SELECT
        'completion_rate'::TEXT,
        v_completed,
        v_accepted,
        CASE WHEN v_accepted > 0
            THEN ROUND((v_completed::NUMERIC / v_accepted) * 100, 2)
            ELSE 0
        END;

    RETURN QUERY SELECT
        'overall_success'::TEXT,
        v_completed,
        v_outbound,
        CASE WHEN v_outbound > 0
            THEN ROUND((v_completed::NUMERIC / v_outbound) * 100, 2)
            ELSE 0
        END;
END;
$$;


ALTER FUNCTION "public"."get_funnel_rates"("p_hours" integer, "p_hospital_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_funnel_rates"("p_hours" integer, "p_hospital_id" "uuid") IS 'Sprint 17: Calcula taxas de conversão do funil';



CREATE OR REPLACE FUNCTION "public"."get_health_score_components"() RETURNS TABLE("component" "text", "metric_name" "text", "value" numeric, "total_count" bigint, "affected_count" bigint, "percentage" numeric, "weight" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_total_doctors BIGINT;
    v_contact_avg NUMERIC(10,2);
    v_contact_p95 NUMERIC(10,2);
    v_opted_out BIGINT;
    v_cooling_off BIGINT;
    v_handoffs_7d BIGINT;
    v_conversations_7d BIGINT;
    v_blocked_7d BIGINT;
    v_outbound_7d BIGINT;
BEGIN
    -- Total de medicos com state
    SELECT COUNT(*) INTO v_total_doctors FROM doctor_state;
    
    -- Se nao temos dados, retornar zeros
    IF v_total_doctors = 0 THEN
        v_total_doctors := 1; -- Evitar divisao por zero
    END IF;

    -- COMPONENTE 1: Pressao (contact_count_7d)
    SELECT
        ROUND(COALESCE(AVG(contact_count_7d), 0)::NUMERIC, 2),
        ROUND(COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY contact_count_7d), 0)::NUMERIC, 2)
    INTO v_contact_avg, v_contact_p95
    FROM doctor_state;

    RETURN QUERY SELECT
        'pressao'::TEXT,
        'contact_count_7d_avg'::TEXT,
        COALESCE(v_contact_avg, 0),
        v_total_doctors,
        (SELECT COUNT(*) FROM doctor_state WHERE contact_count_7d > 5),
        ROUND(((SELECT COUNT(*) FROM doctor_state WHERE contact_count_7d > 5)::NUMERIC / v_total_doctors) * 100, 2),
        0.25::NUMERIC;

    RETURN QUERY SELECT
        'pressao'::TEXT,
        'contact_count_7d_p95'::TEXT,
        COALESCE(v_contact_p95, 0),
        v_total_doctors,
        0::BIGINT,
        0::NUMERIC,
        0::NUMERIC;

    -- COMPONENTE 2: Friccao (opted_out + cooling_off)
    SELECT COUNT(*) INTO v_opted_out FROM doctor_state WHERE permission_state = 'opted_out';
    SELECT COUNT(*) INTO v_cooling_off FROM doctor_state WHERE permission_state = 'cooling_off';

    RETURN QUERY SELECT
        'friccao'::TEXT,
        'opted_out_rate'::TEXT,
        0::NUMERIC,
        v_total_doctors,
        COALESCE(v_opted_out, 0),
        ROUND((COALESCE(v_opted_out, 0)::NUMERIC / v_total_doctors) * 100, 2),
        0.175::NUMERIC;

    RETURN QUERY SELECT
        'friccao'::TEXT,
        'cooling_off_rate'::TEXT,
        0::NUMERIC,
        v_total_doctors,
        COALESCE(v_cooling_off, 0),
        ROUND((COALESCE(v_cooling_off, 0)::NUMERIC / v_total_doctors) * 100, 2),
        0.175::NUMERIC;

    -- COMPONENTE 3: Qualidade (handoff rate)
    SELECT COUNT(*) INTO v_handoffs_7d
    FROM business_events
    WHERE event_type = 'handoff_started'
      AND ts >= now() - interval '7 days';

    SELECT COUNT(DISTINCT cliente_id) INTO v_conversations_7d
    FROM business_events
    WHERE event_type IN ('doctor_inbound', 'doctor_outbound')
      AND ts >= now() - interval '7 days';

    IF v_conversations_7d = 0 THEN
        v_conversations_7d := 1;
    END IF;

    RETURN QUERY SELECT
        'qualidade'::TEXT,
        'handoff_rate'::TEXT,
        0::NUMERIC,
        COALESCE(v_conversations_7d, 0),
        COALESCE(v_handoffs_7d, 0),
        ROUND((COALESCE(v_handoffs_7d, 0)::NUMERIC / v_conversations_7d) * 100, 2),
        0.25::NUMERIC;

    -- COMPONENTE 4: Spam (campaign_blocked rate)
    SELECT COUNT(*) INTO v_blocked_7d
    FROM business_events
    WHERE event_type = 'campaign_blocked'
      AND ts >= now() - interval '7 days';

    SELECT COUNT(*) INTO v_outbound_7d
    FROM business_events
    WHERE event_type = 'doctor_outbound'
      AND ts >= now() - interval '7 days';

    IF v_outbound_7d = 0 THEN
        v_outbound_7d := 1;
    END IF;

    RETURN QUERY SELECT
        'spam'::TEXT,
        'blocked_rate'::TEXT,
        0::NUMERIC,
        COALESCE(v_outbound_7d, 0),
        COALESCE(v_blocked_7d, 0),
        ROUND((COALESCE(v_blocked_7d, 0)::NUMERIC / v_outbound_7d) * 100, 2),
        0.15::NUMERIC;

END;
$$;


ALTER FUNCTION "public"."get_health_score_components"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_health_score_components"() IS 'Sprint 18 - E12.3: Componentes do Health Score (pressao, friccao, qualidade, spam)';



CREATE OR REPLACE FUNCTION "public"."get_time_to_fill_breakdown"("p_days" integer DEFAULT 30, "p_hospital_id" "uuid" DEFAULT NULL::"uuid") RETURNS TABLE("metric_name" "text", "segment_type" "text", "segment_value" "text", "sample_size" bigint, "avg_hours" numeric, "median_hours" numeric, "p90_hours" numeric, "p95_hours" numeric, "min_hours" numeric, "max_hours" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- Time-to-Reserve: anunciada -> reservada (global)
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
                - v.created_at
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status IN ('reservada', 'pendente_confirmacao', 'realizada')
          AND v.created_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
    )
    SELECT
        'time_to_reserve'::TEXT,
        'global'::TEXT,
        'all'::TEXT,
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0 AND horas IS NOT NULL;

    -- Time-to-Reserve por hospital
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
                - v.created_at
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status IN ('reservada', 'pendente_confirmacao', 'realizada')
          AND v.created_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
    )
    SELECT
        'time_to_reserve'::TEXT,
        'hospital'::TEXT,
        COALESCE(hospital_nome, hospital_id::TEXT),
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0 AND horas IS NOT NULL
    GROUP BY hospital_id, hospital_nome
    HAVING COUNT(*) >= 3;

    -- Time-to-Confirm: pendente_confirmacao -> realizada/cancelada (global)
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                COALESCE(
                    (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_completed'),
                    (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_cancelled')
                )
                - (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_pending_confirmation')
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status IN ('realizada', 'cancelada')
          AND v.updated_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_pending_confirmation')
    )
    SELECT
        'time_to_confirm'::TEXT,
        'global'::TEXT,
        'all'::TEXT,
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0 AND horas IS NOT NULL;

    -- Time-to-Fill (full): anunciada -> realizada (global)
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_completed')
                - v.created_at
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status = 'realizada'
          AND v.updated_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_completed')
    )
    SELECT
        'time_to_fill'::TEXT,
        'global'::TEXT,
        'all'::TEXT,
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0 AND horas IS NOT NULL;

END;
$$;


ALTER FUNCTION "public"."get_time_to_fill_breakdown"("p_days" integer, "p_hospital_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_time_to_fill_breakdown"("p_days" integer, "p_hospital_id" "uuid") IS 'Sprint 18 - E12.2: Breakdown de tempos (reserve, confirm, fill)';



CREATE OR REPLACE FUNCTION "public"."incrementar_mensagens_contato"("p_contato_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    UPDATE contatos_grupo
    SET
        total_mensagens = total_mensagens + 1,
        ultimo_contato = now(),
        updated_at = now()
    WHERE id = p_contato_id;
END;
$$;


ALTER FUNCTION "public"."incrementar_mensagens_contato"("p_contato_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."incrementar_mensagens_contato"("p_contato_id" "uuid") IS 'Incrementa contador de mensagens de um contato';



CREATE OR REPLACE FUNCTION "public"."incrementar_mensagens_grupo"("p_grupo_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    UPDATE grupos_whatsapp
    SET
        total_mensagens = total_mensagens + 1,
        ultima_mensagem_em = now(),
        updated_at = now()
    WHERE id = p_grupo_id;
END;
$$;


ALTER FUNCTION "public"."incrementar_mensagens_grupo"("p_grupo_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."incrementar_mensagens_grupo"("p_grupo_id" "uuid") IS 'Incrementa contador de mensagens de um grupo';



CREATE OR REPLACE FUNCTION "public"."incrementar_metricas_grupo"("p_data" "date", "p_grupo_id" "uuid", "p_mensagens" integer DEFAULT 0, "p_vagas" integer DEFAULT 0, "p_tokens_in" integer DEFAULT 0, "p_tokens_out" integer DEFAULT 0, "p_tempo_medio" integer DEFAULT NULL::integer, "p_confianca" numeric DEFAULT NULL::numeric, "p_custo" numeric DEFAULT 0) RETURNS "void"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    INSERT INTO metricas_grupos_diarias (
        data, grupo_id,
        mensagens_processadas, vagas_extraidas,
        tokens_input, tokens_output,
        tempo_medio_processamento_ms,
        confianca_media_extracao,
        custo_estimado_usd
    ) VALUES (
        p_data, p_grupo_id,
        p_mensagens, p_vagas,
        p_tokens_in, p_tokens_out,
        p_tempo_medio,
        p_confianca,
        p_custo
    )
    ON CONFLICT (data, grupo_id) DO UPDATE SET
        mensagens_processadas = metricas_grupos_diarias.mensagens_processadas + p_mensagens,
        vagas_extraidas = metricas_grupos_diarias.vagas_extraidas + p_vagas,
        tokens_input = metricas_grupos_diarias.tokens_input + p_tokens_in,
        tokens_output = metricas_grupos_diarias.tokens_output + p_tokens_out,
        tempo_medio_processamento_ms = COALESCE(
            (COALESCE(metricas_grupos_diarias.tempo_medio_processamento_ms, 0) + COALESCE(p_tempo_medio, 0)) / 2,
            p_tempo_medio
        ),
        confianca_media_extracao = COALESCE(
            (COALESCE(metricas_grupos_diarias.confianca_media_extracao, 0) + COALESCE(p_confianca, 0)) / 2,
            p_confianca
        ),
        custo_estimado_usd = metricas_grupos_diarias.custo_estimado_usd + p_custo,
        updated_at = NOW();
END;
$$;


ALTER FUNCTION "public"."incrementar_metricas_grupo"("p_data" "date", "p_grupo_id" "uuid", "p_mensagens" integer, "p_vagas" integer, "p_tokens_in" integer, "p_tokens_out" integer, "p_tempo_medio" integer, "p_confianca" numeric, "p_custo" numeric) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."incrementar_vezes_usado"("p_tabela" "text", "p_alias_normalizado" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    IF p_tabela = 'hospitais_alias' THEN
        UPDATE hospitais_alias 
        SET vezes_usado = COALESCE(vezes_usado, 0) + 1,
            ultimo_uso = NOW()
        WHERE alias_normalizado = p_alias_normalizado;
    ELSIF p_tabela = 'especialidades_alias' THEN
        UPDATE especialidades_alias 
        SET vezes_usado = COALESCE(vezes_usado, 0) + 1,
            ultimo_uso = NOW()
        WHERE alias_normalizado = p_alias_normalizado;
    END IF;
END;
$$;


ALTER FUNCTION "public"."incrementar_vezes_usado"("p_tabela" "text", "p_alias_normalizado" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."inserir_intent_se_novo"("p_fingerprint" "text", "p_cliente_id" "uuid", "p_intent_type" "text", "p_reference_id" "uuid" DEFAULT NULL::"uuid", "p_expires_at" timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS TABLE("fingerprint" "text", "inserted" boolean)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_rows_affected INT;
BEGIN
    INSERT INTO intent_log (fingerprint, cliente_id, intent_type, reference_id, expires_at)
    VALUES (
        p_fingerprint,
        p_cliente_id,
        p_intent_type,
        p_reference_id,
        COALESCE(p_expires_at, NOW() + INTERVAL '30 days')
    )
    ON CONFLICT (fingerprint) DO NOTHING;

    GET DIAGNOSTICS v_rows_affected = ROW_COUNT;

    RETURN QUERY SELECT p_fingerprint, (v_rows_affected > 0);
END;
$$;


ALTER FUNCTION "public"."inserir_intent_se_novo"("p_fingerprint" "text", "p_cliente_id" "uuid", "p_intent_type" "text", "p_reference_id" "uuid", "p_expires_at" timestamp with time zone) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."inserir_intent_se_novo"("p_fingerprint" "text", "p_cliente_id" "uuid", "p_intent_type" "text", "p_reference_id" "uuid", "p_expires_at" timestamp with time zone) IS 'Sprint 24 E02: Insert idempotente de intent, retorna se inseriu ou já existia';



CREATE OR REPLACE FUNCTION "public"."log_clientes_changes"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO clientes_log(cliente_id, acao, dados_antigos, usuario)
        VALUES (OLD.id, 'DELETE', row_to_json(OLD), OLD.created_by);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO clientes_log(cliente_id, acao, dados_antigos, dados_novos, usuario)
        VALUES (NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), NEW.created_by);
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO clientes_log(cliente_id, acao, dados_novos, usuario)
        VALUES (NEW.id, 'INSERT', row_to_json(NEW), NEW.created_by);
        RETURN NEW;
    END IF;
END;
$$;


ALTER FUNCTION "public"."log_clientes_changes"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."marcar_vaga_realizada"("p_vaga_id" "uuid", "p_realizada_por" "text" DEFAULT 'ops'::"text") RETURNS boolean
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_status TEXT;
BEGIN
    -- Verificar status atual
    SELECT status INTO v_status FROM vagas WHERE id = p_vaga_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'Vaga não encontrada: %', p_vaga_id;
    END IF;

    -- Aceita tanto 'reservada' quanto 'fechada' (legado)
    IF v_status NOT IN ('reservada', 'fechada') THEN
        RAISE EXCEPTION 'Vaga deve estar reservada ou fechada para ser realizada. Status atual: %', v_status;
    END IF;

    -- Atualizar status para realizada
    UPDATE vagas
    SET status = 'realizada',
        realizada_em = NOW(),
        realizada_por = p_realizada_por,
        updated_at = NOW()
    WHERE id = p_vaga_id;

    RETURN TRUE;
END;
$$;


ALTER FUNCTION "public"."marcar_vaga_realizada"("p_vaga_id" "uuid", "p_realizada_por" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."marcar_vaga_realizada"("p_vaga_id" "uuid", "p_realizada_por" "text") IS 'Sprint 17: Marca vaga como realizada (aceita reservada ou fechada como origem)';



CREATE OR REPLACE FUNCTION "public"."normalizar_alias"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    NEW.alias_normalizado := lower(unaccent(NEW.alias));
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."normalizar_alias"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reconcile_all"("p_hours" integer DEFAULT 24) RETURNS TABLE("direction" "text", "anomaly_type" "text", "entity_type" "text", "entity_id" "uuid", "expected" "text", "found" "text", "details" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_start TIMESTAMPTZ;
    v_end TIMESTAMPTZ;
BEGIN
    v_end := now();
    v_start := v_end - (p_hours || ' hours')::interval;

    -- DB -> Eventos
    RETURN QUERY
    SELECT
        'db_to_events'::TEXT,
        r.anomaly_type,
        r.entity_type,
        r.entity_id,
        r.expected,
        r.found,
        r.details
    FROM reconcile_db_to_events(v_start, v_end) r;

    -- Eventos -> DB
    RETURN QUERY
    SELECT
        'events_to_db'::TEXT,
        r.anomaly_type,
        r.entity_type,
        r.entity_id,
        r.expected,
        r.found,
        r.details
    FROM reconcile_events_to_db(v_start, v_end) r;
END;
$$;


ALTER FUNCTION "public"."reconcile_all"("p_hours" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."reconcile_all"("p_hours" integer) IS 'Sprint 18 - E11.2: Reconciliacao completa bidirecional';



CREATE OR REPLACE FUNCTION "public"."reconcile_db_to_events"("p_start" timestamp with time zone, "p_end" timestamp with time zone) RETURNS TABLE("anomaly_type" "text", "entity_type" "text", "entity_id" "uuid", "expected" "text", "found" "text", "details" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- 1. Vaga reservada -> offer_accepted
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento offer_accepted'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at,
            'cliente_id', v.cliente_id
        )
    FROM vagas v
    WHERE v.status = 'reservada'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'offer_accepted'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 2. Vaga pendente_confirmacao -> shift_pending_confirmation
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento shift_pending_confirmation'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at
        )
    FROM vagas v
    WHERE v.status = 'pendente_confirmacao'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'shift_pending_confirmation'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 3. Vaga realizada -> shift_completed
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento shift_completed'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at,
            'realizada_por', v.realizada_por
        )
    FROM vagas v
    WHERE v.status = 'realizada'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'shift_completed'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 4. Vaga cancelada -> shift_cancelled
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento shift_cancelled'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at
        )
    FROM vagas v
    WHERE v.status = 'cancelada'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'shift_cancelled'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 5. Handoff criado -> handoff_started
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'handoff'::TEXT,
        h.id,
        'evento handoff_started'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'conversa_id', h.conversa_id,
            'created_at', h.created_at
        )
    FROM handoffs h
    WHERE h.created_at >= p_start AND h.created_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'handoff_started'
            AND be.event_props->>'handoff_id' = h.id::text
            AND be.ts >= h.created_at - interval '1 minute'
      );
END;
$$;


ALTER FUNCTION "public"."reconcile_db_to_events"("p_start" timestamp with time zone, "p_end" timestamp with time zone) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."reconcile_db_to_events"("p_start" timestamp with time zone, "p_end" timestamp with time zone) IS 'Sprint 18 - E11.2: Reconcilia DB -> Eventos (mudancas de estado devem ter eventos)';



CREATE OR REPLACE FUNCTION "public"."reconcile_events_to_db"("p_start" timestamp with time zone, "p_end" timestamp with time zone) RETURNS TABLE("anomaly_type" "text", "entity_type" "text", "entity_id" "uuid", "expected" "text", "found" "text", "details" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    -- 1. offer_accepted -> vaga deve estar reservada/realizada
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'vaga.status IN (reservada, realizada, pendente_confirmacao)'::TEXT,
        COALESCE('vaga.status = ' || v.status, 'vaga nao encontrada')::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'vaga_id', be.vaga_id,
            'event_ts', be.ts,
            'vaga_status', v.status
        )
    FROM business_events be
    LEFT JOIN vagas v ON v.id = be.vaga_id
    WHERE be.event_type = 'offer_accepted'
      AND be.ts >= p_start AND be.ts < p_end
      AND be.vaga_id IS NOT NULL
      AND (v.id IS NULL OR v.status NOT IN ('reservada', 'realizada', 'pendente_confirmacao'));

    -- 2. shift_completed -> vaga deve estar realizada
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'vaga.status = realizada'::TEXT,
        COALESCE('vaga.status = ' || v.status, 'vaga nao encontrada')::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'vaga_id', be.vaga_id,
            'event_ts', be.ts,
            'vaga_status', v.status
        )
    FROM business_events be
    LEFT JOIN vagas v ON v.id = be.vaga_id
    WHERE be.event_type = 'shift_completed'
      AND be.ts >= p_start AND be.ts < p_end
      AND be.vaga_id IS NOT NULL
      AND (v.id IS NULL OR v.status != 'realizada');

    -- 3. shift_cancelled -> vaga deve estar cancelada
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'vaga.status = cancelada'::TEXT,
        COALESCE('vaga.status = ' || v.status, 'vaga nao encontrada')::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'vaga_id', be.vaga_id,
            'event_ts', be.ts,
            'vaga_status', v.status
        )
    FROM business_events be
    LEFT JOIN vagas v ON v.id = be.vaga_id
    WHERE be.event_type = 'shift_cancelled'
      AND be.ts >= p_start AND be.ts < p_end
      AND be.vaga_id IS NOT NULL
      AND (v.id IS NULL OR v.status != 'cancelada');

    -- 4. handoff_resolved -> handoff deve estar resolvido
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'handoff.resolvido_em IS NOT NULL'::TEXT,
        'handoff nao resolvido ou nao encontrado'::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'handoff_id', be.event_props->>'handoff_id',
            'event_ts', be.ts
        )
    FROM business_events be
    WHERE be.event_type = 'handoff_resolved'
      AND be.ts >= p_start AND be.ts < p_end
      AND NOT EXISTS (
          SELECT 1 FROM handoffs h
          WHERE h.id::text = be.event_props->>'handoff_id'
            AND h.resolvido_em IS NOT NULL
      );
END;
$$;


ALTER FUNCTION "public"."reconcile_events_to_db"("p_start" timestamp with time zone, "p_end" timestamp with time zone) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."reconcile_events_to_db"("p_start" timestamp with time zone, "p_end" timestamp with time zone) IS 'Sprint 18 - E11.2: Reconcilia Eventos -> DB (eventos devem refletir estado no DB)';



CREATE OR REPLACE FUNCTION "public"."registrar_alias_especialidade"("p_especialidade_id" "uuid", "p_alias" "text", "p_origem" "text" DEFAULT 'importacao'::"text", "p_confianca" double precision DEFAULT 0.8) RETURNS "uuid"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_alias_normalizado TEXT;
    v_alias_id UUID;
BEGIN
    v_alias_normalizado := lower(unaccent(p_alias));
    
    -- Verifica se já existe
    SELECT id INTO v_alias_id
    FROM especialidades_alias
    WHERE especialidade_id = p_especialidade_id AND alias_normalizado = v_alias_normalizado;
    
    IF FOUND THEN
        -- Atualiza uso
        UPDATE especialidades_alias 
        SET vezes_usado = vezes_usado + 1, ultimo_uso = now()
        WHERE id = v_alias_id;
        RETURN v_alias_id;
    END IF;
    
    -- Insere novo alias
    INSERT INTO especialidades_alias (especialidade_id, alias, alias_normalizado, origem, confianca)
    VALUES (p_especialidade_id, p_alias, v_alias_normalizado, p_origem, p_confianca)
    RETURNING id INTO v_alias_id;
    
    RETURN v_alias_id;
END;
$$;


ALTER FUNCTION "public"."registrar_alias_especialidade"("p_especialidade_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."registrar_alias_especialidade"("p_especialidade_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) IS 'Registra novo alias de especialidade ou atualiza uso se já existir';



CREATE OR REPLACE FUNCTION "public"."registrar_alias_hospital"("p_hospital_id" "uuid", "p_alias" "text", "p_origem" "text" DEFAULT 'importacao'::"text", "p_confianca" double precision DEFAULT 0.8) RETURNS "uuid"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
DECLARE
    v_alias_normalizado TEXT;
    v_alias_id UUID;
BEGIN
    v_alias_normalizado := lower(unaccent(p_alias));
    
    -- Verifica se já existe
    SELECT id INTO v_alias_id
    FROM hospitais_alias
    WHERE hospital_id = p_hospital_id AND alias_normalizado = v_alias_normalizado;
    
    IF FOUND THEN
        -- Atualiza uso
        UPDATE hospitais_alias 
        SET vezes_usado = vezes_usado + 1, ultimo_uso = now()
        WHERE id = v_alias_id;
        RETURN v_alias_id;
    END IF;
    
    -- Insere novo alias
    INSERT INTO hospitais_alias (hospital_id, alias, alias_normalizado, origem, confianca)
    VALUES (p_hospital_id, p_alias, v_alias_normalizado, p_origem, p_confianca)
    RETURNING id INTO v_alias_id;
    
    RETURN v_alias_id;
END;
$$;


ALTER FUNCTION "public"."registrar_alias_hospital"("p_hospital_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."registrar_alias_hospital"("p_hospital_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) IS 'Registra novo alias de hospital ou atualiza uso se já existir';



CREATE OR REPLACE FUNCTION "public"."registrar_primeira_mensagem_grupo"("p_grupo_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    UPDATE grupos_whatsapp
    SET primeira_mensagem_em = now()
    WHERE id = p_grupo_id AND primeira_mensagem_em IS NULL;
END;
$$;


ALTER FUNCTION "public"."registrar_primeira_mensagem_grupo"("p_grupo_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."registrar_primeira_mensagem_grupo"("p_grupo_id" "uuid") IS 'Registra timestamp da primeira mensagem do grupo se ainda não existir';



CREATE OR REPLACE FUNCTION "public"."stats_vagas_grupo"("data_inicio" "date") RETURNS TABLE("total" bigint, "importadas" bigint, "revisao" bigint, "descartadas" bigint, "duplicadas" bigint, "taxa_conversao" numeric, "taxa_auto" numeric, "taxa_dup" numeric)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total,
        COUNT(*) FILTER (WHERE status = 'importada')::BIGINT as importadas,
        COUNT(*) FILTER (WHERE status = 'aguardando_revisao')::BIGINT as revisao,
        COUNT(*) FILTER (WHERE status = 'descartada')::BIGINT as descartadas,
        COUNT(*) FILTER (WHERE eh_duplicada = true)::BIGINT as duplicadas,
        COALESCE(
            COUNT(*) FILTER (WHERE status = 'importada')::NUMERIC / NULLIF(COUNT(*), 0),
            0
        ) as taxa_conversao,
        COALESCE(
            COUNT(*) FILTER (WHERE status = 'importada' AND revisado_em IS NULL)::NUMERIC
            / NULLIF(COUNT(*) FILTER (WHERE status = 'importada'), 0),
            0
        ) as taxa_auto,
        COALESCE(
            COUNT(*) FILTER (WHERE eh_duplicada = true)::NUMERIC / NULLIF(COUNT(*), 0),
            0
        ) as taxa_dup
    FROM vagas_grupo
    WHERE created_at >= data_inicio;
END;
$$;


ALTER FUNCTION "public"."stats_vagas_grupo"("data_inicio" "date") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."status_fila_grupos"() RETURNS TABLE("pendentes" bigint, "em_processamento" bigint, "finalizados_hoje" bigint, "erros_hoje" bigint, "tempo_medio_ms" bigint)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE estagio = 'pendente')::BIGINT as pendentes,
        COUNT(*) FILTER (WHERE estagio NOT IN ('pendente', 'finalizado', 'descartado', 'erro'))::BIGINT as em_processamento,
        COUNT(*) FILTER (WHERE estagio = 'finalizado' AND DATE(updated_at) = CURRENT_DATE)::BIGINT as finalizados_hoje,
        COUNT(*) FILTER (WHERE estagio = 'erro' AND DATE(updated_at) = CURRENT_DATE)::BIGINT as erros_hoje,
        COALESCE(AVG(
            CASE WHEN estagio = 'finalizado'
            THEN EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000
            END
        )::BIGINT, 0) as tempo_medio_ms
    FROM fila_processamento_grupos;
END;
$$;


ALTER FUNCTION "public"."status_fila_grupos"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sync_cliente_to_bitrix"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'app_config'
    AS $$
DECLARE
  function_url TEXT := 'https://ofpnronthwcsybfxnxgj.supabase.co/functions/v1/sync-bitrix';
  service_role_key TEXT;
  payload JSON;
  response_id BIGINT;
BEGIN
  IF NEW.primeiro_nome IS NOT NULL AND 
     NEW.sobrenome IS NOT NULL AND 
     NEW.telefone IS NOT NULL AND 
     NEW.especialidade IS NOT NULL AND 
     NEW.email IS NOT NULL AND
     NEW.deleted_at IS NULL AND
     NEW.opt_out = FALSE THEN
    
    IF NEW.bitrix_id IS NULL OR TG_OP = 'UPDATE' THEN
      
      SELECT app_config.get_secret('supabase_service_role_key') INTO service_role_key;
      
      IF service_role_key IS NULL THEN
        RAISE WARNING 'Service role key não encontrada. Configure em app_config.secrets';
        RETURN NEW;
      END IF;
      
      payload := json_build_object('record', row_to_json(NEW));
      
      SELECT net.http_post(
        url := function_url,
        headers := jsonb_build_object(
          'Content-Type', 'application/json',
          'Authorization', 'Bearer ' || service_role_key
        ),
        body := payload::jsonb
      ) INTO response_id;
      
      RAISE NOTICE 'Sincronização iniciada para cliente: % (response_id: %)', NEW.id, response_id;
      
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."sync_cliente_to_bitrix"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."sync_cliente_to_bitrix"() IS 'Sincroniza cliente com Bitrix24 via Edge Function';



CREATE OR REPLACE FUNCTION "public"."top_grupos_vagas"("data_inicio" "date", "limite" integer DEFAULT 5) RETURNS TABLE("grupo_id" "uuid", "nome" "text", "total" bigint)
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        g.id as grupo_id,
        g.nome,
        COUNT(v.id)::BIGINT as total
    FROM grupos_whatsapp g
    JOIN vagas_grupo v ON v.grupo_origem_id = g.id
    WHERE v.created_at >= data_inicio
      AND v.status = 'importada'
    GROUP BY g.id, g.nome
    ORDER BY total DESC
    LIMIT limite;
END;
$$;


ALTER FUNCTION "public"."top_grupos_vagas"("data_inicio" "date", "limite" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_app_settings_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_app_settings_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_conhecimento_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_conhecimento_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_conversation_on_new_message"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
BEGIN
    IF NEW.conversation_id IS NOT NULL THEN
        UPDATE conversations 
        SET 
            message_count = message_count + 1,
            last_message_at = NEW.created_at,
            updated_at = NOW()
        WHERE id = NEW.conversation_id;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_conversation_on_new_message"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_data_anomalies_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_data_anomalies_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_doctor_state_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_doctor_state_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_external_handoffs_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_external_handoffs_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_fila_processamento_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_fila_processamento_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."validar_valor_vaga"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Se tipo e fixo, valor deve existir
    IF NEW.valor_tipo = 'fixo' AND (NEW.valor IS NULL OR NEW.valor <= 0) THEN
        RAISE EXCEPTION 'valor_tipo fixo requer valor > 0';
    END IF;

    -- Se tipo e faixa, pelo menos minimo ou maximo deve existir
    IF NEW.valor_tipo = 'faixa' AND NEW.valor_minimo IS NULL AND NEW.valor_maximo IS NULL THEN
        RAISE EXCEPTION 'valor_tipo faixa requer valor_minimo ou valor_maximo';
    END IF;

    -- Se tipo e a_combinar, valor deve ser null
    IF NEW.valor_tipo = 'a_combinar' AND NEW.valor IS NOT NULL AND NEW.valor > 0 THEN
        -- Nao bloquear, apenas ajustar para consistencia
        NEW.valor_tipo := 'fixo';
    END IF;

    -- Validar faixa coerente
    IF NEW.valor_minimo IS NOT NULL AND NEW.valor_maximo IS NOT NULL THEN
        IF NEW.valor_minimo > NEW.valor_maximo THEN
            RAISE EXCEPTION 'valor_minimo nao pode ser maior que valor_maximo';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."validar_valor_vaga"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "app_config"."secrets" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "secret" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "app_config"."secrets" OWNER TO "postgres";


COMMENT ON TABLE "app_config"."secrets" IS 'Armazena secrets de forma segura';



CREATE TABLE IF NOT EXISTS "public"."app_settings" (
    "key" "text" NOT NULL,
    "value" "text" NOT NULL,
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."app_settings" OWNER TO "postgres";


COMMENT ON TABLE "public"."app_settings" IS 'App settings and environment markers for deploy safety';



CREATE TABLE IF NOT EXISTS "public"."avaliacoes_qualidade" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "conversa_id" "uuid",
    "naturalidade" integer,
    "persona" integer,
    "objetivo" integer,
    "satisfacao" integer,
    "score_geral" integer,
    "avaliador" character varying(20) NOT NULL,
    "notas" "text",
    "tags" "text"[] DEFAULT '{}'::"text"[],
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "avaliacoes_qualidade_avaliador_check" CHECK ((("avaliador")::"text" = ANY ((ARRAY['auto'::character varying, 'gestor'::character varying])::"text"[]))),
    CONSTRAINT "avaliacoes_qualidade_naturalidade_check" CHECK ((("naturalidade" >= 1) AND ("naturalidade" <= 10))),
    CONSTRAINT "avaliacoes_qualidade_objetivo_check" CHECK ((("objetivo" >= 1) AND ("objetivo" <= 10))),
    CONSTRAINT "avaliacoes_qualidade_persona_check" CHECK ((("persona" >= 1) AND ("persona" <= 10))),
    CONSTRAINT "avaliacoes_qualidade_satisfacao_check" CHECK ((("satisfacao" >= 1) AND ("satisfacao" <= 10))),
    CONSTRAINT "avaliacoes_qualidade_score_geral_check" CHECK ((("score_geral" >= 1) AND ("score_geral" <= 10)))
);


ALTER TABLE "public"."avaliacoes_qualidade" OWNER TO "postgres";


COMMENT ON TABLE "public"."avaliacoes_qualidade" IS 'Avaliações de qualidade das conversas (automáticas e do gestor)';



CREATE TABLE IF NOT EXISTS "public"."briefing_config" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "google_doc_id" "text" NOT NULL,
    "google_doc_url" "text",
    "ultima_leitura" timestamp with time zone,
    "ultimo_hash" "text",
    "intervalo_leitura_minutos" integer DEFAULT 60,
    "ativo" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."briefing_config" OWNER TO "postgres";


COMMENT ON TABLE "public"."briefing_config" IS 'Configuração do Google Docs de briefing';



CREATE TABLE IF NOT EXISTS "public"."briefing_historico" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "briefing_config_id" "uuid",
    "conteudo_raw" "text" NOT NULL,
    "conteudo_parseado" "jsonb",
    "hash" "text" NOT NULL,
    "mudou" boolean DEFAULT false,
    "diretrizes_geradas" integer DEFAULT 0,
    "erros" "text"[],
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."briefing_historico" OWNER TO "postgres";


COMMENT ON TABLE "public"."briefing_historico" IS 'Histórico de leituras do briefing';



CREATE TABLE IF NOT EXISTS "public"."briefing_sync_log" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "doc_hash" "text" NOT NULL,
    "doc_title" "text",
    "conteudo_raw" "text",
    "parseado" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."briefing_sync_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."briefing_sync_log" IS 'Log de sincronizacoes do briefing do Google Docs';



COMMENT ON COLUMN "public"."briefing_sync_log"."doc_hash" IS 'Hash MD5 do conteudo para detectar mudancas';



COMMENT ON COLUMN "public"."briefing_sync_log"."parseado" IS 'JSON com secoes parseadas do briefing';



CREATE TABLE IF NOT EXISTS "public"."briefings_pendentes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "doc_id" "text" NOT NULL,
    "doc_nome" "text" NOT NULL,
    "doc_url" "text",
    "channel_id" "text" NOT NULL,
    "user_id" "text" NOT NULL,
    "plano" "jsonb" NOT NULL,
    "status" "text" DEFAULT 'aguardando'::"text" NOT NULL,
    "criado_em" timestamp with time zone DEFAULT "now"(),
    "atualizado_em" timestamp with time zone DEFAULT "now"(),
    "expira_em" timestamp with time zone DEFAULT ("now"() + '24:00:00'::interval),
    CONSTRAINT "briefings_pendentes_status_check" CHECK (("status" = ANY (ARRAY['aguardando'::"text", 'aprovado'::"text", 'ajuste'::"text", 'duvida'::"text", 'cancelado'::"text", 'executando'::"text", 'concluido'::"text"])))
);


ALTER TABLE "public"."briefings_pendentes" OWNER TO "postgres";


COMMENT ON TABLE "public"."briefings_pendentes" IS 'Briefings aguardando aprovação do gestor - Sprint 11';



CREATE TABLE IF NOT EXISTS "public"."business_alerts" (
    "alert_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "ts" timestamp with time zone DEFAULT "now"() NOT NULL,
    "alert_type" "text" NOT NULL,
    "severity" "text" NOT NULL,
    "title" "text" NOT NULL,
    "description" "text",
    "hospital_id" "uuid",
    "current_value" numeric,
    "baseline_value" numeric,
    "threshold_pct" numeric,
    "notified" boolean DEFAULT false,
    "notified_at" timestamp with time zone,
    "acknowledged" boolean DEFAULT false,
    "acknowledged_by" "text",
    "acknowledged_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."business_alerts" OWNER TO "postgres";


COMMENT ON TABLE "public"."business_alerts" IS 'Sprint 17 - E07: Historico de alertas de negocio';



COMMENT ON COLUMN "public"."business_alerts"."alert_type" IS 'Tipo: handoff_spike, recusa_spike, conversion_drop';



COMMENT ON COLUMN "public"."business_alerts"."severity" IS 'Severidade: warning, critical';



COMMENT ON COLUMN "public"."business_alerts"."notified" IS 'Se o alerta foi enviado ao Slack';



COMMENT ON COLUMN "public"."business_alerts"."acknowledged" IS 'Se o alerta foi reconhecido pelo operador';



CREATE TABLE IF NOT EXISTS "public"."business_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "ts" timestamp with time zone DEFAULT "now"() NOT NULL,
    "source" "text" NOT NULL,
    "cliente_id" "uuid",
    "vaga_id" "uuid",
    "hospital_id" "uuid",
    "conversation_id" "uuid",
    "interaction_id" bigint,
    "policy_decision_id" "uuid",
    "event_type" "text" NOT NULL,
    "event_props" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "dedupe_key" "text",
    CONSTRAINT "business_events_source_check" CHECK (("source" = ANY (ARRAY['pipeline'::"text", 'backend'::"text", 'db'::"text", 'heuristic'::"text", 'ops'::"text"])))
);


ALTER TABLE "public"."business_events" OWNER TO "postgres";


COMMENT ON TABLE "public"."business_events" IS 'Eventos de negocio para funil e metricas - Sprint 17';



COMMENT ON COLUMN "public"."business_events"."source" IS 'Origem: pipeline (processamento), backend (codigo), db (trigger), heuristic (detector), ops (manual)';



COMMENT ON COLUMN "public"."business_events"."event_type" IS 'Tipo: doctor_inbound, doctor_outbound, offer_teaser_sent, offer_made, offer_accepted, offer_declined, handoff_created, shift_completed';



COMMENT ON COLUMN "public"."business_events"."event_props" IS 'Propriedades especificas do evento (JSON)';



COMMENT ON COLUMN "public"."business_events"."dedupe_key" IS 'Chave de deduplicação para idempotência. Formato: {event_type}:{entity_id}:{ref}. NULL permite duplicatas (eventos sem necessidade de dedupe).';



CREATE TABLE IF NOT EXISTS "public"."campaign_contact_history" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "campaign_id" bigint NOT NULL,
    "campaign_type" "text" NOT NULL,
    "sent_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."campaign_contact_history" OWNER TO "postgres";


COMMENT ON TABLE "public"."campaign_contact_history" IS 'Histórico de campanhas enviadas para cooldown. Sprint 23 E05.';



COMMENT ON COLUMN "public"."campaign_contact_history"."campaign_type" IS 'Tipo da campanha (primeiro_contato, reativacao, followup, etc)';



CREATE TABLE IF NOT EXISTS "public"."envios" (
    "id" bigint NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "execucao_campanha_id" bigint,
    "campanha_id" bigint,
    "template_sid" "text",
    "template_friendly_name" "text",
    "conteudo_enviado" "text" NOT NULL,
    "variaveis_usadas" "jsonb",
    "status" "text" DEFAULT 'pendente'::"text" NOT NULL,
    "twilio_message_sid" "text",
    "twilio_status" "text",
    "twilio_error_code" "text",
    "twilio_error_message" "text",
    "origem" "text" DEFAULT 'automacao'::"text" NOT NULL,
    "enviado_por_user_id" "text",
    "deal_bitrix_id" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "enviado_em" timestamp with time zone,
    "entregue_em" timestamp with time zone,
    "visualizado_em" timestamp with time zone,
    "falhou_em" timestamp with time zone,
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."envios" OWNER TO "postgres";


COMMENT ON TABLE "public"."envios" IS 'Log completo de TODAS as mensagens enviadas (automação + manual)';



COMMENT ON COLUMN "public"."envios"."status" IS 'Status interno nosso';



COMMENT ON COLUMN "public"."envios"."twilio_status" IS 'Status bruto retornado pela API Twilio';



CREATE TABLE IF NOT EXISTS "public"."fila_mensagens" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "conversa_id" "uuid",
    "conteudo" "text" NOT NULL,
    "tipo" "text" DEFAULT 'lembrete'::"text" NOT NULL,
    "prioridade" integer DEFAULT 5,
    "status" "text" DEFAULT 'pendente'::"text",
    "agendar_para" timestamp with time zone,
    "enviada_em" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "max_tentativas" integer DEFAULT 3,
    "tentativas" integer DEFAULT 0,
    "erro" "text",
    "processando_desde" timestamp with time zone,
    "outcome" "public"."send_outcome",
    "outcome_reason_code" "text",
    "outcome_at" timestamp with time zone,
    "provider_message_id" "text",
    CONSTRAINT "fila_mensagens_prioridade_check" CHECK ((("prioridade" >= 0) AND ("prioridade" <= 10))),
    CONSTRAINT "fila_mensagens_status_check" CHECK (("status" = ANY (ARRAY['pendente'::"text", 'processando'::"text", 'enviada'::"text", 'erro'::"text", 'cancelada'::"text", 'bloqueada'::"text"])))
);


ALTER TABLE "public"."fila_mensagens" OWNER TO "postgres";


COMMENT ON TABLE "public"."fila_mensagens" IS 'Fila de mensagens agendadas para envio futuro';



COMMENT ON COLUMN "public"."fila_mensagens"."tipo" IS 'Tipo: lembrete, followup, campanha, etc';



COMMENT ON COLUMN "public"."fila_mensagens"."prioridade" IS 'Prioridade 0-10, maior = mais urgente';



COMMENT ON COLUMN "public"."fila_mensagens"."outcome" IS 'Resultado do envio: SENT, BLOCKED_*, DEDUPED, FAILED_*, BYPASS';



COMMENT ON COLUMN "public"."fila_mensagens"."outcome_reason_code" IS 'Codigo detalhado do motivo (ex: contact_cap, content_hash_window)';



COMMENT ON COLUMN "public"."fila_mensagens"."outcome_at" IS 'Timestamp de quando o outcome foi determinado';



COMMENT ON COLUMN "public"."fila_mensagens"."provider_message_id" IS 'ID da mensagem no provider (Evolution API) quando SENT';



CREATE OR REPLACE VIEW "public"."campaign_sends_raw" AS
 SELECT ('fm_'::"text" || ("fm"."id")::"text") AS "send_id",
    "fm"."cliente_id",
    (("fm"."metadata" ->> 'campanha_id'::"text"))::bigint AS "campaign_id",
    "fm"."tipo" AS "send_type",
    "fm"."status" AS "queue_status",
    ("fm"."outcome")::"text" AS "outcome",
    "fm"."outcome_reason_code",
    "fm"."provider_message_id",
    "fm"."created_at" AS "queued_at",
    "fm"."agendar_para" AS "scheduled_for",
    "fm"."enviada_em" AS "sent_at",
    "fm"."outcome_at",
    'fila_mensagens'::"text" AS "source_table",
        CASE
            WHEN ("fm"."provider_message_id" IS NOT NULL) THEN ('wa:'::"text" || "fm"."provider_message_id")
            ELSE ('fb:'::"text" || "md5"(((((("fm"."cliente_id")::"text" || ':'::"text") || COALESCE(("fm"."metadata" ->> 'campanha_id'::"text"), 'none'::"text")) || ':'::"text") || ("date_trunc"('hour'::"text", "fm"."created_at"))::"text")))
        END AS "canonical_key",
    ((
        CASE
            WHEN ("fm"."provider_message_id" IS NOT NULL) THEN 10
            ELSE 0
        END +
        CASE
            WHEN ("fm"."outcome" IS NOT NULL) THEN 5
            ELSE 0
        END) + 3) AS "dedup_score"
   FROM "public"."fila_mensagens" "fm"
  WHERE (("fm"."metadata" ->> 'campanha_id'::"text") IS NOT NULL)
UNION ALL
 SELECT ('env_'::"text" || ("e"."id")::"text") AS "send_id",
    "e"."cliente_id",
    "e"."campanha_id" AS "campaign_id",
    'campanha'::"text" AS "send_type",
    "e"."status" AS "queue_status",
        CASE
            WHEN ("e"."status" = ANY (ARRAY['enviado'::"text", 'entregue'::"text"])) THEN 'SENT'::"text"
            WHEN ("e"."status" = 'falhou'::"text") THEN 'FAILED_PROVIDER'::"text"
            WHEN ("e"."status" = 'bloqueado'::"text") THEN 'BLOCKED_OPTED_OUT'::"text"
            ELSE NULL::"text"
        END AS "outcome",
    "e"."twilio_error_message" AS "outcome_reason_code",
    "e"."twilio_message_sid" AS "provider_message_id",
    "e"."created_at" AS "queued_at",
    NULL::timestamp with time zone AS "scheduled_for",
    "e"."enviado_em" AS "sent_at",
    COALESCE("e"."enviado_em", "e"."falhou_em") AS "outcome_at",
    'envios'::"text" AS "source_table",
        CASE
            WHEN ("e"."twilio_message_sid" IS NOT NULL) THEN ('wa:'::"text" || "e"."twilio_message_sid")
            ELSE ('fb:'::"text" || "md5"(((((("e"."cliente_id")::"text" || ':'::"text") || COALESCE(("e"."campanha_id")::"text", 'none'::"text")) || ':'::"text") || ("date_trunc"('hour'::"text", "e"."created_at"))::"text")))
        END AS "canonical_key",
    ((
        CASE
            WHEN ("e"."twilio_message_sid" IS NOT NULL) THEN 10
            ELSE 0
        END +
        CASE
            WHEN ("e"."status" = ANY (ARRAY['enviado'::"text", 'entregue'::"text", 'falhou'::"text"])) THEN 5
            ELSE 0
        END) + 1) AS "dedup_score"
   FROM "public"."envios" "e"
  WHERE ("e"."campanha_id" IS NOT NULL);


ALTER VIEW "public"."campaign_sends_raw" OWNER TO "postgres";


COMMENT ON VIEW "public"."campaign_sends_raw" IS 'View unificada de envios de campanha (raw, não deduplicada). Sprint 24 E05.';



CREATE OR REPLACE VIEW "public"."campaign_sends" AS
 SELECT DISTINCT ON ("canonical_key") "send_id",
    "cliente_id",
    "campaign_id",
    "send_type",
    "queue_status",
    "outcome",
    "outcome_reason_code",
    "provider_message_id",
    "queued_at",
    "scheduled_for",
    "sent_at",
    "outcome_at",
    "source_table",
    "canonical_key"
   FROM "public"."campaign_sends_raw"
  ORDER BY "canonical_key", "dedup_score" DESC, "queued_at" DESC;


ALTER VIEW "public"."campaign_sends" OWNER TO "postgres";


COMMENT ON VIEW "public"."campaign_sends" IS 'View deduplicada de envios de campanha. Usa canonical_key para eliminar duplicatas entre fila_mensagens e envios. Sprint 24 E06.';



CREATE OR REPLACE VIEW "public"."campaign_metrics" AS
 SELECT "campaign_id",
    "count"(*) AS "total_sends",
    "count"(*) FILTER (WHERE ("outcome" = 'SENT'::"text")) AS "delivered",
    "count"(*) FILTER (WHERE ("outcome" = 'BYPASS'::"text")) AS "bypassed",
    "count"(*) FILTER (WHERE ("outcome" = ANY (ARRAY['SENT'::"text", 'BYPASS'::"text"]))) AS "delivered_total",
    "count"(*) FILTER (WHERE ("outcome" ~~ 'BLOCKED_%'::"text")) AS "blocked",
    "count"(*) FILTER (WHERE ("outcome" = 'DEDUPED'::"text")) AS "deduped",
    "count"(*) FILTER (WHERE ("outcome" ~~ 'FAILED_%'::"text")) AS "failed",
    "count"(*) FILTER (WHERE ("outcome" = 'FAILED_VALIDATION'::"text")) AS "failed_validation",
    "count"(*) FILTER (WHERE ("outcome" = 'FAILED_BANNED'::"text")) AS "failed_banned",
    "count"(*) FILTER (WHERE ("outcome" = ANY (ARRAY['FAILED_PROVIDER'::"text", 'FAILED_RATE_LIMIT'::"text", 'FAILED_CIRCUIT_OPEN'::"text"]))) AS "failed_provider",
    "count"(*) FILTER (WHERE ("outcome" IS NULL)) AS "pending",
    "round"(((("count"(*) FILTER (WHERE ("outcome" = 'SENT'::"text")))::numeric / (NULLIF("count"(*), 0))::numeric) * (100)::numeric), 2) AS "delivery_rate",
    "round"(((("count"(*) FILTER (WHERE ("outcome" = ANY (ARRAY['SENT'::"text", 'BYPASS'::"text"]))))::numeric / (NULLIF("count"(*), 0))::numeric) * (100)::numeric), 2) AS "delivery_rate_total",
    "round"(((("count"(*) FILTER (WHERE ("outcome" ~~ 'BLOCKED_%'::"text")))::numeric / (NULLIF("count"(*), 0))::numeric) * (100)::numeric), 2) AS "block_rate",
    "round"(((("count"(*) FILTER (WHERE ("outcome" = 'FAILED_VALIDATION'::"text")))::numeric / (NULLIF("count"(*), 0))::numeric) * (100)::numeric), 2) AS "validation_fail_rate",
    "round"(((("count"(*) FILTER (WHERE ("outcome" = 'FAILED_BANNED'::"text")))::numeric / (NULLIF("count"(*), 0))::numeric) * (100)::numeric), 2) AS "banned_rate",
    "min"("queued_at") AS "first_send_at",
    "max"("sent_at") AS "last_send_at",
    "count"(*) FILTER (WHERE ("source_table" = 'fila_mensagens'::"text")) AS "from_fila_mensagens",
    "count"(*) FILTER (WHERE ("source_table" = 'envios'::"text")) AS "from_envios_legado"
   FROM "public"."campaign_sends"
  GROUP BY "campaign_id";


ALTER VIEW "public"."campaign_metrics" OWNER TO "postgres";


COMMENT ON VIEW "public"."campaign_metrics" IS 'Métricas agregadas por campanha. Sprint 23: Inclui breakdown de falhas para diagnóstico.';



CREATE TABLE IF NOT EXISTS "public"."campanhas" (
    "id" bigint NOT NULL,
    "nome_template" "text",
    "categoria" "text",
    "idioma" "text",
    "corpo" "text",
    "tom" "text",
    "template_sid" "text",
    "friendly_name" "text",
    "tipo_campanha" "text" DEFAULT 'oferta_plantao'::"text",
    "aprovado_meta" boolean DEFAULT true,
    "data_aprovacao_meta" timestamp with time zone,
    "pressure_points" integer DEFAULT 25,
    "ativo" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "objetivo" "text",
    "hipotese" "text",
    "kpi_primaria" "text",
    "kpi_secundaria" "text",
    "playbook_versao" "text",
    "meta_status" "text",
    "meta_error_reason" "text",
    "status" "text" DEFAULT 'rascunho'::"text",
    "agendar_para" timestamp with time zone,
    "iniciada_em" timestamp with time zone,
    "concluida_em" timestamp with time zone,
    CONSTRAINT "campanhas_status_check" CHECK (("status" = ANY (ARRAY['rascunho'::"text", 'agendada'::"text", 'ativa'::"text", 'pausada'::"text", 'concluida'::"text", 'cancelada'::"text"])))
);


ALTER TABLE "public"."campanhas" OWNER TO "postgres";


COMMENT ON COLUMN "public"."campanhas"."tipo_campanha" IS 'discovery, engajamento, conversao_cadastro, oferta_plantao, reativacao, feedback';



COMMENT ON COLUMN "public"."campanhas"."pressure_points" IS 'Pontos que adiciona ao pressure_score do médico ao enviar';



COMMENT ON COLUMN "public"."campanhas"."status" IS 'Status da campanha: rascunho, agendada, ativa, pausada, concluida, cancelada';



COMMENT ON COLUMN "public"."campanhas"."agendar_para" IS 'Data/hora para iniciar a campanha automaticamente';



COMMENT ON COLUMN "public"."campanhas"."iniciada_em" IS 'Data/hora em que a campanha foi iniciada';



COMMENT ON COLUMN "public"."campanhas"."concluida_em" IS 'Data/hora em que a campanha foi concluida';



CREATE SEQUENCE IF NOT EXISTS "public"."campanhas_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."campanhas_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."campanhas_id_seq" OWNED BY "public"."campanhas"."id";



CREATE TABLE IF NOT EXISTS "public"."clientes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "primeiro_nome" character varying(50),
    "sobrenome" character varying(100),
    "cpf" character varying(11),
    "crm" character varying(20),
    "especialidade" character varying(50),
    "telefone" character varying(20) NOT NULL,
    "email" character varying(100),
    "cidade" character varying(50),
    "estado" character varying(2),
    "bitrix_id" integer,
    "origem" character varying(100),
    "status" character varying(50) DEFAULT 'novo'::character varying,
    "observacoes" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "created_by" character varying(255),
    "deleted_at" timestamp with time zone,
    "opt_out" boolean DEFAULT false,
    "opt_out_data" timestamp with time zone,
    "ultima_mensagem_data" timestamp with time zone,
    "ultima_mensagem_tipo" "text",
    "total_interacoes" integer DEFAULT 0,
    "stage_jornada" "text" DEFAULT 'novo'::"text",
    "pressure_score_atual" integer DEFAULT 0,
    "deals_ativos_bitrix" "jsonb",
    "tags" "jsonb",
    "app_cadastrado" boolean DEFAULT false,
    "titulo" "text",
    "contexto_consolidado" "text",
    "embedding" "public"."vector"(1536),
    "ultima_interacao_resumo" "text",
    "preferencias_detectadas" "jsonb" DEFAULT '{}'::"jsonb",
    "flags_comportamento" "jsonb" DEFAULT '{}'::"jsonb",
    "qualification_score" double precision DEFAULT 0,
    "preferencias_conhecidas" "jsonb" DEFAULT '{}'::"jsonb",
    "grupo_piloto" boolean DEFAULT false,
    "opted_out" boolean DEFAULT false,
    "opted_out_at" timestamp with time zone,
    "opted_out_reason" "text",
    "ultima_abertura" "jsonb",
    CONSTRAINT "check_estado" CHECK (((("estado")::"text" ~* '^[A-Z]{2}$'::"text") OR ("estado" IS NULL)))
);


ALTER TABLE "public"."clientes" OWNER TO "postgres";


COMMENT ON COLUMN "public"."clientes"."opt_out" IS 'Se o médico pediu para parar de receber mensagens';



COMMENT ON COLUMN "public"."clientes"."ultima_mensagem_tipo" IS 'Tipo da última campanha enviada (discovery, oferta, etc)';



COMMENT ON COLUMN "public"."clientes"."stage_jornada" IS 'novo, aguardando_resposta, nao_respondeu, respondeu, em_conversacao, inativo, qualificado, cadastrado, ativo, perdido, opt_out';



COMMENT ON COLUMN "public"."clientes"."pressure_score_atual" IS 'Score de saturação (0-100). >70 = alta, >90 = saturado';



COMMENT ON COLUMN "public"."clientes"."tags" IS 'Array livre de tags. Ex: ["vip", "respondeu_rapido"]';



COMMENT ON COLUMN "public"."clientes"."contexto_consolidado" IS 'Resumo consolidado do histórico do médico para o agente de IA';



COMMENT ON COLUMN "public"."clientes"."embedding" IS 'Embedding do contexto consolidado para busca semântica (1536 dims = OpenAI ada-002)';



COMMENT ON COLUMN "public"."clientes"."ultima_interacao_resumo" IS 'Resumo da última interação para quick context';



COMMENT ON COLUMN "public"."clientes"."preferencias_detectadas" IS 'Preferências extraídas das conversas. Ex: {"turno": "noturno", "regiao": "ABC"}';



COMMENT ON COLUMN "public"."clientes"."flags_comportamento" IS 'Flags comportamentais. Ex: {"responde_rapido": true, "ja_cancelou": false}';



COMMENT ON COLUMN "public"."clientes"."qualification_score" IS 'Score de qualificação 0-1, quão completo está o perfil';



COMMENT ON COLUMN "public"."clientes"."preferencias_conhecidas" IS 'Preferências conhecidas. Ex: {"turnos": ["noturno"], "hospitais_preferidos": ["HU SBC"]}';



COMMENT ON COLUMN "public"."clientes"."grupo_piloto" IS 'Marca médicos selecionados para o piloto do MVP';



COMMENT ON COLUMN "public"."clientes"."opted_out" IS 'Se o cliente pediu para não receber mais mensagens';



COMMENT ON COLUMN "public"."clientes"."opted_out_at" IS 'Data/hora do opt-out';



COMMENT ON COLUMN "public"."clientes"."opted_out_reason" IS 'Mensagem que triggou o opt-out';



COMMENT ON COLUMN "public"."clientes"."ultima_abertura" IS 'Ultima abertura usada para este medico (evita repeticao)';



CREATE TABLE IF NOT EXISTS "public"."clientes_log" (
    "id" bigint NOT NULL,
    "cliente_id" "uuid",
    "acao" character varying(50),
    "dados_antigos" "jsonb",
    "dados_novos" "jsonb",
    "usuario" character varying(255),
    "timestamp" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."clientes_log" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."clientes_log_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."clientes_log_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."clientes_log_id_seq" OWNED BY "public"."clientes_log"."id";



CREATE TABLE IF NOT EXISTS "public"."conhecimento_julia" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "arquivo" "text" NOT NULL,
    "secao" "text",
    "subsecao" "text",
    "conteudo" "text" NOT NULL,
    "tipo" "text" NOT NULL,
    "subtipo" "text",
    "tags" "text"[],
    "embedding" "public"."vector"(1024),
    "versao" "text" DEFAULT 'v1'::"text",
    "ativo" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."conhecimento_julia" OWNER TO "postgres";


COMMENT ON TABLE "public"."conhecimento_julia" IS 'Base de conhecimento indexada para RAG dinâmico da Julia';



COMMENT ON COLUMN "public"."conhecimento_julia"."tipo" IS 'Categoria: perfil, objecao, erro, conversa, guardrail, handoff, escalacao, fundacao, negociacao, preferencias, abertura';



CREATE TABLE IF NOT EXISTS "public"."contatos_grupo" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "jid" "text" NOT NULL,
    "telefone" "text",
    "nome" "text",
    "empresa" "text",
    "tipo" "text" DEFAULT 'desconhecido'::"text",
    "total_mensagens" integer DEFAULT 0,
    "total_vagas_postadas" integer DEFAULT 0,
    "total_vagas_validas" integer DEFAULT 0,
    "taxa_qualidade" double precision,
    "cliente_id" "uuid",
    "primeiro_contato" timestamp with time zone,
    "ultimo_contato" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."contatos_grupo" OWNER TO "postgres";


COMMENT ON TABLE "public"."contatos_grupo" IS 'Contatos que postam vagas nos grupos de WhatsApp';



COMMENT ON COLUMN "public"."contatos_grupo"."jid" IS 'JID único do contato no formato 5511999999999@s.whatsapp.net';



COMMENT ON COLUMN "public"."contatos_grupo"."tipo" IS 'Tipo do contato: escalista, hospital, medico, desconhecido';



COMMENT ON COLUMN "public"."contatos_grupo"."taxa_qualidade" IS 'Percentual de vagas válidas (importadas) deste contato';



CREATE TABLE IF NOT EXISTS "public"."conversations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "execucao_campanha_id" bigint,
    "campanha_id" bigint,
    "instance_id" character varying(100),
    "status" character varying(50) DEFAULT 'active'::character varying,
    "controlled_by" character varying(20) DEFAULT 'ai'::character varying,
    "controlled_by_user_id" "uuid",
    "escalation_reason" "text",
    "message_count" integer DEFAULT 0,
    "last_message_at" timestamp with time zone,
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "chatwoot_conversation_id" "text",
    "chatwoot_contact_id" "text",
    "stage" character varying(50) DEFAULT 'novo'::character varying,
    "ultima_mensagem_em" timestamp with time zone,
    "pausado_ate" timestamp with time zone,
    "first_touch_campaign_id" bigint,
    "first_touch_type" "text",
    "first_touch_at" timestamp with time zone,
    "last_touch_campaign_id" bigint,
    "last_touch_type" "text",
    "last_touch_at" timestamp with time zone,
    CONSTRAINT "conversations_controlled_by_check" CHECK ((("controlled_by")::"text" = ANY ((ARRAY['ai'::character varying, 'human'::character varying])::"text"[]))),
    CONSTRAINT "conversations_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['active'::character varying, 'paused'::character varying, 'escalated'::character varying, 'completed'::character varying, 'abandoned'::character varying])::"text"[])))
);


ALTER TABLE "public"."conversations" OWNER TO "postgres";


COMMENT ON TABLE "public"."conversations" IS 'Agrupa mensagens em conversas com controle de handoff IA/humano';



COMMENT ON COLUMN "public"."conversations"."status" IS 'active, paused, escalated, completed, abandoned';



COMMENT ON COLUMN "public"."conversations"."controlled_by" IS 'ai ou human - quem está no controle da conversa';



COMMENT ON COLUMN "public"."conversations"."stage" IS 'Stage do follow-up: novo, msg_enviada, followup_1_enviado, followup_2_enviado, nao_respondeu, respondeu, reservou, recontato';



COMMENT ON COLUMN "public"."conversations"."ultima_mensagem_em" IS 'Data/hora da última mensagem (para calcular delay do follow-up)';



COMMENT ON COLUMN "public"."conversations"."pausado_ate" IS 'Se não null, conversa está pausada até esta data';



COMMENT ON COLUMN "public"."conversations"."first_touch_campaign_id" IS 'ID da primeira campanha que gerou conversa (atribuição analítica)';



COMMENT ON COLUMN "public"."conversations"."first_touch_type" IS 'Tipo do primeiro touch (campaign, followup, manual, slack)';



COMMENT ON COLUMN "public"."conversations"."first_touch_at" IS 'Timestamp do primeiro touch';



COMMENT ON COLUMN "public"."conversations"."last_touch_campaign_id" IS 'ID da última campanha que tocou (atribuição operacional)';



COMMENT ON COLUMN "public"."conversations"."last_touch_type" IS 'Tipo do último touch';



COMMENT ON COLUMN "public"."conversations"."last_touch_at" IS 'Timestamp do último touch';



CREATE TABLE IF NOT EXISTS "public"."data_anomalies" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "anomaly_type" "text" NOT NULL,
    "entity_type" "text" NOT NULL,
    "entity_id" "uuid" NOT NULL,
    "expected" "text" NOT NULL,
    "found" "text",
    "first_seen_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_seen_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "occurrence_count" integer DEFAULT 1 NOT NULL,
    "severity" "text" DEFAULT 'warning'::"text" NOT NULL,
    "details" "jsonb" DEFAULT '{}'::"jsonb",
    "reconciliation_run_id" "uuid",
    "resolved" boolean DEFAULT false,
    "resolved_at" timestamp with time zone,
    "resolved_by" "text",
    "resolution_notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."data_anomalies" OWNER TO "postgres";


COMMENT ON TABLE "public"."data_anomalies" IS 'Sprint 18 - E11: Historico de anomalias de dados com tracking de recorrencia';



COMMENT ON COLUMN "public"."data_anomalies"."expected" IS 'O que deveria existir (ex: "evento offer_accepted")';



COMMENT ON COLUMN "public"."data_anomalies"."found" IS 'O que foi encontrado (ex: "nenhum evento" ou "status=aberta")';



COMMENT ON COLUMN "public"."data_anomalies"."occurrence_count" IS 'Quantas vezes essa anomalia foi detectada';



CREATE TABLE IF NOT EXISTS "public"."diretrizes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tipo" "text" NOT NULL,
    "conteudo" "text" NOT NULL,
    "contexto" "text",
    "cliente_id" "uuid",
    "vaga_id" "uuid",
    "prioridade" integer DEFAULT 0,
    "origem" "text" NOT NULL,
    "criado_por" "text",
    "ativo" boolean DEFAULT true,
    "expira_em" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "diretrizes_origem_check" CHECK (("origem" = ANY (ARRAY['google_docs'::"text", 'slack'::"text", 'sistema'::"text"]))),
    CONSTRAINT "diretrizes_tipo_check" CHECK (("tipo" = ANY (ARRAY['foco'::"text", 'foco_semana'::"text", 'evitar'::"text", 'tom'::"text", 'tom_semana'::"text", 'meta'::"text", 'vip'::"text", 'bloqueado'::"text", 'vaga_prioritaria'::"text", 'instrucao_geral'::"text", 'margem_negociacao'::"text", 'observacoes'::"text"])))
);


ALTER TABLE "public"."diretrizes" OWNER TO "postgres";


COMMENT ON TABLE "public"."diretrizes" IS 'Diretrizes ativas que guiam o comportamento da Júlia';



CREATE TABLE IF NOT EXISTS "public"."doctor_context" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "content" "text" NOT NULL,
    "source" character varying(50) DEFAULT 'conversation'::character varying NOT NULL,
    "source_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "tipo" character varying(50) DEFAULT 'info_pessoal'::character varying,
    "confianca" character varying(20) DEFAULT 'media'::character varying,
    "embedding" "public"."vector"(1024)
);


ALTER TABLE "public"."doctor_context" OWNER TO "postgres";


COMMENT ON TABLE "public"."doctor_context" IS 'Chunks de contexto do médico para RAG - memória de longo prazo do agente';



COMMENT ON COLUMN "public"."doctor_context"."content" IS 'Texto do contexto (resumo de interação, preferência detectada, etc)';



COMMENT ON COLUMN "public"."doctor_context"."source" IS 'Origem: conversation, manual, import, system';



COMMENT ON COLUMN "public"."doctor_context"."source_id" IS 'ID da conversa ou outro objeto que originou este contexto';



COMMENT ON COLUMN "public"."doctor_context"."tipo" IS 'Tipo da memoria: preferencia, restricao, info_pessoal, historico, comportamento';



COMMENT ON COLUMN "public"."doctor_context"."confianca" IS 'Nivel de confianca: alta, media, baixa';



COMMENT ON COLUMN "public"."doctor_context"."embedding" IS 'Embedding do conteudo para busca semantica (1024 dims = Voyage AI voyage-3.5-lite)';



CREATE TABLE IF NOT EXISTS "public"."doctor_state" (
    "cliente_id" "uuid" NOT NULL,
    "permission_state" "text" DEFAULT 'none'::"text" NOT NULL,
    "cooling_off_until" timestamp with time zone,
    "temperature" numeric(3,2) DEFAULT 0.50 NOT NULL,
    "temperature_trend" "text" DEFAULT 'stable'::"text" NOT NULL,
    "temperature_band" "text" GENERATED ALWAYS AS (
CASE
    WHEN ("temperature" < 0.33) THEN 'cold'::"text"
    WHEN ("temperature" < 0.66) THEN 'warm'::"text"
    ELSE 'hot'::"text"
END) STORED,
    "risk_tolerance" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "last_inbound_at" timestamp with time zone,
    "last_outbound_at" timestamp with time zone,
    "last_outbound_actor" "text",
    "next_allowed_at" timestamp with time zone,
    "contact_count_7d" integer DEFAULT 0 NOT NULL,
    "active_objection" "text",
    "objection_severity" "text",
    "objection_detected_at" timestamp with time zone,
    "objection_resolved_at" timestamp with time zone,
    "pending_action" "text",
    "current_intent" "text",
    "lifecycle_stage" "text" DEFAULT 'novo'::"text" NOT NULL,
    "flags" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "last_decay_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_touch_at" timestamp with time zone,
    "last_touch_method" "text",
    "last_touch_campaign_id" bigint,
    CONSTRAINT "doctor_state_last_outbound_actor_check" CHECK (("last_outbound_actor" = ANY (ARRAY['julia'::"text", 'humano'::"text"]))),
    CONSTRAINT "doctor_state_lifecycle_stage_check" CHECK (("lifecycle_stage" = ANY (ARRAY['novo'::"text", 'prospecting'::"text", 'engaged'::"text", 'qualified'::"text", 'active'::"text", 'churned'::"text"]))),
    CONSTRAINT "doctor_state_objection_severity_check" CHECK (("objection_severity" = ANY (ARRAY['low'::"text", 'medium'::"text", 'high'::"text", 'grave'::"text"]))),
    CONSTRAINT "doctor_state_permission_state_check" CHECK (("permission_state" = ANY (ARRAY['none'::"text", 'initial'::"text", 'active'::"text", 'cooling_off'::"text", 'opted_out'::"text"]))),
    CONSTRAINT "doctor_state_risk_tolerance_check" CHECK (("risk_tolerance" = ANY (ARRAY['unknown'::"text", 'low'::"text", 'medium'::"text", 'high'::"text"]))),
    CONSTRAINT "doctor_state_temperature_check" CHECK ((("temperature" >= 0.00) AND ("temperature" <= 1.00))),
    CONSTRAINT "doctor_state_temperature_trend_check" CHECK (("temperature_trend" = ANY (ARRAY['warming'::"text", 'cooling'::"text", 'stable'::"text"])))
);


ALTER TABLE "public"."doctor_state" OWNER TO "postgres";


COMMENT ON TABLE "public"."doctor_state" IS 'Estado dinâmico do relacionamento com cada médico - Sprint 15 Policy Engine';



COMMENT ON COLUMN "public"."doctor_state"."permission_state" IS 'none=nunca conversou, initial=contato inicial, active=conversa saudável, cooling_off=pausa por atrito, opted_out=não contatar';



COMMENT ON COLUMN "public"."doctor_state"."temperature" IS 'Engajamento 0.0 (frio) a 1.0 (quente)';



COMMENT ON COLUMN "public"."doctor_state"."temperature_band" IS 'Faixa derivada: cold (<0.33), warm (0.33-0.66), hot (>0.66)';



COMMENT ON COLUMN "public"."doctor_state"."active_objection" IS 'Objeção não resolvida - persiste até resolve_objection()';



COMMENT ON COLUMN "public"."doctor_state"."last_decay_at" IS 'Última vez que decay foi aplicado - para idempotência do job';



COMMENT ON COLUMN "public"."doctor_state"."last_touch_at" IS 'Timestamp do último envio outbound para este médico';



COMMENT ON COLUMN "public"."doctor_state"."last_touch_method" IS 'Método do último envio: campaign, followup, reply, etc';



COMMENT ON COLUMN "public"."doctor_state"."last_touch_campaign_id" IS 'ID da campanha do último touch. BIGINT para corresponder a campanhas.id';



CREATE SEQUENCE IF NOT EXISTS "public"."envios_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."envios_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."envios_id_seq" OWNED BY "public"."envios"."id";



CREATE TABLE IF NOT EXISTS "public"."especialidades" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "nome" character varying NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."especialidades" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."especialidades_alias" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "especialidade_id" "uuid" NOT NULL,
    "alias" "text" NOT NULL,
    "alias_normalizado" "text" NOT NULL,
    "origem" "text" DEFAULT 'sistema'::"text",
    "criado_por" "text",
    "confianca" double precision DEFAULT 1.0,
    "confirmado" boolean DEFAULT false,
    "vezes_usado" integer DEFAULT 0,
    "ultimo_uso" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."especialidades_alias" OWNER TO "postgres";


COMMENT ON TABLE "public"."especialidades_alias" IS 'Variações de nomes de especialidades para fuzzy match';



COMMENT ON COLUMN "public"."especialidades_alias"."alias" IS 'Nome alternativo (ex: CM, cardio, GO)';



COMMENT ON COLUMN "public"."especialidades_alias"."alias_normalizado" IS 'Versão normalizada para busca';



CREATE TABLE IF NOT EXISTS "public"."execucoes_campanhas" (
    "id" bigint NOT NULL,
    "nome_execucao" "text" NOT NULL,
    "descricao" "text",
    "campanhas_ids" bigint[],
    "tipo_execucao" "text" DEFAULT 'simples'::"text",
    "status" "text" DEFAULT 'rascunho'::"text" NOT NULL,
    "data_hora_agendada" timestamp with time zone,
    "data_hora_inicio" timestamp with time zone,
    "data_hora_fim" timestamp with time zone,
    "data_hora_pausada" timestamp with time zone,
    "segmento_filtros" "jsonb",
    "especialidades" "text"[],
    "estados" "text"[],
    "cidades" "text"[],
    "quantidade_alvo" integer,
    "quantidade_enviada" integer DEFAULT 0,
    "quantidade_entregue" integer DEFAULT 0,
    "quantidade_sucesso" integer DEFAULT 0,
    "quantidade_falha" integer DEFAULT 0,
    "quantidade_respostas" integer DEFAULT 0,
    "parametros_personalizacao" "jsonb",
    "criado_por" "text",
    "pausado_por" "text",
    "cancelado_por" "text",
    "observacoes" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "ia_config" "jsonb",
    "ia_resultados" "jsonb"
);


ALTER TABLE "public"."execucoes_campanhas" OWNER TO "postgres";


COMMENT ON TABLE "public"."execucoes_campanhas" IS 'Instâncias de envio de campanhas (agendadas ou executadas)';



COMMENT ON COLUMN "public"."execucoes_campanhas"."segmento_filtros" IS 'JSON com regras. Ex: {"especialidade": ["cardiologia"], "status": ["novo"]}';



CREATE SEQUENCE IF NOT EXISTS "public"."execucoes_campanhas_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."execucoes_campanhas_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."execucoes_campanhas_id_seq" OWNED BY "public"."execucoes_campanhas"."id";



CREATE TABLE IF NOT EXISTS "public"."external_contacts" (
    "telefone" "text" NOT NULL,
    "nome" "text",
    "empresa" "text",
    "permission_state" "text" DEFAULT 'active'::"text",
    "opted_out_at" timestamp with time zone,
    "opted_out_reason" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "external_contacts_permission_state_check" CHECK (("permission_state" = ANY (ARRAY['active'::"text", 'opted_out'::"text"])))
);


ALTER TABLE "public"."external_contacts" OWNER TO "postgres";


COMMENT ON TABLE "public"."external_contacts" IS 'Contatos externos (divulgadores) para ponte médico-divulgador';



COMMENT ON COLUMN "public"."external_contacts"."permission_state" IS 'Estado de permissão: active ou opted_out';



COMMENT ON COLUMN "public"."external_contacts"."opted_out_at" IS 'Data/hora do opt-out';



COMMENT ON COLUMN "public"."external_contacts"."opted_out_reason" IS 'Motivo do opt-out (reclamação, bloqueio, etc)';



CREATE TABLE IF NOT EXISTS "public"."external_handoffs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "vaga_id" "uuid" NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "divulgador_nome" "text",
    "divulgador_telefone" "text" NOT NULL,
    "divulgador_empresa" "text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "reserved_until" timestamp with time zone NOT NULL,
    "last_followup_at" timestamp with time zone,
    "followup_count" integer DEFAULT 0,
    "confirmed_at" timestamp with time zone,
    "confirmed_by" "text",
    "confirmation_source" "text",
    "expired_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "external_handoffs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'contacted'::"text", 'confirmed'::"text", 'not_confirmed'::"text", 'expired'::"text"])))
);


ALTER TABLE "public"."external_handoffs" OWNER TO "postgres";


COMMENT ON TABLE "public"."external_handoffs" IS 'Ponte automatica medico-divulgador - Sprint 20';



COMMENT ON COLUMN "public"."external_handoffs"."status" IS 'pending=aguardando, contacted=msg enviada, confirmed=fechou, not_confirmed=nao fechou, expired=expirou';



COMMENT ON COLUMN "public"."external_handoffs"."reserved_until" IS 'Prazo para confirmacao (48h por padrao)';



COMMENT ON COLUMN "public"."external_handoffs"."confirmed_by" IS 'link ou keyword';



CREATE TABLE IF NOT EXISTS "public"."feature_flags" (
    "key" "text" NOT NULL,
    "value" "jsonb" NOT NULL,
    "description" "text",
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_by" "text"
);


ALTER TABLE "public"."feature_flags" OWNER TO "postgres";


COMMENT ON TABLE "public"."feature_flags" IS 'Flags de funcionalidades para controle sem deploy (Sprint 16)';



COMMENT ON COLUMN "public"."feature_flags"."key" IS 'Nome único da flag';



COMMENT ON COLUMN "public"."feature_flags"."value" IS 'Valor da flag (JSON para flexibilidade)';



COMMENT ON COLUMN "public"."feature_flags"."description" IS 'Descrição do que a flag controla';



COMMENT ON COLUMN "public"."feature_flags"."updated_by" IS 'Quem alterou por último';



CREATE TABLE IF NOT EXISTS "public"."feedbacks_gestor" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid",
    "conversa_id" "uuid",
    "interacao_id" bigint,
    "tipo" "text" NOT NULL,
    "conteudo" "text" NOT NULL,
    "impacto" "text",
    "aplicado" boolean DEFAULT false,
    "aplicado_em" timestamp with time zone,
    "criado_por" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "feedbacks_gestor_impacto_check" CHECK (("impacto" = ANY (ARRAY['aplicar_sempre'::"text", 'aplicar_este_medico'::"text", 'apenas_registro'::"text"]))),
    CONSTRAINT "feedbacks_gestor_tipo_check" CHECK (("tipo" = ANY (ARRAY['positivo'::"text", 'negativo'::"text", 'correcao'::"text", 'instrucao'::"text", 'contexto'::"text"])))
);


ALTER TABLE "public"."feedbacks_gestor" OWNER TO "postgres";


COMMENT ON TABLE "public"."feedbacks_gestor" IS 'Feedbacks do gestor sobre conversas e mensagens';



CREATE TABLE IF NOT EXISTS "public"."fila_processamento_grupos" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "mensagem_id" "uuid" NOT NULL,
    "estagio" character varying(50) DEFAULT 'pendente'::character varying NOT NULL,
    "tentativas" integer DEFAULT 0,
    "max_tentativas" integer DEFAULT 3,
    "ultimo_erro" "text",
    "proximo_retry" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "vaga_grupo_id" "uuid"
);


ALTER TABLE "public"."fila_processamento_grupos" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."formas_recebimento" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "forma_recebimento" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."formas_recebimento" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."interacoes" (
    "id" bigint NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "envio_id" bigint,
    "deal_bitrix_id" "text",
    "parent_id" bigint,
    "origem" "text" NOT NULL,
    "tipo" "text" NOT NULL,
    "canal" "text" DEFAULT 'whatsapp'::"text" NOT NULL,
    "conteudo" "text",
    "conteudo_original" "text",
    "anexos" "jsonb",
    "autor_user_id" "text",
    "autor_nome" "text",
    "autor_tipo" "text",
    "sentimento_score" integer,
    "classificacao_ia" "jsonb",
    "requer_followup" boolean DEFAULT false,
    "prioridade" "text",
    "bitrix_message_id" "text",
    "bitrix_activity_id" "text",
    "twilio_message_sid" "text",
    "contexto_conversa" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "sincronizado_bitrix_em" timestamp with time zone,
    "processado_em" timestamp with time zone,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "conversation_id" "uuid",
    "ai_confidence" double precision,
    "ai_suggested_response" "text",
    "extracted_data" "jsonb",
    "attributed_campaign_id" bigint
);


ALTER TABLE "public"."interacoes" OWNER TO "postgres";


COMMENT ON TABLE "public"."interacoes" IS 'Log de TODAS as interações (médico + recrutador + sistema)';



COMMENT ON COLUMN "public"."interacoes"."classificacao_ia" IS 'JSON com análise completa. Ex: {"intencao": "interesse", "topicos": ["disponibilidade"], "urgencia": "alta"}';



COMMENT ON COLUMN "public"."interacoes"."conversation_id" IS 'Conversa a qual esta interação pertence';



COMMENT ON COLUMN "public"."interacoes"."ai_confidence" IS 'Nível de confiança do agente na resposta (0-1)';



COMMENT ON COLUMN "public"."interacoes"."ai_suggested_response" IS 'Resposta sugerida pela IA (para aprovação humana)';



COMMENT ON COLUMN "public"."interacoes"."extracted_data" IS 'Dados extraídos da mensagem pela IA (nome, CRM, especialidade, etc)';



COMMENT ON COLUMN "public"."interacoes"."attributed_campaign_id" IS 'ID da campanha atribuída a esta resposta (last touch dentro da janela de 7 dias)';



CREATE OR REPLACE VIEW "public"."funil_conversao" AS
 WITH "base" AS (
         SELECT "c"."id",
            "c"."especialidade",
            "c"."estado",
            "c"."status",
            "c"."stage_jornada",
            (EXISTS ( SELECT 1
                   FROM "public"."envios"
                  WHERE ("envios"."cliente_id" = "c"."id"))) AS "foi_contatado",
            (EXISTS ( SELECT 1
                   FROM "public"."interacoes"
                  WHERE (("interacoes"."cliente_id" = "c"."id") AND ("interacoes"."origem" = 'medico_whatsapp'::"text")))) AS "respondeu",
            "c"."app_cadastrado",
            "c"."opt_out"
           FROM "public"."clientes" "c"
          WHERE ("c"."deleted_at" IS NULL)
        )
 SELECT COALESCE("especialidade", 'Não informado'::character varying) AS "especialidade",
    "count"(*) AS "total_base",
    "count"(*) FILTER (WHERE "foi_contatado") AS "contatados",
    "count"(*) FILTER (WHERE "respondeu") AS "responderam",
    "count"(*) FILTER (WHERE "app_cadastrado") AS "cadastrados",
    "count"(*) FILTER (WHERE "opt_out") AS "opt_outs",
    "round"(((100.0 * ("count"(*) FILTER (WHERE "respondeu"))::numeric) / (NULLIF("count"(*) FILTER (WHERE "foi_contatado"), 0))::numeric), 2) AS "taxa_resposta",
    "round"(((100.0 * ("count"(*) FILTER (WHERE "app_cadastrado"))::numeric) / (NULLIF("count"(*) FILTER (WHERE "respondeu"), 0))::numeric), 2) AS "taxa_conversao",
    "round"(((100.0 * ("count"(*) FILTER (WHERE "opt_out"))::numeric) / (NULLIF("count"(*) FILTER (WHERE "foi_contatado"), 0))::numeric), 2) AS "taxa_opt_out"
   FROM "base"
  GROUP BY "especialidade"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "public"."funil_conversao" OWNER TO "postgres";


COMMENT ON VIEW "public"."funil_conversao" IS 'View de gestão - acesso apenas via service_role';



CREATE TABLE IF NOT EXISTS "public"."grupos_whatsapp" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "jid" "text" NOT NULL,
    "nome" "text",
    "descricao" "text",
    "tipo" "text" DEFAULT 'vagas'::"text",
    "regiao" "text",
    "hospital_id" "uuid",
    "ativo" boolean DEFAULT true,
    "monitorar_ofertas" boolean DEFAULT true,
    "total_mensagens" integer DEFAULT 0,
    "total_ofertas_detectadas" integer DEFAULT 0,
    "total_vagas_importadas" integer DEFAULT 0,
    "primeira_mensagem_em" timestamp with time zone,
    "ultima_mensagem_em" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."grupos_whatsapp" OWNER TO "postgres";


COMMENT ON TABLE "public"."grupos_whatsapp" IS 'Cadastro dos grupos de WhatsApp monitorados para captura de vagas';



COMMENT ON COLUMN "public"."grupos_whatsapp"."jid" IS 'JID único do grupo no formato 123456789-987654321@g.us';



COMMENT ON COLUMN "public"."grupos_whatsapp"."tipo" IS 'Tipo do grupo: vagas, geral, regional, hospital';



COMMENT ON COLUMN "public"."grupos_whatsapp"."monitorar_ofertas" IS 'Se deve processar ofertas de plantão deste grupo';



CREATE TABLE IF NOT EXISTS "public"."handoff_used_tokens" (
    "jti" "text" NOT NULL,
    "handoff_id" "uuid" NOT NULL,
    "action" "text" NOT NULL,
    "used_at" timestamp with time zone DEFAULT "now"(),
    "ip_address" "text",
    CONSTRAINT "handoff_used_tokens_action_check" CHECK (("action" = ANY (ARRAY['confirmed'::"text", 'not_confirmed'::"text"])))
);


ALTER TABLE "public"."handoff_used_tokens" OWNER TO "postgres";


COMMENT ON TABLE "public"."handoff_used_tokens" IS 'Tokens JWT usados para confirmacao - previne reuso';



COMMENT ON COLUMN "public"."handoff_used_tokens"."jti" IS 'JWT ID (claim jti) - identificador unico do token';



CREATE TABLE IF NOT EXISTS "public"."handoffs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "conversation_id" "uuid",
    "from_controller" character varying(10),
    "to_controller" character varying(10),
    "from_user_id" "uuid",
    "to_user_id" "uuid",
    "reason" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "conversa_id" "uuid",
    "motivo" "text",
    "trigger_type" character varying(50),
    "status" character varying(50) DEFAULT 'pendente'::character varying,
    "metadata" "jsonb",
    "notas" "text",
    "resolvido_em" timestamp with time zone,
    "resolvido_por" character varying(100),
    CONSTRAINT "handoffs_from_controller_check" CHECK ((("from_controller")::"text" = ANY ((ARRAY['ai'::character varying, 'human'::character varying])::"text"[]))),
    CONSTRAINT "handoffs_to_controller_check" CHECK ((("to_controller")::"text" = ANY ((ARRAY['ai'::character varying, 'human'::character varying])::"text"[])))
);


ALTER TABLE "public"."handoffs" OWNER TO "postgres";


COMMENT ON TABLE "public"."handoffs" IS 'Registro de todas as trocas de controle entre IA e humano';



COMMENT ON COLUMN "public"."handoffs"."from_controller" IS 'Quem estava no controle antes: ai ou human';



COMMENT ON COLUMN "public"."handoffs"."to_controller" IS 'Quem assumiu o controle: ai ou human';



COMMENT ON COLUMN "public"."handoffs"."reason" IS 'Motivo da troca (ex: médico irritado, dúvida complexa, etc)';



COMMENT ON COLUMN "public"."handoffs"."conversa_id" IS 'ID da conversa (tabela conversations)';



COMMENT ON COLUMN "public"."handoffs"."motivo" IS 'Razão do handoff (detectado pelo sistema)';



COMMENT ON COLUMN "public"."handoffs"."trigger_type" IS 'Tipo de trigger: auto, manual, pedido_humano, etc';



COMMENT ON COLUMN "public"."handoffs"."status" IS 'Status: pendente, em_atendimento, resolvido';



COMMENT ON COLUMN "public"."handoffs"."metadata" IS 'Dados extras como última mensagem, total de interações';



CREATE TABLE IF NOT EXISTS "public"."hospitais" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "nome" "text" NOT NULL,
    "logradouro" "text",
    "numero" "text",
    "cidade" "text" NOT NULL,
    "bairro" "text",
    "estado" "text" NOT NULL,
    "pais" "text" DEFAULT 'Brasil'::"text",
    "cep" "text",
    "latitude" numeric,
    "longitude" numeric,
    "endereco_formatado" "text",
    "avatar" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "criado_automaticamente" boolean DEFAULT false,
    "precisa_revisao" boolean DEFAULT false,
    "revisado_em" timestamp with time zone,
    "revisado_por" "text"
);


ALTER TABLE "public"."hospitais" OWNER TO "postgres";


COMMENT ON COLUMN "public"."hospitais"."criado_automaticamente" IS 'Se o hospital foi criado automaticamente pelo sistema';



COMMENT ON COLUMN "public"."hospitais"."precisa_revisao" IS 'Se o hospital precisa de revisão humana';



COMMENT ON COLUMN "public"."hospitais"."revisado_em" IS 'Data/hora da revisão';



COMMENT ON COLUMN "public"."hospitais"."revisado_por" IS 'Quem revisou o hospital';



CREATE TABLE IF NOT EXISTS "public"."hospitais_alias" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "hospital_id" "uuid" NOT NULL,
    "alias" "text" NOT NULL,
    "alias_normalizado" "text" NOT NULL,
    "origem" "text" DEFAULT 'sistema'::"text",
    "criado_por" "text",
    "confianca" double precision DEFAULT 1.0,
    "confirmado" boolean DEFAULT false,
    "vezes_usado" integer DEFAULT 0,
    "ultimo_uso" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."hospitais_alias" OWNER TO "postgres";


COMMENT ON TABLE "public"."hospitais_alias" IS 'Variações de nomes de hospitais para fuzzy match';



COMMENT ON COLUMN "public"."hospitais_alias"."alias" IS 'Nome alternativo do hospital (ex: HSL, São Luiz ABC)';



COMMENT ON COLUMN "public"."hospitais_alias"."alias_normalizado" IS 'Versão normalizada (lowercase, sem acentos) para busca';



COMMENT ON COLUMN "public"."hospitais_alias"."confianca" IS '1.0 = confirmado manualmente, <1.0 = inferido pelo sistema';



CREATE TABLE IF NOT EXISTS "public"."intent_log" (
    "fingerprint" "text" NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "intent_type" "text" NOT NULL,
    "reference_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "expires_at" timestamp with time zone DEFAULT ("now"() + '30 days'::interval)
);


ALTER TABLE "public"."intent_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."intent_log" IS 'Sprint 24 E02: Dedupe semântico por intenção de mensagem';



CREATE SEQUENCE IF NOT EXISTS "public"."interacoes_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."interacoes_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."interacoes_id_seq" OWNED BY "public"."interacoes"."id";



CREATE TABLE IF NOT EXISTS "public"."julia_status" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "status" "text" DEFAULT 'ativo'::"text" NOT NULL,
    "motivo" "text",
    "detalhes" "jsonb",
    "alterado_por" "text",
    "alterado_via" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "julia_status_alterado_via_check" CHECK (("alterado_via" = ANY (ARRAY['slack'::"text", 'sistema'::"text", 'api'::"text", 'manual'::"text"]))),
    CONSTRAINT "julia_status_status_check" CHECK (("status" = ANY (ARRAY['ativo'::"text", 'pausado'::"text", 'manutencao'::"text", 'erro'::"text"])))
);


ALTER TABLE "public"."julia_status" OWNER TO "postgres";


COMMENT ON TABLE "public"."julia_status" IS 'Histórico de status operacional da Júlia';



CREATE OR REPLACE VIEW "public"."julia_status_atual" AS
 SELECT "id",
    "status",
    "motivo",
    "detalhes",
    "alterado_por",
    "alterado_via",
    "created_at"
   FROM "public"."julia_status"
  ORDER BY "created_at" DESC
 LIMIT 1;


ALTER VIEW "public"."julia_status_atual" OWNER TO "postgres";


COMMENT ON VIEW "public"."julia_status_atual" IS 'View de gestão - acesso apenas via service_role';



CREATE OR REPLACE VIEW "public"."medicos_travados" AS
 WITH "ultima_interacao" AS (
         SELECT "interacoes"."cliente_id",
            "max"("interacoes"."created_at") AS "ultima_msg",
            "count"(*) FILTER (WHERE ("interacoes"."origem" = 'medico_whatsapp'::"text")) AS "total_respostas"
           FROM "public"."interacoes"
          GROUP BY "interacoes"."cliente_id"
        ), "ultimos_envios" AS (
         SELECT "envios"."cliente_id",
            "count"(*) AS "total_envios",
            "max"("envios"."enviado_em") AS "ultimo_envio"
           FROM "public"."envios"
          WHERE ("envios"."status" = ANY (ARRAY['enviado'::"text", 'entregue'::"text"]))
          GROUP BY "envios"."cliente_id"
        )
 SELECT "c"."id",
    "c"."primeiro_nome",
    "c"."sobrenome",
    "c"."telefone",
    "c"."especialidade",
    "c"."status",
    "c"."stage_jornada",
    "ue"."total_envios",
    "ue"."ultimo_envio",
    "ui"."total_respostas",
    "ui"."ultima_msg" AS "ultima_interacao",
        CASE
            WHEN ("ui"."total_respostas" = 0) THEN 'nunca_respondeu'::"text"
            WHEN ("ui"."ultima_msg" < ("now"() - '7 days'::interval)) THEN 'parou_de_interagir'::"text"
            ELSE 'ativo'::"text"
        END AS "tipo_travamento",
    "date_part"('day'::"text", ("now"() - COALESCE("ui"."ultima_msg", "ue"."ultimo_envio"))) AS "dias_sem_interacao"
   FROM (("public"."clientes" "c"
     LEFT JOIN "ultimos_envios" "ue" ON (("ue"."cliente_id" = "c"."id")))
     LEFT JOIN "ultima_interacao" "ui" ON (("ui"."cliente_id" = "c"."id")))
  WHERE (("c"."deleted_at" IS NULL) AND ("c"."opt_out" = false) AND (("c"."status")::"text" <> ALL ((ARRAY['cadastrado'::character varying, 'ativo'::character varying, 'perdido'::character varying, 'opt_out'::character varying])::"text"[])) AND ((("ui"."total_respostas" = 0) AND ("ue"."total_envios" > 0)) OR ("ui"."ultima_msg" < ("now"() - '7 days'::interval))))
  ORDER BY ("date_part"('day'::"text", ("now"() - COALESCE("ui"."ultima_msg", "ue"."ultimo_envio")))) DESC;


ALTER VIEW "public"."medicos_travados" OWNER TO "postgres";


COMMENT ON VIEW "public"."medicos_travados" IS 'View de gestão - acesso apenas via service_role';



CREATE TABLE IF NOT EXISTS "public"."mensagens_fora_horario" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "conversa_id" "uuid",
    "mensagem" "text" NOT NULL,
    "recebida_em" timestamp with time zone DEFAULT "now"() NOT NULL,
    "contexto" "jsonb" DEFAULT '{}'::"jsonb",
    "ack_enviado" boolean DEFAULT false,
    "ack_enviado_em" timestamp with time zone,
    "ack_mensagem_id" "text",
    "ack_template_tipo" "text",
    "processada" boolean DEFAULT false,
    "processada_em" timestamp with time zone,
    "processada_resultado" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "inbound_message_id" "text"
);


ALTER TABLE "public"."mensagens_fora_horario" OWNER TO "postgres";


COMMENT ON TABLE "public"."mensagens_fora_horario" IS 'Mensagens recebidas fora do horário comercial para processamento diferido';



COMMENT ON COLUMN "public"."mensagens_fora_horario"."ack_enviado" IS 'Se o ack imediato foi enviado';



COMMENT ON COLUMN "public"."mensagens_fora_horario"."processada" IS 'Se a mensagem foi processada no próximo horário comercial';



COMMENT ON COLUMN "public"."mensagens_fora_horario"."inbound_message_id" IS 'ID da mensagem no WhatsApp para idempotência. Evita duplicatas em webhook retries.';



CREATE TABLE IF NOT EXISTS "public"."mensagens_grupo" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "grupo_id" "uuid" NOT NULL,
    "contato_id" "uuid",
    "message_id" "text" NOT NULL,
    "sender_jid" "text" NOT NULL,
    "sender_nome" "text",
    "texto" "text",
    "tipo_midia" "text" DEFAULT 'texto'::"text",
    "tem_midia" boolean DEFAULT false,
    "timestamp_msg" timestamp with time zone NOT NULL,
    "is_forwarded" boolean DEFAULT false,
    "is_reply" boolean DEFAULT false,
    "reply_to_id" "text",
    "status" "text" DEFAULT 'pendente'::"text",
    "passou_heuristica" boolean,
    "score_heuristica" double precision,
    "keywords_encontradas" "text"[],
    "eh_oferta" boolean,
    "confianca_classificacao" double precision,
    "qtd_vagas_extraidas" integer DEFAULT 0,
    "erro" "text",
    "tentativas" integer DEFAULT 0,
    "processado_em" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."mensagens_grupo" OWNER TO "postgres";


COMMENT ON TABLE "public"."mensagens_grupo" IS 'Todas as mensagens capturadas dos grupos de WhatsApp';



COMMENT ON COLUMN "public"."mensagens_grupo"."status" IS 'Status do pipeline: pendente, ignorada_midia, ignorada_curta, heuristica_passou, heuristica_rejeitou, classificada_oferta, classificada_nao_oferta, extraida, extracao_falhou, erro';



COMMENT ON COLUMN "public"."mensagens_grupo"."score_heuristica" IS 'Score de 0-1 da heurística de classificação';



COMMENT ON COLUMN "public"."mensagens_grupo"."keywords_encontradas" IS 'Array de keywords que matcharam na heurística';



COMMENT ON COLUMN "public"."mensagens_grupo"."confianca_classificacao" IS 'Confiança do LLM na classificação (0-1)';



CREATE TABLE IF NOT EXISTS "public"."metricas_campanhas" (
    "id" bigint NOT NULL,
    "campanha_id" bigint,
    "execucao_campanha_id" bigint,
    "nome_template" "text" NOT NULL,
    "tipo_campanha" "text",
    "total_enviadas" integer DEFAULT 0,
    "total_entregues" integer DEFAULT 0,
    "total_visualizadas" integer DEFAULT 0,
    "total_falhas" integer DEFAULT 0,
    "taxa_entrega_percentual" numeric(5,2) DEFAULT 0.00,
    "taxa_visualizacao_percentual" numeric(5,2) DEFAULT 0.00,
    "respostas_totais" integer DEFAULT 0,
    "respostas_unicas" integer DEFAULT 0,
    "taxa_resposta_percentual" numeric(5,2) DEFAULT 0.00,
    "respostas_positivas" integer DEFAULT 0,
    "respostas_neutras" integer DEFAULT 0,
    "respostas_negativas" integer DEFAULT 0,
    "opt_outs" integer DEFAULT 0,
    "tempo_medio_primeira_resposta_min" numeric(10,2),
    "tempo_mediano_primeira_resposta_min" numeric(10,2),
    "total_deals_criados" integer DEFAULT 0,
    "total_conversoes_cadastro" integer DEFAULT 0,
    "taxa_conversao_percentual" numeric(5,2) DEFAULT 0.00,
    "sentimento_medio" numeric(5,2),
    "sentimento_mediano" numeric(5,2),
    "tom" "text",
    "observacoes" "text",
    "insights_ia" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "calculado_em" timestamp with time zone
);


ALTER TABLE "public"."metricas_campanhas" OWNER TO "postgres";


COMMENT ON TABLE "public"."metricas_campanhas" IS 'KPIs agregados por campanha (atualizados via triggers ou jobs)';



CREATE SEQUENCE IF NOT EXISTS "public"."metricas_campanhas_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."metricas_campanhas_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."metricas_campanhas_id_seq" OWNED BY "public"."metricas_campanhas"."id";



CREATE TABLE IF NOT EXISTS "public"."metricas_conversa" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "conversa_id" "uuid",
    "total_mensagens_medico" integer DEFAULT 0,
    "total_mensagens_julia" integer DEFAULT 0,
    "tempo_primeira_resposta_segundos" numeric,
    "tempo_medio_resposta_segundos" numeric,
    "duracao_conversa_minutos" numeric,
    "mensagens_por_hora" numeric,
    "resultado" character varying(50),
    "primeira_mensagem_em" timestamp with time zone,
    "ultima_mensagem_em" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."metricas_conversa" OWNER TO "postgres";


COMMENT ON TABLE "public"."metricas_conversa" IS 'Métricas agregadas por conversa para dashboard';



CREATE TABLE IF NOT EXISTS "public"."metricas_deteccao_bot" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "cliente_id" "uuid",
    "conversa_id" "uuid",
    "mensagem" "text",
    "padrao_detectado" "text",
    "trecho" "text",
    "revisado_por" "text",
    "falso_positivo" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."metricas_deteccao_bot" OWNER TO "postgres";


COMMENT ON TABLE "public"."metricas_deteccao_bot" IS 'Registra quando medicos percebem que estao falando com uma IA';



COMMENT ON COLUMN "public"."metricas_deteccao_bot"."padrao_detectado" IS 'Padrao regex que matchou';



COMMENT ON COLUMN "public"."metricas_deteccao_bot"."trecho" IS 'Parte da mensagem que indicou deteccao';



COMMENT ON COLUMN "public"."metricas_deteccao_bot"."falso_positivo" IS 'Marcado pelo gestor ao revisar';



CREATE TABLE IF NOT EXISTS "public"."metricas_grupos_diarias" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "data" "date" NOT NULL,
    "grupo_id" "uuid",
    "mensagens_total" integer DEFAULT 0,
    "mensagens_processadas" integer DEFAULT 0,
    "mensagens_descartadas" integer DEFAULT 0,
    "vagas_extraidas" integer DEFAULT 0,
    "vagas_importadas" integer DEFAULT 0,
    "vagas_revisao" integer DEFAULT 0,
    "vagas_descartadas" integer DEFAULT 0,
    "vagas_duplicadas" integer DEFAULT 0,
    "tempo_medio_processamento_ms" integer,
    "tempo_medio_llm_ms" integer,
    "tokens_input" integer DEFAULT 0,
    "tokens_output" integer DEFAULT 0,
    "custo_estimado_usd" numeric(10,4) DEFAULT 0,
    "confianca_media_extracao" numeric(3,2),
    "confianca_media_match" numeric(3,2),
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."metricas_grupos_diarias" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."metricas_pipeline_diarias" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "data" "date" NOT NULL,
    "grupos_ativos" integer DEFAULT 0,
    "mensagens_total" integer DEFAULT 0,
    "mensagens_processadas" integer DEFAULT 0,
    "heuristica_passou" integer DEFAULT 0,
    "llm_classificou" integer DEFAULT 0,
    "extracao_sucesso" integer DEFAULT 0,
    "normalizacao_sucesso" integer DEFAULT 0,
    "vagas_importadas" integer DEFAULT 0,
    "vagas_revisao" integer DEFAULT 0,
    "vagas_duplicadas" integer DEFAULT 0,
    "p50_tempo_ms" integer,
    "p95_tempo_ms" integer,
    "p99_tempo_ms" integer,
    "custo_total_usd" numeric(10,4),
    "erros_total" integer DEFAULT 0,
    "erros_por_estagio" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."metricas_pipeline_diarias" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."notificacoes_gestor" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tipo" "text" NOT NULL,
    "titulo" "text" NOT NULL,
    "mensagem" "text" NOT NULL,
    "dados" "jsonb",
    "canal" "text" NOT NULL,
    "destino" "text" NOT NULL,
    "enviada" boolean DEFAULT false,
    "enviada_em" timestamp with time zone,
    "erro" "text",
    "tentativas" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."notificacoes_gestor" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."outbound_dedupe" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "dedupe_key" "text" NOT NULL,
    "cliente_id" "uuid",
    "conversation_id" "uuid",
    "method" "text" NOT NULL,
    "status" "text" DEFAULT 'queued'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "sent_at" timestamp with time zone,
    "error" "text",
    CONSTRAINT "valid_status" CHECK (("status" = ANY (ARRAY['queued'::"text", 'sent'::"text", 'failed'::"text", 'deduped'::"text"])))
);


ALTER TABLE "public"."outbound_dedupe" OWNER TO "postgres";


COMMENT ON TABLE "public"."outbound_dedupe" IS 'Deduplicação de mensagens outbound para evitar duplicatas em timeout/retry';



COMMENT ON COLUMN "public"."outbound_dedupe"."dedupe_key" IS 'Hash único: sha256(cliente_id + method + content_hash + window_bucket)';



COMMENT ON COLUMN "public"."outbound_dedupe"."status" IS 'queued=pronto para enviar, sent=enviado, failed=falhou, deduped=duplicata ignorada';



CREATE TABLE IF NOT EXISTS "public"."periodos" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "nome" character varying,
    "index" smallint,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."periodos" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."policy_events" (
    "event_id" "uuid" NOT NULL,
    "policy_decision_id" "uuid" NOT NULL,
    "event_type" "text" NOT NULL,
    "ts" timestamp with time zone DEFAULT "now"() NOT NULL,
    "policy_version" "text" NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "conversation_id" "uuid",
    "interaction_id" bigint,
    "rule_matched" "text",
    "primary_action" "text",
    "tone" "text",
    "requires_human" boolean,
    "forbid_all" boolean,
    "allowed_actions" "text"[],
    "forbidden_actions" "text"[],
    "doctor_state_input" "jsonb",
    "snapshot_hash" "text",
    "reasoning" "text",
    "effect_type" "text",
    "effect_details" "jsonb",
    "is_first_message" boolean,
    "conversa_status" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "decision_effect_exclusive" CHECK (((("event_type" = 'decision'::"text") AND ("effect_type" IS NULL)) OR (("event_type" = 'effect'::"text") AND ("rule_matched" IS NULL) AND ("primary_action" IS NULL)))),
    CONSTRAINT "valid_event_type" CHECK (("event_type" = ANY (ARRAY['decision'::"text", 'effect'::"text"])))
);


ALTER TABLE "public"."policy_events" OWNER TO "postgres";


COMMENT ON TABLE "public"."policy_events" IS 'Eventos do Policy Engine para observabilidade e replay';



COMMENT ON COLUMN "public"."policy_events"."event_id" IS 'ID único do evento (span_id)';



COMMENT ON COLUMN "public"."policy_events"."policy_decision_id" IS 'ID da decisão (trace_id/correlation_id)';



COMMENT ON COLUMN "public"."policy_events"."snapshot_hash" IS 'Hash SHA256 truncado do doctor_state_input para verificação de integridade';



CREATE TABLE IF NOT EXISTS "public"."prompts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "nome" character varying(100) NOT NULL,
    "versao" character varying(20) NOT NULL,
    "tipo" character varying(50) NOT NULL,
    "conteudo" "text" NOT NULL,
    "descricao" "text",
    "ativo" boolean DEFAULT false,
    "especialidade_id" "uuid",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "created_by" character varying(100)
);


ALTER TABLE "public"."prompts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."prompts_historico" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "prompt_id" "uuid",
    "acao" character varying(50),
    "versao_anterior" character varying(20),
    "versao_nova" character varying(20),
    "created_at" timestamp with time zone DEFAULT "now"(),
    "created_by" character varying(100)
);


ALTER TABLE "public"."prompts_historico" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."report_schedule" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tipo" "text" NOT NULL,
    "horario" time without time zone NOT NULL,
    "dias_semana" integer[] DEFAULT '{1,2,3,4,5}'::integer[],
    "timezone" "text" DEFAULT 'America/Sao_Paulo'::"text",
    "ativo" boolean DEFAULT true,
    "ultimo_envio" timestamp with time zone,
    "proximo_envio" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "report_schedule_tipo_check" CHECK (("tipo" = ANY (ARRAY['manha'::"text", 'almoco'::"text", 'tarde'::"text", 'fim_dia'::"text", 'semanal'::"text"])))
);


ALTER TABLE "public"."report_schedule" OWNER TO "postgres";


COMMENT ON TABLE "public"."report_schedule" IS 'Agendamento de reports automáticos';



CREATE TABLE IF NOT EXISTS "public"."reports" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tipo" "text" NOT NULL,
    "periodo_inicio" timestamp with time zone NOT NULL,
    "periodo_fim" timestamp with time zone NOT NULL,
    "metricas" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "analise" "text",
    "destaques" "text"[],
    "preocupacoes" "text"[],
    "sugestoes" "text"[],
    "enviado_slack" boolean DEFAULT false,
    "enviado_em" timestamp with time zone,
    "slack_message_ts" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "reports_tipo_check" CHECK (("tipo" = ANY (ARRAY['manha'::"text", 'almoco'::"text", 'tarde'::"text", 'fim_dia'::"text", 'semanal'::"text", 'adhoc'::"text"])))
);


ALTER TABLE "public"."reports" OWNER TO "postgres";


COMMENT ON TABLE "public"."reports" IS 'Reports periódicos gerados pela Júlia';



CREATE TABLE IF NOT EXISTS "public"."setores" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "nome" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."setores" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."slack_comandos" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "comando" "text" NOT NULL,
    "argumentos" "text"[],
    "texto_original" "text" NOT NULL,
    "user_id" "text" NOT NULL,
    "user_name" "text",
    "channel_id" "text" NOT NULL,
    "channel_name" "text",
    "message_ts" "text",
    "resposta" "text",
    "respondido" boolean DEFAULT false,
    "respondido_em" timestamp with time zone,
    "erro" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."slack_comandos" OWNER TO "postgres";


COMMENT ON TABLE "public"."slack_comandos" IS 'Log de comandos recebidos via Slack';



CREATE TABLE IF NOT EXISTS "public"."slack_sessoes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "channel_id" "text" NOT NULL,
    "mensagens" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "contexto" "jsonb" DEFAULT '{}'::"jsonb",
    "acao_pendente" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "expires_at" timestamp with time zone DEFAULT ("now"() + '00:30:00'::interval)
);


ALTER TABLE "public"."slack_sessoes" OWNER TO "postgres";


COMMENT ON TABLE "public"."slack_sessoes" IS 'Contexto de conversas do gestor com a Julia no Slack';



COMMENT ON COLUMN "public"."slack_sessoes"."mensagens" IS 'Array de {role: user|assistant, content: string, timestamp: ISO}';



COMMENT ON COLUMN "public"."slack_sessoes"."contexto" IS 'Dados extraidos: {medicos: [], vagas: [], ultimo_resultado: any}';



COMMENT ON COLUMN "public"."slack_sessoes"."acao_pendente" IS 'Acao aguardando confirmacao: {tipo, params, preview}';



CREATE TABLE IF NOT EXISTS "public"."sugestoes_prompt" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "conversa_id" "uuid",
    "avaliacao_id" "uuid",
    "tipo" character varying(50) NOT NULL,
    "descricao" "text" NOT NULL,
    "exemplo_ruim" "text",
    "exemplo_bom" "text",
    "status" character varying(20) DEFAULT 'pendente'::character varying,
    "implementada_em" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "sugestoes_prompt_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['pendente'::character varying, 'implementada'::character varying, 'rejeitada'::character varying])::"text"[]))),
    CONSTRAINT "sugestoes_prompt_tipo_check" CHECK ((("tipo")::"text" = ANY ((ARRAY['adicionar_regra'::character varying, 'remover_regra'::character varying, 'ajustar_tom'::character varying, 'exemplo'::character varying])::"text"[])))
);


ALTER TABLE "public"."sugestoes_prompt" OWNER TO "postgres";


COMMENT ON TABLE "public"."sugestoes_prompt" IS 'Sugestões de melhoria do prompt coletadas do feedback do gestor';



CREATE OR REPLACE VIEW "public"."timeline_medico" AS
 SELECT "c"."id" AS "cliente_id",
    "c"."primeiro_nome",
    "c"."sobrenome",
    "c"."telefone",
    "c"."especialidade",
    COALESCE("e"."enviado_em", "i"."created_at") AS "timestamp",
        CASE
            WHEN ("e"."id" IS NOT NULL) THEN 'envio'::"text"
            ELSE "i"."origem"
        END AS "tipo_evento",
        CASE
            WHEN ("e"."id" IS NOT NULL) THEN '📤'::"text"
            WHEN ("i"."origem" = 'medico_whatsapp'::"text") THEN '📱'::"text"
            WHEN ("i"."origem" = 'recrutador_bitrix'::"text") THEN '👤'::"text"
            ELSE '🤖'::"text"
        END AS "icone",
    COALESCE("e"."conteudo_enviado", "i"."conteudo") AS "mensagem",
    "i"."sentimento_score",
    "e"."status" AS "status_envio",
    "i"."tipo" AS "tipo_interacao",
    "e"."id" AS "envio_id",
    "i"."id" AS "interacao_id",
    "e"."campanha_id",
    "i"."deal_bitrix_id"
   FROM (("public"."clientes" "c"
     LEFT JOIN "public"."envios" "e" ON (("e"."cliente_id" = "c"."id")))
     LEFT JOIN "public"."interacoes" "i" ON (("i"."cliente_id" = "c"."id")))
  WHERE ("c"."deleted_at" IS NULL)
  ORDER BY "c"."id", COALESCE("e"."enviado_em", "i"."created_at") DESC;


ALTER VIEW "public"."timeline_medico" OWNER TO "postgres";


COMMENT ON VIEW "public"."timeline_medico" IS 'View de gestão - acesso apenas via service_role';



CREATE TABLE IF NOT EXISTS "public"."tipos_vaga" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "nome" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."tipos_vaga" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."touch_reconciliation_log" (
    "provider_message_id" "text" NOT NULL,
    "mensagem_id" "uuid" NOT NULL,
    "cliente_id" "uuid" NOT NULL,
    "campaign_id" bigint NOT NULL,
    "touch_at" timestamp with time zone NOT NULL,
    "processed_at" timestamp with time zone DEFAULT "now"(),
    "status" "text" NOT NULL,
    "error" "text",
    "previous_touch_at" timestamp with time zone,
    "previous_campaign_id" bigint,
    CONSTRAINT "touch_reconciliation_log_status_check" CHECK (("status" = ANY (ARRAY['processing'::"text", 'ok'::"text", 'skipped_already_newer'::"text", 'skipped_no_change'::"text", 'failed'::"text", 'abandoned'::"text"])))
);


ALTER TABLE "public"."touch_reconciliation_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."touch_reconciliation_log" IS 'Sprint 24 P1: Log de reconciliação de touches.
Tabela INTERNA - acesso apenas via service_role.
PK em provider_message_id garante idempotência.
Status "processing" usado para claim atômico.';



CREATE OR REPLACE VIEW "public"."v_conversations_list" AS
 SELECT "c"."id",
    "c"."status",
    "c"."controlled_by",
    "c"."controlled_by_user_id",
    "c"."escalation_reason",
    "c"."message_count",
    "c"."last_message_at",
    "c"."started_at",
    "c"."instance_id",
    "cl"."id" AS "cliente_id",
    "cl"."primeiro_nome",
    "cl"."sobrenome",
    (((COALESCE("cl"."primeiro_nome", ''::character varying))::"text" || ' '::"text") || (COALESCE("cl"."sobrenome", ''::character varying))::"text") AS "cliente_nome_completo",
    "cl"."telefone" AS "cliente_telefone",
    "cl"."especialidade" AS "cliente_especialidade",
    "cl"."cidade" AS "cliente_cidade",
    "cl"."estado" AS "cliente_estado",
    "cl"."stage_jornada" AS "cliente_stage",
    "cl"."qualification_score" AS "cliente_qualification_score",
    "camp"."id" AS "campanha_id",
    "camp"."nome_template" AS "campanha_nome",
    "camp"."tipo_campanha",
    ( SELECT "i"."conteudo"
           FROM "public"."interacoes" "i"
          WHERE ("i"."conversation_id" = "c"."id")
          ORDER BY "i"."created_at" DESC
         LIMIT 1) AS "ultima_mensagem",
    ( SELECT "i"."autor_tipo"
           FROM "public"."interacoes" "i"
          WHERE ("i"."conversation_id" = "c"."id")
          ORDER BY "i"."created_at" DESC
         LIMIT 1) AS "ultima_mensagem_autor"
   FROM (("public"."conversations" "c"
     JOIN "public"."clientes" "cl" ON (("c"."cliente_id" = "cl"."id")))
     LEFT JOIN "public"."campanhas" "camp" ON (("c"."campanha_id" = "camp"."id")));


ALTER VIEW "public"."v_conversations_list" OWNER TO "postgres";


COMMENT ON VIEW "public"."v_conversations_list" IS 'View de gestão - acesso apenas via service_role';



CREATE TABLE IF NOT EXISTS "public"."vagas" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "hospital_id" "uuid" NOT NULL,
    "especialidade_id" "uuid" NOT NULL,
    "setor_id" "uuid",
    "periodo_id" "uuid",
    "tipos_vaga_id" "uuid",
    "forma_recebimento_id" "uuid",
    "data" "date",
    "hora_inicio" time without time zone,
    "hora_fim" time without time zone,
    "valor" integer,
    "data_pagamento" "date",
    "status" character varying DEFAULT ''::character varying,
    "total_candidaturas" integer DEFAULT 0,
    "cliente_id" "uuid",
    "fechada_em" timestamp with time zone,
    "fechada_por" "text",
    "grupo_id" "uuid",
    "grade_id" "uuid",
    "recorrencia_id" "uuid",
    "index" smallint,
    "escalista_id" "uuid",
    "observacoes" character varying,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "updated_by" "uuid",
    "deleted_at" timestamp with time zone,
    "origem" character varying(50) DEFAULT 'manual'::character varying,
    "vaga_grupo_id" "uuid",
    "realizada_em" timestamp with time zone,
    "realizada_por" "text",
    "cancelada_em" timestamp with time zone,
    "cancelada_por" "text",
    "pendente_confirmacao_em" timestamp with time zone,
    "valor_minimo" integer,
    "valor_maximo" integer,
    "valor_tipo" "text" DEFAULT 'fixo'::"text",
    "source" "text",
    "source_id" "uuid",
    CONSTRAINT "chk_vagas_valor_tipo" CHECK (("valor_tipo" = ANY (ARRAY['fixo'::"text", 'a_combinar'::"text", 'faixa'::"text"]))),
    CONSTRAINT "vagas_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['aberta'::character varying, 'anunciada'::character varying, 'reservada'::character varying, 'pendente_confirmacao'::character varying, 'aguardando_confirmacao'::character varying, 'confirmada'::character varying, 'fechada'::character varying, 'realizada'::character varying, 'cancelada'::character varying])::"text"[])))
);


ALTER TABLE "public"."vagas" OWNER TO "postgres";


COMMENT ON COLUMN "public"."vagas"."status" IS 'Status da vaga: aberta, anunciada, reservada, realizada, cancelada. LEGADO: fechada (não usar para novas vagas, excluir do funil)';



COMMENT ON COLUMN "public"."vagas"."origem" IS 'Origem da vaga: manual, grupo_whatsapp, api';



COMMENT ON COLUMN "public"."vagas"."vaga_grupo_id" IS 'Referência à vaga de grupo de origem (se aplicável)';



COMMENT ON COLUMN "public"."vagas"."realizada_em" IS 'Timestamp de quando o plantão foi marcado como realizado';



COMMENT ON COLUMN "public"."vagas"."realizada_por" IS 'Quem marcou como realizado (user_id ou "ops")';



COMMENT ON COLUMN "public"."vagas"."cancelada_em" IS 'Timestamp de quando a vaga foi cancelada';



COMMENT ON COLUMN "public"."vagas"."cancelada_por" IS 'Quem cancelou a vaga (julia, gestor, medico, sistema)';



COMMENT ON COLUMN "public"."vagas"."pendente_confirmacao_em" IS 'Timestamp de quando a vaga entrou em pendente_confirmacao';



COMMENT ON COLUMN "public"."vagas"."valor_minimo" IS 'Valor minimo da faixa (quando valor_tipo = faixa)';



COMMENT ON COLUMN "public"."vagas"."valor_maximo" IS 'Valor maximo da faixa (quando valor_tipo = faixa)';



COMMENT ON COLUMN "public"."vagas"."valor_tipo" IS 'Tipo de valor: fixo, a_combinar, faixa';



COMMENT ON COLUMN "public"."vagas"."source" IS 'Origem da vaga: grupo, manual, api';



COMMENT ON COLUMN "public"."vagas"."source_id" IS 'ID da origem (ex: vagas_grupo.id)';



CREATE OR REPLACE VIEW "public"."vagas_disponiveis" AS
 SELECT "v"."id",
    "v"."data",
    "v"."hora_inicio",
    "v"."hora_fim",
    (EXTRACT(epoch FROM ("v"."hora_fim" - "v"."hora_inicio")) / (3600)::numeric) AS "duracao_horas",
    "v"."valor",
    (("v"."valor")::numeric / NULLIF((EXTRACT(epoch FROM ("v"."hora_fim" - "v"."hora_inicio")) / (3600)::numeric), (0)::numeric)) AS "valor_hora",
    "v"."data_pagamento",
    "v"."status",
    "v"."observacoes",
    "h"."id" AS "hospital_id",
    "h"."nome" AS "hospital_nome",
    "h"."cidade" AS "hospital_cidade",
    "h"."bairro" AS "hospital_bairro",
    "h"."estado" AS "hospital_estado",
    "h"."endereco_formatado" AS "hospital_endereco",
    "e"."id" AS "especialidade_id",
    "e"."nome" AS "especialidade_nome",
    "s"."nome" AS "setor_nome",
    "p"."nome" AS "periodo_nome",
    "t"."nome" AS "tipo_vaga_nome",
    "f"."forma_recebimento"
   FROM (((((("public"."vagas" "v"
     LEFT JOIN "public"."hospitais" "h" ON (("v"."hospital_id" = "h"."id")))
     LEFT JOIN "public"."especialidades" "e" ON (("v"."especialidade_id" = "e"."id")))
     LEFT JOIN "public"."setores" "s" ON (("v"."setor_id" = "s"."id")))
     LEFT JOIN "public"."periodos" "p" ON (("v"."periodo_id" = "p"."id")))
     LEFT JOIN "public"."tipos_vaga" "t" ON (("v"."tipos_vaga_id" = "t"."id")))
     LEFT JOIN "public"."formas_recebimento" "f" ON (("v"."forma_recebimento_id" = "f"."id")))
  WHERE ((("v"."status")::"text" = 'aberta'::"text") AND ("v"."deleted_at" IS NULL) AND ("v"."data" >= CURRENT_DATE));


ALTER VIEW "public"."vagas_disponiveis" OWNER TO "postgres";


COMMENT ON VIEW "public"."vagas_disponiveis" IS 'View operacional - acesso apenas via service_role';



CREATE TABLE IF NOT EXISTS "public"."vagas_grupo" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "mensagem_id" "uuid" NOT NULL,
    "grupo_origem_id" "uuid" NOT NULL,
    "contato_responsavel_id" "uuid",
    "hospital_raw" "text",
    "especialidade_raw" "text",
    "setor_raw" "text",
    "periodo_raw" "text",
    "tipo_vaga_raw" "text",
    "forma_pagamento_raw" "text",
    "data" "date",
    "hora_inicio" time without time zone,
    "hora_fim" time without time zone,
    "valor" integer,
    "observacoes_raw" "text",
    "hospital_id" "uuid",
    "especialidade_id" "uuid",
    "setor_id" "uuid",
    "periodo_id" "uuid",
    "tipos_vaga_id" "uuid",
    "forma_recebimento_id" "uuid",
    "hospital_criado" boolean DEFAULT false,
    "hospital_match_score" double precision,
    "especialidade_match_score" double precision,
    "confianca_geral" double precision,
    "confianca_hospital" double precision,
    "confianca_especialidade" double precision,
    "confianca_data" double precision,
    "confianca_horario" double precision,
    "confianca_valor" double precision,
    "campos_faltando" "text"[],
    "data_valida" boolean DEFAULT true,
    "dados_minimos_ok" boolean DEFAULT false,
    "hash_dedup" "text",
    "eh_duplicada" boolean DEFAULT false,
    "duplicada_de" "uuid",
    "qtd_fontes" integer DEFAULT 1,
    "status" "text" DEFAULT 'nova'::"text",
    "motivo_status" "text",
    "vaga_importada_id" "uuid",
    "importada_em" timestamp with time zone,
    "revisada_por" "text",
    "revisada_em" timestamp with time zone,
    "notas_revisao" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "valor_minimo" integer,
    "valor_maximo" integer,
    "valor_tipo" "text" DEFAULT 'fixo'::"text",
    CONSTRAINT "chk_valor_tipo" CHECK (("valor_tipo" = ANY (ARRAY['fixo'::"text", 'a_combinar'::"text", 'faixa'::"text"])))
);


ALTER TABLE "public"."vagas_grupo" OWNER TO "postgres";


COMMENT ON TABLE "public"."vagas_grupo" IS 'Staging de vagas extraídas dos grupos antes de importação para tabela vagas';



COMMENT ON COLUMN "public"."vagas_grupo"."confianca_geral" IS 'Score ponderado de confiança (0-1)';



COMMENT ON COLUMN "public"."vagas_grupo"."hash_dedup" IS 'Hash para deduplicação: MD5(hospital_id|data|periodo_id|especialidade_id)';



COMMENT ON COLUMN "public"."vagas_grupo"."status" IS 'Status: nova, normalizando, normalizada, duplicada, aguardando_revisao, aprovada, importada, rejeitada, descartada, erro';



COMMENT ON COLUMN "public"."vagas_grupo"."valor_minimo" IS 'Valor minimo da faixa (quando valor_tipo = faixa)';



COMMENT ON COLUMN "public"."vagas_grupo"."valor_maximo" IS 'Valor maximo da faixa (quando valor_tipo = faixa)';



COMMENT ON COLUMN "public"."vagas_grupo"."valor_tipo" IS 'Tipo de valor: fixo, a_combinar, faixa';



CREATE TABLE IF NOT EXISTS "public"."vagas_grupo_fontes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "vaga_grupo_id" "uuid" NOT NULL,
    "mensagem_id" "uuid" NOT NULL,
    "grupo_id" "uuid" NOT NULL,
    "contato_id" "uuid",
    "ordem" integer DEFAULT 1,
    "texto_original" "text",
    "valor_informado" integer,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."vagas_grupo_fontes" OWNER TO "postgres";


COMMENT ON TABLE "public"."vagas_grupo_fontes" IS 'Rastreia múltiplas fontes de uma mesma vaga (deduplicação)';



COMMENT ON COLUMN "public"."vagas_grupo_fontes"."ordem" IS '1 = primeira fonte descoberta, 2 = segunda, etc';



COMMENT ON COLUMN "public"."vagas_grupo_fontes"."valor_informado" IS 'Valor informado nesta fonte específica (pode variar entre fontes)';



CREATE TABLE IF NOT EXISTS "public"."whatsapp_instances" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "instance_id" character varying(100) NOT NULL,
    "instance_name" character varying(100) NOT NULL,
    "phone" character varying(20),
    "status" character varying(20) DEFAULT 'disconnected'::character varying,
    "last_health_check" timestamp with time zone,
    "messages_sent_today" integer DEFAULT 0,
    "messages_sent_hour" integer DEFAULT 0,
    "daily_limit" integer DEFAULT 500,
    "hourly_limit" integer DEFAULT 50,
    "is_active" boolean DEFAULT true,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "whatsapp_instances_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['connected'::character varying, 'disconnected'::character varying, 'connecting'::character varying, 'banned'::character varying])::"text"[])))
);


ALTER TABLE "public"."whatsapp_instances" OWNER TO "postgres";


COMMENT ON TABLE "public"."whatsapp_instances" IS 'Pool de instâncias WhatsApp gerenciadas via Evolution API';



COMMENT ON COLUMN "public"."whatsapp_instances"."instance_id" IS 'ID único da instância na Evolution API';



COMMENT ON COLUMN "public"."whatsapp_instances"."status" IS 'Estado da conexão: connected, disconnected, connecting, banned';



COMMENT ON COLUMN "public"."whatsapp_instances"."messages_sent_today" IS 'Contador de mensagens enviadas hoje (reset à meia-noite)';



COMMENT ON COLUMN "public"."whatsapp_instances"."messages_sent_hour" IS 'Contador de mensagens na última hora (rolling window)';



COMMENT ON COLUMN "public"."whatsapp_instances"."daily_limit" IS 'Limite máximo de mensagens por dia para esta instância';



COMMENT ON COLUMN "public"."whatsapp_instances"."hourly_limit" IS 'Limite máximo de mensagens por hora para esta instância';



ALTER TABLE ONLY "public"."campanhas" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."campanhas_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."clientes_log" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."clientes_log_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."envios" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."envios_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."execucoes_campanhas" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."execucoes_campanhas_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."interacoes" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."interacoes_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."metricas_campanhas" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."metricas_campanhas_id_seq"'::"regclass");



ALTER TABLE ONLY "app_config"."secrets"
    ADD CONSTRAINT "secrets_name_key" UNIQUE ("name");



ALTER TABLE ONLY "app_config"."secrets"
    ADD CONSTRAINT "secrets_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."app_settings"
    ADD CONSTRAINT "app_settings_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "public"."avaliacoes_qualidade"
    ADD CONSTRAINT "avaliacoes_qualidade_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."briefing_config"
    ADD CONSTRAINT "briefing_config_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."briefing_historico"
    ADD CONSTRAINT "briefing_historico_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."briefing_sync_log"
    ADD CONSTRAINT "briefing_sync_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."briefings_pendentes"
    ADD CONSTRAINT "briefings_pendentes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."business_alerts"
    ADD CONSTRAINT "business_alerts_pkey" PRIMARY KEY ("alert_id");



ALTER TABLE ONLY "public"."business_events"
    ADD CONSTRAINT "business_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."campaign_contact_history"
    ADD CONSTRAINT "campaign_contact_history_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."campanhas"
    ADD CONSTRAINT "campanhas_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."clientes_log"
    ADD CONSTRAINT "clientes_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."clientes"
    ADD CONSTRAINT "clientes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conhecimento_julia"
    ADD CONSTRAINT "conhecimento_julia_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."contatos_grupo"
    ADD CONSTRAINT "contatos_grupo_jid_key" UNIQUE ("jid");



ALTER TABLE ONLY "public"."contatos_grupo"
    ADD CONSTRAINT "contatos_grupo_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."data_anomalies"
    ADD CONSTRAINT "data_anomalies_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."diretrizes"
    ADD CONSTRAINT "diretrizes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."doctor_context"
    ADD CONSTRAINT "doctor_context_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."doctor_state"
    ADD CONSTRAINT "doctor_state_pkey" PRIMARY KEY ("cliente_id");



ALTER TABLE ONLY "public"."envios"
    ADD CONSTRAINT "envios_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."especialidades_alias"
    ADD CONSTRAINT "especialidades_alias_especialidade_id_alias_normalizado_key" UNIQUE ("especialidade_id", "alias_normalizado");



ALTER TABLE ONLY "public"."especialidades_alias"
    ADD CONSTRAINT "especialidades_alias_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."especialidades"
    ADD CONSTRAINT "especialidades_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."execucoes_campanhas"
    ADD CONSTRAINT "execucoes_campanhas_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."external_contacts"
    ADD CONSTRAINT "external_contacts_pkey" PRIMARY KEY ("telefone");



ALTER TABLE ONLY "public"."external_handoffs"
    ADD CONSTRAINT "external_handoffs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."external_handoffs"
    ADD CONSTRAINT "external_handoffs_vaga_id_cliente_id_key" UNIQUE ("vaga_id", "cliente_id");



ALTER TABLE ONLY "public"."feature_flags"
    ADD CONSTRAINT "feature_flags_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "public"."feedbacks_gestor"
    ADD CONSTRAINT "feedbacks_gestor_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."fila_mensagens"
    ADD CONSTRAINT "fila_mensagens_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."fila_processamento_grupos"
    ADD CONSTRAINT "fila_processamento_grupos_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."formas_recebimento"
    ADD CONSTRAINT "formas_recebimento_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."grupos_whatsapp"
    ADD CONSTRAINT "grupos_whatsapp_jid_key" UNIQUE ("jid");



ALTER TABLE ONLY "public"."grupos_whatsapp"
    ADD CONSTRAINT "grupos_whatsapp_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."handoff_used_tokens"
    ADD CONSTRAINT "handoff_used_tokens_pkey" PRIMARY KEY ("jti");



ALTER TABLE ONLY "public"."handoffs"
    ADD CONSTRAINT "handoffs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."hospitais_alias"
    ADD CONSTRAINT "hospitais_alias_hospital_id_alias_normalizado_key" UNIQUE ("hospital_id", "alias_normalizado");



ALTER TABLE ONLY "public"."hospitais_alias"
    ADD CONSTRAINT "hospitais_alias_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."hospitais"
    ADD CONSTRAINT "hospitais_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."campaign_contact_history"
    ADD CONSTRAINT "idx_campaign_contact_unique" UNIQUE ("cliente_id", "campaign_id");



ALTER TABLE ONLY "public"."intent_log"
    ADD CONSTRAINT "intent_log_pkey" PRIMARY KEY ("fingerprint");



ALTER TABLE ONLY "public"."interacoes"
    ADD CONSTRAINT "interacoes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."julia_status"
    ADD CONSTRAINT "julia_status_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."mensagens_fora_horario"
    ADD CONSTRAINT "mensagens_fora_horario_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."mensagens_grupo"
    ADD CONSTRAINT "mensagens_grupo_message_id_key" UNIQUE ("message_id");



ALTER TABLE ONLY "public"."mensagens_grupo"
    ADD CONSTRAINT "mensagens_grupo_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."metricas_campanhas"
    ADD CONSTRAINT "metricas_campanhas_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."metricas_conversa"
    ADD CONSTRAINT "metricas_conversa_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."metricas_deteccao_bot"
    ADD CONSTRAINT "metricas_deteccao_bot_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."metricas_grupos_diarias"
    ADD CONSTRAINT "metricas_grupos_diarias_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."metricas_pipeline_diarias"
    ADD CONSTRAINT "metricas_pipeline_diarias_data_key" UNIQUE ("data");



ALTER TABLE ONLY "public"."metricas_pipeline_diarias"
    ADD CONSTRAINT "metricas_pipeline_diarias_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."notificacoes_gestor"
    ADD CONSTRAINT "notificacoes_gestor_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."outbound_dedupe"
    ADD CONSTRAINT "outbound_dedupe_dedupe_key_key" UNIQUE ("dedupe_key");



ALTER TABLE ONLY "public"."outbound_dedupe"
    ADD CONSTRAINT "outbound_dedupe_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."periodos"
    ADD CONSTRAINT "periodos_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."policy_events"
    ADD CONSTRAINT "policy_events_pkey" PRIMARY KEY ("event_id");



ALTER TABLE ONLY "public"."prompts_historico"
    ADD CONSTRAINT "prompts_historico_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."prompts"
    ADD CONSTRAINT "prompts_nome_versao_key" UNIQUE ("nome", "versao");



ALTER TABLE ONLY "public"."prompts"
    ADD CONSTRAINT "prompts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_schedule"
    ADD CONSTRAINT "report_schedule_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."reports"
    ADD CONSTRAINT "reports_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."setores"
    ADD CONSTRAINT "setores_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."slack_comandos"
    ADD CONSTRAINT "slack_comandos_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."slack_sessoes"
    ADD CONSTRAINT "slack_sessoes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."sugestoes_prompt"
    ADD CONSTRAINT "sugestoes_prompt_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."tipos_vaga"
    ADD CONSTRAINT "tipos_vaga_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."touch_reconciliation_log"
    ADD CONSTRAINT "touch_reconciliation_log_pkey" PRIMARY KEY ("provider_message_id");



ALTER TABLE ONLY "public"."clientes"
    ADD CONSTRAINT "unique_telefone" UNIQUE ("telefone");



ALTER TABLE ONLY "public"."slack_sessoes"
    ADD CONSTRAINT "unique_user_channel" UNIQUE ("user_id", "channel_id");



ALTER TABLE ONLY "public"."fila_processamento_grupos"
    ADD CONSTRAINT "uq_fila_mensagem" UNIQUE ("mensagem_id");



ALTER TABLE ONLY "public"."metricas_grupos_diarias"
    ADD CONSTRAINT "uq_metricas_dia_grupo" UNIQUE ("data", "grupo_id");



ALTER TABLE ONLY "public"."vagas_grupo_fontes"
    ADD CONSTRAINT "vagas_grupo_fontes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."vagas_grupo_fontes"
    ADD CONSTRAINT "vagas_grupo_fontes_vaga_grupo_id_mensagem_id_key" UNIQUE ("vaga_grupo_id", "mensagem_id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."whatsapp_instances"
    ADD CONSTRAINT "whatsapp_instances_instance_id_key" UNIQUE ("instance_id");



ALTER TABLE ONLY "public"."whatsapp_instances"
    ADD CONSTRAINT "whatsapp_instances_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_avaliacoes_avaliador" ON "public"."avaliacoes_qualidade" USING "btree" ("avaliador");



CREATE INDEX "idx_avaliacoes_conversa" ON "public"."avaliacoes_qualidade" USING "btree" ("conversa_id");



CREATE INDEX "idx_avaliacoes_score" ON "public"."avaliacoes_qualidade" USING "btree" ("score_geral");



CREATE INDEX "idx_avaliacoes_tags" ON "public"."avaliacoes_qualidade" USING "gin" ("tags");



CREATE INDEX "idx_be_cliente_ts" ON "public"."business_events" USING "btree" ("cliente_id", "ts" DESC);



CREATE INDEX "idx_be_hospital_ts" ON "public"."business_events" USING "btree" ("hospital_id", "ts" DESC);



CREATE INDEX "idx_be_policy" ON "public"."business_events" USING "btree" ("policy_decision_id");



CREATE INDEX "idx_be_ts" ON "public"."business_events" USING "btree" ("ts" DESC);



CREATE INDEX "idx_be_type_ts" ON "public"."business_events" USING "btree" ("event_type", "ts" DESC);



CREATE INDEX "idx_be_vaga_ts" ON "public"."business_events" USING "btree" ("vaga_id", "ts" DESC);



CREATE INDEX "idx_briefing_historico_config" ON "public"."briefing_historico" USING "btree" ("briefing_config_id", "created_at" DESC);



CREATE INDEX "idx_briefing_sync_data" ON "public"."briefing_sync_log" USING "btree" ("created_at");



CREATE INDEX "idx_briefing_sync_hash" ON "public"."briefing_sync_log" USING "btree" ("doc_hash");



CREATE INDEX "idx_briefings_pendentes_channel" ON "public"."briefings_pendentes" USING "btree" ("channel_id");



CREATE INDEX "idx_briefings_pendentes_expira" ON "public"."briefings_pendentes" USING "btree" ("expira_em");



CREATE INDEX "idx_briefings_pendentes_status" ON "public"."briefings_pendentes" USING "btree" ("status");



CREATE INDEX "idx_business_alerts_hospital" ON "public"."business_alerts" USING "btree" ("hospital_id") WHERE ("hospital_id" IS NOT NULL);



CREATE INDEX "idx_business_alerts_notified" ON "public"."business_alerts" USING "btree" ("notified") WHERE ("notified" = false);



CREATE INDEX "idx_business_alerts_ts" ON "public"."business_alerts" USING "btree" ("ts" DESC);



CREATE INDEX "idx_business_alerts_type" ON "public"."business_alerts" USING "btree" ("alert_type");



CREATE UNIQUE INDEX "idx_business_events_dedupe_key" ON "public"."business_events" USING "btree" ("dedupe_key") WHERE ("dedupe_key" IS NOT NULL);



CREATE INDEX "idx_campaign_contact_campaign" ON "public"."campaign_contact_history" USING "btree" ("campaign_id");



CREATE INDEX "idx_campaign_contact_lookup" ON "public"."campaign_contact_history" USING "btree" ("cliente_id", "sent_at" DESC);



CREATE INDEX "idx_campanhas_ativo" ON "public"."campanhas" USING "btree" ("ativo") WHERE ("ativo" = true);



CREATE INDEX "idx_campanhas_friendly_name" ON "public"."campanhas" USING "btree" ("friendly_name");



CREATE INDEX "idx_campanhas_status_agendar" ON "public"."campanhas" USING "btree" ("status", "agendar_para") WHERE ("status" = 'agendada'::"text");



CREATE INDEX "idx_campanhas_template_sid" ON "public"."campanhas" USING "btree" ("template_sid");



CREATE UNIQUE INDEX "idx_clientes_bitrix_unique" ON "public"."clientes" USING "btree" ("bitrix_id") WHERE ("bitrix_id" IS NOT NULL);



CREATE INDEX "idx_clientes_cidade" ON "public"."clientes" USING "btree" ("cidade");



CREATE INDEX "idx_clientes_cpf" ON "public"."clientes" USING "btree" ("cpf") WHERE ("cpf" IS NOT NULL);



CREATE UNIQUE INDEX "idx_clientes_cpf_unique" ON "public"."clientes" USING "btree" ("cpf") WHERE ("cpf" IS NOT NULL);



CREATE INDEX "idx_clientes_created_at" ON "public"."clientes" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_clientes_crm" ON "public"."clientes" USING "btree" ("crm") WHERE ("crm" IS NOT NULL);



CREATE UNIQUE INDEX "idx_clientes_crm_unique" ON "public"."clientes" USING "btree" ("crm") WHERE ("crm" IS NOT NULL);



CREATE INDEX "idx_clientes_email" ON "public"."clientes" USING "btree" ("email") WHERE ("email" IS NOT NULL);



CREATE INDEX "idx_clientes_especialidade" ON "public"."clientes" USING "btree" ("especialidade");



CREATE INDEX "idx_clientes_estado" ON "public"."clientes" USING "btree" ("estado");



CREATE INDEX "idx_clientes_grupo_piloto" ON "public"."clientes" USING "btree" ("grupo_piloto") WHERE ("grupo_piloto" = true);



CREATE INDEX "idx_clientes_opt_out" ON "public"."clientes" USING "btree" ("opt_out") WHERE (("opt_out" = false) AND ("deleted_at" IS NULL));



CREATE INDEX "idx_clientes_opted_out" ON "public"."clientes" USING "btree" ("opted_out") WHERE ("opted_out" = false);



CREATE INDEX "idx_clientes_stage" ON "public"."clientes" USING "btree" ("stage_jornada") WHERE ("deleted_at" IS NULL);



CREATE INDEX "idx_clientes_status" ON "public"."clientes" USING "btree" ("status");



CREATE INDEX "idx_clientes_telefone" ON "public"."clientes" USING "btree" ("telefone");



CREATE INDEX "idx_clientes_ultima_abertura" ON "public"."clientes" USING "gin" ("ultima_abertura");



CREATE INDEX "idx_conhecimento_arquivo" ON "public"."conhecimento_julia" USING "btree" ("arquivo");



CREATE INDEX "idx_conhecimento_ativo" ON "public"."conhecimento_julia" USING "btree" ("ativo") WHERE ("ativo" = true);



CREATE INDEX "idx_conhecimento_embedding" ON "public"."conhecimento_julia" USING "ivfflat" ("embedding" "public"."vector_cosine_ops") WITH ("lists"='100');



CREATE INDEX "idx_conhecimento_subtipo" ON "public"."conhecimento_julia" USING "btree" ("subtipo");



CREATE INDEX "idx_conhecimento_tags" ON "public"."conhecimento_julia" USING "gin" ("tags");



CREATE INDEX "idx_conhecimento_tipo" ON "public"."conhecimento_julia" USING "btree" ("tipo");



CREATE INDEX "idx_contatos_grupo_empresa" ON "public"."contatos_grupo" USING "btree" ("empresa");



CREATE INDEX "idx_contatos_grupo_jid" ON "public"."contatos_grupo" USING "btree" ("jid");



CREATE INDEX "idx_contatos_grupo_telefone" ON "public"."contatos_grupo" USING "btree" ("telefone");



CREATE INDEX "idx_contatos_grupo_tipo" ON "public"."contatos_grupo" USING "btree" ("tipo");



CREATE INDEX "idx_conversations_chatwoot" ON "public"."conversations" USING "btree" ("chatwoot_conversation_id") WHERE ("chatwoot_conversation_id" IS NOT NULL);



CREATE INDEX "idx_conversations_cliente" ON "public"."conversations" USING "btree" ("cliente_id");



CREATE INDEX "idx_conversations_controlled_by" ON "public"."conversations" USING "btree" ("controlled_by");



CREATE INDEX "idx_conversations_first_touch" ON "public"."conversations" USING "btree" ("first_touch_campaign_id") WHERE ("first_touch_campaign_id" IS NOT NULL);



CREATE INDEX "idx_conversations_followup" ON "public"."conversations" USING "btree" ("stage", "controlled_by", "ultima_mensagem_em") WHERE ("pausado_ate" IS NULL);



CREATE INDEX "idx_conversations_last_message" ON "public"."conversations" USING "btree" ("last_message_at" DESC);



CREATE INDEX "idx_conversations_last_touch" ON "public"."conversations" USING "btree" ("last_touch_campaign_id") WHERE ("last_touch_campaign_id" IS NOT NULL);



CREATE INDEX "idx_conversations_last_touch_at" ON "public"."conversations" USING "btree" ("last_touch_at" DESC) WHERE ("last_touch_at" IS NOT NULL);



CREATE INDEX "idx_conversations_status" ON "public"."conversations" USING "btree" ("status");



CREATE UNIQUE INDEX "idx_data_anomalies_dedup" ON "public"."data_anomalies" USING "btree" ("anomaly_type", "entity_type", "entity_id") WHERE ("resolved" = false);



CREATE INDEX "idx_data_anomalies_entity" ON "public"."data_anomalies" USING "btree" ("entity_type", "entity_id");



CREATE INDEX "idx_data_anomalies_last_seen" ON "public"."data_anomalies" USING "btree" ("last_seen_at" DESC);



CREATE INDEX "idx_data_anomalies_severity" ON "public"."data_anomalies" USING "btree" ("severity") WHERE ("resolved" = false);



CREATE INDEX "idx_data_anomalies_type" ON "public"."data_anomalies" USING "btree" ("anomaly_type");



CREATE INDEX "idx_data_anomalies_unresolved" ON "public"."data_anomalies" USING "btree" ("resolved") WHERE ("resolved" = false);



CREATE INDEX "idx_deteccao_bot_cliente" ON "public"."metricas_deteccao_bot" USING "btree" ("cliente_id");



CREATE INDEX "idx_deteccao_bot_conversa" ON "public"."metricas_deteccao_bot" USING "btree" ("conversa_id");



CREATE INDEX "idx_deteccao_bot_data" ON "public"."metricas_deteccao_bot" USING "btree" ("created_at");



CREATE INDEX "idx_deteccao_bot_falso_positivo" ON "public"."metricas_deteccao_bot" USING "btree" ("falso_positivo");



CREATE INDEX "idx_diretrizes_ativo" ON "public"."diretrizes" USING "btree" ("ativo") WHERE ("ativo" = true);



CREATE INDEX "idx_diretrizes_cliente" ON "public"."diretrizes" USING "btree" ("cliente_id") WHERE ("cliente_id" IS NOT NULL);



CREATE INDEX "idx_diretrizes_expira" ON "public"."diretrizes" USING "btree" ("expira_em") WHERE ("expira_em" IS NOT NULL);



CREATE INDEX "idx_diretrizes_tipo" ON "public"."diretrizes" USING "btree" ("tipo");



CREATE INDEX "idx_doctor_context_cliente" ON "public"."doctor_context" USING "btree" ("cliente_id");



CREATE INDEX "idx_doctor_context_cliente_tipo" ON "public"."doctor_context" USING "btree" ("cliente_id", "tipo");



CREATE INDEX "idx_doctor_context_created_at" ON "public"."doctor_context" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_doctor_context_embedding_hnsw" ON "public"."doctor_context" USING "hnsw" ("embedding" "public"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



COMMENT ON INDEX "public"."idx_doctor_context_embedding_hnsw" IS 'Indice HNSW para busca semantica com cosine similarity';



CREATE INDEX "idx_doctor_state_active_objection" ON "public"."doctor_state" USING "btree" ("objection_severity") WHERE ("active_objection" IS NOT NULL);



CREATE INDEX "idx_doctor_state_last_touch_at" ON "public"."doctor_state" USING "btree" ("last_touch_at") WHERE ("last_touch_at" IS NOT NULL);



CREATE INDEX "idx_doctor_state_lifecycle" ON "public"."doctor_state" USING "btree" ("lifecycle_stage");



CREATE INDEX "idx_doctor_state_next_allowed" ON "public"."doctor_state" USING "btree" ("next_allowed_at") WHERE ("next_allowed_at" IS NOT NULL);



CREATE INDEX "idx_doctor_state_permission" ON "public"."doctor_state" USING "btree" ("permission_state");



CREATE INDEX "idx_doctor_state_temperature_band" ON "public"."doctor_state" USING "btree" ("temperature_band");



CREATE INDEX "idx_eh_cliente" ON "public"."external_handoffs" USING "btree" ("cliente_id");



CREATE INDEX "idx_eh_divulgador_tel" ON "public"."external_handoffs" USING "btree" ("divulgador_telefone");



CREATE INDEX "idx_eh_reserved_until" ON "public"."external_handoffs" USING "btree" ("reserved_until") WHERE ("status" = 'pending'::"text");



CREATE INDEX "idx_eh_status" ON "public"."external_handoffs" USING "btree" ("status");



CREATE UNIQUE INDEX "idx_eh_unique_active_vaga" ON "public"."external_handoffs" USING "btree" ("vaga_id") WHERE ("status" = ANY (ARRAY['pending'::"text", 'contacted'::"text"]));



CREATE INDEX "idx_eh_vaga" ON "public"."external_handoffs" USING "btree" ("vaga_id");



CREATE INDEX "idx_envios_campanha" ON "public"."envios" USING "btree" ("campanha_id");



CREATE INDEX "idx_envios_cliente" ON "public"."envios" USING "btree" ("cliente_id");



CREATE INDEX "idx_envios_enviado" ON "public"."envios" USING "btree" ("enviado_em" DESC) WHERE ("enviado_em" IS NOT NULL);



CREATE INDEX "idx_envios_execucao" ON "public"."envios" USING "btree" ("execucao_campanha_id");



CREATE INDEX "idx_envios_origem" ON "public"."envios" USING "btree" ("origem");



CREATE INDEX "idx_envios_pendentes" ON "public"."envios" USING "btree" ("created_at") WHERE ("status" = 'pendente'::"text");



CREATE INDEX "idx_envios_status" ON "public"."envios" USING "btree" ("status");



CREATE INDEX "idx_envios_twilio_sid" ON "public"."envios" USING "btree" ("twilio_message_sid") WHERE ("twilio_message_sid" IS NOT NULL);



CREATE INDEX "idx_especialidades_alias_especialidade" ON "public"."especialidades_alias" USING "btree" ("especialidade_id");



CREATE INDEX "idx_especialidades_alias_normalizado" ON "public"."especialidades_alias" USING "btree" ("alias_normalizado");



CREATE INDEX "idx_especialidades_alias_trgm" ON "public"."especialidades_alias" USING "gin" ("alias_normalizado" "public"."gin_trgm_ops");



CREATE INDEX "idx_especialidades_nome_trgm" ON "public"."especialidades" USING "gin" ("nome" "public"."gin_trgm_ops");



CREATE INDEX "idx_execucoes_agendada" ON "public"."execucoes_campanhas" USING "btree" ("data_hora_agendada") WHERE ("status" = ANY (ARRAY['agendada'::"text", 'em_execucao'::"text"]));



CREATE INDEX "idx_execucoes_created" ON "public"."execucoes_campanhas" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_execucoes_status" ON "public"."execucoes_campanhas" USING "btree" ("status");



CREATE INDEX "idx_external_contacts_empresa" ON "public"."external_contacts" USING "btree" ("empresa");



CREATE INDEX "idx_external_contacts_permission" ON "public"."external_contacts" USING "btree" ("permission_state");



CREATE INDEX "idx_feature_flags_updated_at" ON "public"."feature_flags" USING "btree" ("updated_at" DESC);



CREATE INDEX "idx_feedbacks_cliente" ON "public"."feedbacks_gestor" USING "btree" ("cliente_id");



CREATE INDEX "idx_feedbacks_nao_aplicado" ON "public"."feedbacks_gestor" USING "btree" ("aplicado") WHERE ("aplicado" = false);



CREATE INDEX "idx_feedbacks_tipo" ON "public"."feedbacks_gestor" USING "btree" ("tipo");



CREATE INDEX "idx_fila_created_at" ON "public"."fila_processamento_grupos" USING "btree" ("created_at");



CREATE INDEX "idx_fila_estagio" ON "public"."fila_processamento_grupos" USING "btree" ("estagio");



CREATE INDEX "idx_fila_mensagens_campanha_id" ON "public"."fila_mensagens" USING "btree" ((("metadata" ->> 'campanha_id'::"text"))) WHERE (("metadata" ->> 'campanha_id'::"text") IS NOT NULL);



CREATE INDEX "idx_fila_mensagens_cliente" ON "public"."fila_mensagens" USING "btree" ("cliente_id");



CREATE INDEX "idx_fila_mensagens_outcome" ON "public"."fila_mensagens" USING "btree" ("outcome") WHERE ("outcome" IS NOT NULL);



CREATE INDEX "idx_fila_mensagens_provider_message_id" ON "public"."fila_mensagens" USING "btree" ("provider_message_id") WHERE ("provider_message_id" IS NOT NULL);



CREATE INDEX "idx_fila_mensagens_status_agendar" ON "public"."fila_mensagens" USING "btree" ("status", "agendar_para") WHERE ("status" = 'pendente'::"text");



CREATE INDEX "idx_fila_proximo_retry" ON "public"."fila_processamento_grupos" USING "btree" ("proximo_retry");



CREATE INDEX "idx_grupos_whatsapp_ativo" ON "public"."grupos_whatsapp" USING "btree" ("ativo") WHERE ("ativo" = true);



CREATE INDEX "idx_grupos_whatsapp_jid" ON "public"."grupos_whatsapp" USING "btree" ("jid");



CREATE INDEX "idx_grupos_whatsapp_regiao" ON "public"."grupos_whatsapp" USING "btree" ("regiao");



CREATE INDEX "idx_grupos_whatsapp_tipo" ON "public"."grupos_whatsapp" USING "btree" ("tipo");



CREATE INDEX "idx_handoffs_conversa_id" ON "public"."handoffs" USING "btree" ("conversa_id");



CREATE INDEX "idx_handoffs_conversation" ON "public"."handoffs" USING "btree" ("conversation_id");



CREATE INDEX "idx_handoffs_created_at" ON "public"."handoffs" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_handoffs_status" ON "public"."handoffs" USING "btree" ("status");



CREATE INDEX "idx_hospitais_alias_hospital" ON "public"."hospitais_alias" USING "btree" ("hospital_id");



CREATE INDEX "idx_hospitais_alias_normalizado" ON "public"."hospitais_alias" USING "btree" ("alias_normalizado");



CREATE INDEX "idx_hospitais_alias_trgm" ON "public"."hospitais_alias" USING "gin" ("alias_normalizado" "public"."gin_trgm_ops");



CREATE INDEX "idx_hospitais_nome_trgm" ON "public"."hospitais" USING "gin" ("nome" "public"."gin_trgm_ops");



CREATE INDEX "idx_hospitais_precisa_revisao" ON "public"."hospitais" USING "btree" ("precisa_revisao") WHERE ("precisa_revisao" = true);



CREATE INDEX "idx_hut_handoff" ON "public"."handoff_used_tokens" USING "btree" ("handoff_id");



CREATE INDEX "idx_intent_log_cliente" ON "public"."intent_log" USING "btree" ("cliente_id");



CREATE INDEX "idx_intent_log_expires" ON "public"."intent_log" USING "btree" ("expires_at");



CREATE INDEX "idx_intent_log_type" ON "public"."intent_log" USING "btree" ("intent_type");



CREATE INDEX "idx_interacoes_attributed_campaign" ON "public"."interacoes" USING "btree" ("attributed_campaign_id") WHERE ("attributed_campaign_id" IS NOT NULL);



CREATE INDEX "idx_interacoes_attributed_campaign_origem" ON "public"."interacoes" USING "btree" ("attributed_campaign_id", "origem", "created_at") WHERE ("attributed_campaign_id" IS NOT NULL);



CREATE INDEX "idx_interacoes_cliente_created" ON "public"."interacoes" USING "btree" ("cliente_id", "created_at" DESC);



CREATE INDEX "idx_interacoes_conversation" ON "public"."interacoes" USING "btree" ("conversation_id");



CREATE INDEX "idx_interacoes_created" ON "public"."interacoes" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_interacoes_deal" ON "public"."interacoes" USING "btree" ("deal_bitrix_id") WHERE ("deal_bitrix_id" IS NOT NULL);



CREATE INDEX "idx_interacoes_envio" ON "public"."interacoes" USING "btree" ("envio_id");



CREATE INDEX "idx_interacoes_origem_tipo" ON "public"."interacoes" USING "btree" ("origem", "tipo");



CREATE INDEX "idx_interacoes_twilio_sid" ON "public"."interacoes" USING "btree" ("twilio_message_sid") WHERE ("twilio_message_sid" IS NOT NULL);



CREATE INDEX "idx_julia_status_recente" ON "public"."julia_status" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_log_cliente_id" ON "public"."clientes_log" USING "btree" ("cliente_id");



CREATE INDEX "idx_log_timestamp" ON "public"."clientes_log" USING "btree" ("timestamp" DESC);



CREATE INDEX "idx_mensagens_fora_horario_ack" ON "public"."mensagens_fora_horario" USING "btree" ("ack_enviado", "cliente_id", "recebida_em");



CREATE INDEX "idx_mensagens_fora_horario_cliente_id" ON "public"."mensagens_fora_horario" USING "btree" ("cliente_id");



CREATE UNIQUE INDEX "idx_mensagens_fora_horario_inbound_unique" ON "public"."mensagens_fora_horario" USING "btree" ("inbound_message_id") WHERE ("inbound_message_id" IS NOT NULL);



CREATE INDEX "idx_mensagens_fora_horario_pendentes" ON "public"."mensagens_fora_horario" USING "btree" ("processada", "recebida_em") WHERE ("processada" = false);



CREATE INDEX "idx_mensagens_grupo_contato" ON "public"."mensagens_grupo" USING "btree" ("contato_id");



CREATE INDEX "idx_mensagens_grupo_grupo" ON "public"."mensagens_grupo" USING "btree" ("grupo_id");



CREATE INDEX "idx_mensagens_grupo_heuristica" ON "public"."mensagens_grupo" USING "btree" ("status", "created_at") WHERE ("status" = 'heuristica_passou'::"text");



CREATE INDEX "idx_mensagens_grupo_ofertas" ON "public"."mensagens_grupo" USING "btree" ("grupo_id", "timestamp_msg") WHERE ("eh_oferta" = true);



CREATE INDEX "idx_mensagens_grupo_pendentes" ON "public"."mensagens_grupo" USING "btree" ("status", "created_at") WHERE ("status" = 'pendente'::"text");



CREATE INDEX "idx_mensagens_grupo_status" ON "public"."mensagens_grupo" USING "btree" ("status");



CREATE INDEX "idx_mensagens_grupo_timestamp" ON "public"."mensagens_grupo" USING "btree" ("timestamp_msg" DESC);



CREATE INDEX "idx_metricas_campanha" ON "public"."metricas_campanhas" USING "btree" ("campanha_id");



CREATE INDEX "idx_metricas_conversa_conversa" ON "public"."metricas_conversa" USING "btree" ("conversa_id");



CREATE INDEX "idx_metricas_conversa_resultado" ON "public"."metricas_conversa" USING "btree" ("resultado");



CREATE INDEX "idx_metricas_execucao" ON "public"."metricas_campanhas" USING "btree" ("execucao_campanha_id");



CREATE INDEX "idx_metricas_grupos_data" ON "public"."metricas_grupos_diarias" USING "btree" ("data");



CREATE INDEX "idx_metricas_grupos_grupo" ON "public"."metricas_grupos_diarias" USING "btree" ("grupo_id");



CREATE INDEX "idx_metricas_nome" ON "public"."metricas_campanhas" USING "btree" ("nome_template");



CREATE INDEX "idx_metricas_pipeline_data" ON "public"."metricas_pipeline_diarias" USING "btree" ("data");



CREATE INDEX "idx_outbound_dedupe_cliente" ON "public"."outbound_dedupe" USING "btree" ("cliente_id");



CREATE INDEX "idx_outbound_dedupe_created" ON "public"."outbound_dedupe" USING "btree" ("created_at");



CREATE INDEX "idx_outbound_dedupe_key" ON "public"."outbound_dedupe" USING "btree" ("dedupe_key");



CREATE INDEX "idx_outbound_dedupe_status" ON "public"."outbound_dedupe" USING "btree" ("status") WHERE ("status" = ANY (ARRAY['queued'::"text", 'sent'::"text"]));



CREATE INDEX "idx_policy_events_action" ON "public"."policy_events" USING "btree" ("primary_action") WHERE ("event_type" = 'decision'::"text");



CREATE INDEX "idx_policy_events_cliente" ON "public"."policy_events" USING "btree" ("cliente_id");



CREATE INDEX "idx_policy_events_decision_id" ON "public"."policy_events" USING "btree" ("policy_decision_id");



CREATE INDEX "idx_policy_events_effect" ON "public"."policy_events" USING "btree" ("effect_type") WHERE ("event_type" = 'effect'::"text");



CREATE INDEX "idx_policy_events_rule" ON "public"."policy_events" USING "btree" ("rule_matched") WHERE ("event_type" = 'decision'::"text");



CREATE INDEX "idx_policy_events_ts" ON "public"."policy_events" USING "btree" ("ts" DESC);



CREATE INDEX "idx_policy_events_type" ON "public"."policy_events" USING "btree" ("event_type");



CREATE INDEX "idx_prompts_especialidade" ON "public"."prompts" USING "btree" ("especialidade_id") WHERE ("especialidade_id" IS NOT NULL);



CREATE INDEX "idx_prompts_nome_ativo" ON "public"."prompts" USING "btree" ("nome", "ativo");



CREATE INDEX "idx_reports_periodo" ON "public"."reports" USING "btree" ("periodo_inicio", "periodo_fim");



CREATE INDEX "idx_reports_tipo_data" ON "public"."reports" USING "btree" ("tipo", "created_at" DESC);



CREATE INDEX "idx_slack_comandos_data" ON "public"."slack_comandos" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_slack_comandos_user" ON "public"."slack_comandos" USING "btree" ("user_id");



CREATE INDEX "idx_slack_sessoes_expires" ON "public"."slack_sessoes" USING "btree" ("expires_at");



CREATE INDEX "idx_slack_sessoes_user_channel" ON "public"."slack_sessoes" USING "btree" ("user_id", "channel_id");



CREATE INDEX "idx_sugestoes_conversa" ON "public"."sugestoes_prompt" USING "btree" ("conversa_id");



CREATE INDEX "idx_sugestoes_status" ON "public"."sugestoes_prompt" USING "btree" ("status");



CREATE INDEX "idx_sugestoes_tipo" ON "public"."sugestoes_prompt" USING "btree" ("tipo");



CREATE INDEX "idx_touch_reconciliation_log_cliente_id" ON "public"."touch_reconciliation_log" USING "btree" ("cliente_id");



CREATE INDEX "idx_touch_reconciliation_log_processed_at" ON "public"."touch_reconciliation_log" USING "btree" ("processed_at");



CREATE INDEX "idx_touch_reconciliation_log_status" ON "public"."touch_reconciliation_log" USING "btree" ("status") WHERE ("status" = 'processing'::"text");



CREATE INDEX "idx_vagas_busca" ON "public"."vagas" USING "btree" ("especialidade_id", "status", "data") WHERE ((("status")::"text" = 'aberta'::"text") AND ("deleted_at" IS NULL));



CREATE INDEX "idx_vagas_data" ON "public"."vagas" USING "btree" ("data", "status") WHERE ("deleted_at" IS NULL);



CREATE INDEX "idx_vagas_grupo_aprovadas" ON "public"."vagas_grupo" USING "btree" ("status", "created_at") WHERE ("status" = 'aprovada'::"text");



CREATE INDEX "idx_vagas_grupo_data" ON "public"."vagas_grupo" USING "btree" ("data");



CREATE INDEX "idx_vagas_grupo_dedup" ON "public"."vagas_grupo" USING "btree" ("hospital_id", "data", "periodo_id", "especialidade_id") WHERE ("eh_duplicada" = false);



CREATE INDEX "idx_vagas_grupo_fontes_grupo" ON "public"."vagas_grupo_fontes" USING "btree" ("grupo_id");



CREATE INDEX "idx_vagas_grupo_fontes_mensagem" ON "public"."vagas_grupo_fontes" USING "btree" ("mensagem_id");



CREATE INDEX "idx_vagas_grupo_fontes_vaga" ON "public"."vagas_grupo_fontes" USING "btree" ("vaga_grupo_id");



CREATE INDEX "idx_vagas_grupo_grupo" ON "public"."vagas_grupo" USING "btree" ("grupo_origem_id");



CREATE INDEX "idx_vagas_grupo_hash" ON "public"."vagas_grupo" USING "btree" ("hash_dedup") WHERE ("hash_dedup" IS NOT NULL);



CREATE INDEX "idx_vagas_grupo_hospital" ON "public"."vagas_grupo" USING "btree" ("hospital_id");



CREATE INDEX "idx_vagas_grupo_mensagem" ON "public"."vagas_grupo" USING "btree" ("mensagem_id");



CREATE INDEX "idx_vagas_grupo_revisao" ON "public"."vagas_grupo" USING "btree" ("status", "created_at") WHERE ("status" = 'aguardando_revisao'::"text");



CREATE INDEX "idx_vagas_grupo_status" ON "public"."vagas_grupo" USING "btree" ("status");



CREATE INDEX "idx_vagas_grupo_valor_tipo" ON "public"."vagas_grupo" USING "btree" ("valor_tipo");



CREATE INDEX "idx_vagas_hospital" ON "public"."vagas" USING "btree" ("hospital_id", "status", "data") WHERE ("deleted_at" IS NULL);



CREATE INDEX "idx_vagas_origem" ON "public"."vagas" USING "btree" ("origem");



CREATE INDEX "idx_vagas_pendente_confirmacao" ON "public"."vagas" USING "btree" ("status", "pendente_confirmacao_em") WHERE (("status")::"text" = 'pendente_confirmacao'::"text");



CREATE INDEX "idx_vagas_reservada_fim" ON "public"."vagas" USING "btree" ("status", "hora_fim", "data") WHERE (("status")::"text" = 'reservada'::"text");



CREATE INDEX "idx_vagas_source" ON "public"."vagas" USING "btree" ("source") WHERE ("source" IS NOT NULL);



CREATE INDEX "idx_vagas_source_id" ON "public"."vagas" USING "btree" ("source_id") WHERE ("source_id" IS NOT NULL);



CREATE INDEX "idx_vagas_status_realizada" ON "public"."vagas" USING "btree" ("status") WHERE (("status")::"text" = 'realizada'::"text");



CREATE INDEX "idx_vagas_vaga_grupo_id" ON "public"."vagas" USING "btree" ("vaga_grupo_id");



CREATE INDEX "idx_vagas_valor_tipo" ON "public"."vagas" USING "btree" ("valor_tipo");



CREATE INDEX "idx_whatsapp_instances_active" ON "public"."whatsapp_instances" USING "btree" ("is_active") WHERE ("is_active" = true);



CREATE INDEX "idx_whatsapp_instances_status" ON "public"."whatsapp_instances" USING "btree" ("status");



CREATE OR REPLACE TRIGGER "app_settings_updated_at" BEFORE UPDATE ON "public"."app_settings" FOR EACH ROW EXECUTE FUNCTION "public"."update_app_settings_updated_at"();



CREATE OR REPLACE TRIGGER "clientes_audit_trigger" AFTER INSERT OR DELETE OR UPDATE ON "public"."clientes" FOR EACH ROW EXECUTE FUNCTION "public"."log_clientes_changes"();



CREATE OR REPLACE TRIGGER "conhecimento_julia_updated_at" BEFORE UPDATE ON "public"."conhecimento_julia" FOR EACH ROW EXECUTE FUNCTION "public"."update_conhecimento_updated_at"();



CREATE OR REPLACE TRIGGER "ensure_single_active_prompt" BEFORE INSERT OR UPDATE ON "public"."prompts" FOR EACH ROW EXECUTE FUNCTION "public"."check_single_active_prompt"();



CREATE OR REPLACE TRIGGER "trg_data_anomalies_updated_at" BEFORE UPDATE ON "public"."data_anomalies" FOR EACH ROW EXECUTE FUNCTION "public"."update_data_anomalies_updated_at"();



CREATE OR REPLACE TRIGGER "trg_offer_accepted" AFTER INSERT OR UPDATE OF "status" ON "public"."vagas" FOR EACH ROW EXECUTE FUNCTION "public"."emit_offer_accepted"();



CREATE OR REPLACE TRIGGER "trg_shift_completed" AFTER UPDATE OF "status" ON "public"."vagas" FOR EACH ROW EXECUTE FUNCTION "public"."emit_shift_completed"();



CREATE OR REPLACE TRIGGER "trg_validar_valor_vagas" BEFORE INSERT OR UPDATE ON "public"."vagas" FOR EACH ROW EXECUTE FUNCTION "public"."validar_valor_vaga"();



CREATE OR REPLACE TRIGGER "trg_validar_valor_vagas_grupo" BEFORE INSERT OR UPDATE ON "public"."vagas_grupo" FOR EACH ROW EXECUTE FUNCTION "public"."validar_valor_vaga"();



CREATE OR REPLACE TRIGGER "trigger_conversations_updated_at" BEFORE UPDATE ON "public"."conversations" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trigger_doctor_state_updated_at" BEFORE UPDATE ON "public"."doctor_state" FOR EACH ROW EXECUTE FUNCTION "public"."update_doctor_state_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_external_handoffs_updated_at" BEFORE UPDATE ON "public"."external_handoffs" FOR EACH ROW EXECUTE FUNCTION "public"."update_external_handoffs_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_fila_processamento_updated_at" BEFORE UPDATE ON "public"."fila_processamento_grupos" FOR EACH ROW EXECUTE FUNCTION "public"."update_fila_processamento_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_normalizar_especialidade_alias" BEFORE INSERT OR UPDATE ON "public"."especialidades_alias" FOR EACH ROW EXECUTE FUNCTION "public"."normalizar_alias"();



CREATE OR REPLACE TRIGGER "trigger_normalizar_hospital_alias" BEFORE INSERT OR UPDATE ON "public"."hospitais_alias" FOR EACH ROW EXECUTE FUNCTION "public"."normalizar_alias"();



CREATE OR REPLACE TRIGGER "trigger_sync_bitrix" AFTER INSERT OR UPDATE OF "primeiro_nome", "sobrenome", "telefone", "especialidade", "email", "crm", "cidade", "estado" ON "public"."clientes" FOR EACH ROW EXECUTE FUNCTION "public"."sync_cliente_to_bitrix"();



COMMENT ON TRIGGER "trigger_sync_bitrix" ON "public"."clientes" IS 'Trigger que sincroniza automaticamente clientes com Bitrix24';



CREATE OR REPLACE TRIGGER "trigger_update_conversation_on_message" AFTER INSERT ON "public"."interacoes" FOR EACH ROW EXECUTE FUNCTION "public"."update_conversation_on_new_message"();



CREATE OR REPLACE TRIGGER "trigger_whatsapp_instances_updated_at" BEFORE UPDATE ON "public"."whatsapp_instances" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_briefing_config_updated_at" BEFORE UPDATE ON "public"."briefing_config" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_campanhas_updated_at" BEFORE UPDATE ON "public"."campanhas" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_clientes_updated_at" BEFORE UPDATE ON "public"."clientes" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_diretrizes_updated_at" BEFORE UPDATE ON "public"."diretrizes" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_envios_updated_at" BEFORE UPDATE ON "public"."envios" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_execucoes_updated_at" BEFORE UPDATE ON "public"."execucoes_campanhas" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_interacoes_updated_at" BEFORE UPDATE ON "public"."interacoes" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_metricas_updated_at" BEFORE UPDATE ON "public"."metricas_campanhas" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."avaliacoes_qualidade"
    ADD CONSTRAINT "avaliacoes_qualidade_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."briefing_historico"
    ADD CONSTRAINT "briefing_historico_briefing_config_id_fkey" FOREIGN KEY ("briefing_config_id") REFERENCES "public"."briefing_config"("id");



ALTER TABLE ONLY "public"."business_alerts"
    ADD CONSTRAINT "business_alerts_hospital_id_fkey" FOREIGN KEY ("hospital_id") REFERENCES "public"."hospitais"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."business_events"
    ADD CONSTRAINT "business_events_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."business_events"
    ADD CONSTRAINT "business_events_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."business_events"
    ADD CONSTRAINT "business_events_hospital_id_fkey" FOREIGN KEY ("hospital_id") REFERENCES "public"."hospitais"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."business_events"
    ADD CONSTRAINT "business_events_interaction_id_fkey" FOREIGN KEY ("interaction_id") REFERENCES "public"."interacoes"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."business_events"
    ADD CONSTRAINT "business_events_vaga_id_fkey" FOREIGN KEY ("vaga_id") REFERENCES "public"."vagas"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."campaign_contact_history"
    ADD CONSTRAINT "campaign_contact_history_campaign_id_fkey" FOREIGN KEY ("campaign_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."campaign_contact_history"
    ADD CONSTRAINT "campaign_contact_history_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."clientes_log"
    ADD CONSTRAINT "clientes_log_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."contatos_grupo"
    ADD CONSTRAINT "contatos_grupo_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_campanha_id_fkey" FOREIGN KEY ("campanha_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_execucao_campanha_id_fkey" FOREIGN KEY ("execucao_campanha_id") REFERENCES "public"."execucoes_campanhas"("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_first_touch_campaign_id_fkey" FOREIGN KEY ("first_touch_campaign_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_last_touch_campaign_id_fkey" FOREIGN KEY ("last_touch_campaign_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."diretrizes"
    ADD CONSTRAINT "diretrizes_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."diretrizes"
    ADD CONSTRAINT "diretrizes_vaga_id_fkey" FOREIGN KEY ("vaga_id") REFERENCES "public"."vagas"("id");



ALTER TABLE ONLY "public"."doctor_context"
    ADD CONSTRAINT "doctor_context_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."doctor_state"
    ADD CONSTRAINT "doctor_state_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."envios"
    ADD CONSTRAINT "envios_campanha_id_fkey" FOREIGN KEY ("campanha_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."envios"
    ADD CONSTRAINT "envios_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."envios"
    ADD CONSTRAINT "envios_execucao_campanha_id_fkey" FOREIGN KEY ("execucao_campanha_id") REFERENCES "public"."execucoes_campanhas"("id");



ALTER TABLE ONLY "public"."especialidades_alias"
    ADD CONSTRAINT "especialidades_alias_especialidade_id_fkey" FOREIGN KEY ("especialidade_id") REFERENCES "public"."especialidades"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."external_handoffs"
    ADD CONSTRAINT "external_handoffs_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."external_handoffs"
    ADD CONSTRAINT "external_handoffs_vaga_id_fkey" FOREIGN KEY ("vaga_id") REFERENCES "public"."vagas"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."feedbacks_gestor"
    ADD CONSTRAINT "feedbacks_gestor_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."feedbacks_gestor"
    ADD CONSTRAINT "feedbacks_gestor_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."feedbacks_gestor"
    ADD CONSTRAINT "feedbacks_gestor_interacao_id_fkey" FOREIGN KEY ("interacao_id") REFERENCES "public"."interacoes"("id");



ALTER TABLE ONLY "public"."fila_mensagens"
    ADD CONSTRAINT "fila_mensagens_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."fila_mensagens"
    ADD CONSTRAINT "fila_mensagens_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."fila_processamento_grupos"
    ADD CONSTRAINT "fila_processamento_grupos_mensagem_id_fkey" FOREIGN KEY ("mensagem_id") REFERENCES "public"."mensagens_grupo"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."fila_processamento_grupos"
    ADD CONSTRAINT "fila_processamento_grupos_vaga_grupo_id_fkey" FOREIGN KEY ("vaga_grupo_id") REFERENCES "public"."vagas_grupo"("id");



ALTER TABLE ONLY "public"."metricas_campanhas"
    ADD CONSTRAINT "fk_metricas_execucao" FOREIGN KEY ("execucao_campanha_id") REFERENCES "public"."execucoes_campanhas"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."grupos_whatsapp"
    ADD CONSTRAINT "grupos_whatsapp_hospital_id_fkey" FOREIGN KEY ("hospital_id") REFERENCES "public"."hospitais"("id");



ALTER TABLE ONLY "public"."handoff_used_tokens"
    ADD CONSTRAINT "handoff_used_tokens_handoff_id_fkey" FOREIGN KEY ("handoff_id") REFERENCES "public"."external_handoffs"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."handoffs"
    ADD CONSTRAINT "handoffs_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."handoffs"
    ADD CONSTRAINT "handoffs_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."hospitais_alias"
    ADD CONSTRAINT "hospitais_alias_hospital_id_fkey" FOREIGN KEY ("hospital_id") REFERENCES "public"."hospitais"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."intent_log"
    ADD CONSTRAINT "intent_log_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."interacoes"
    ADD CONSTRAINT "interacoes_attributed_campaign_id_fkey" FOREIGN KEY ("attributed_campaign_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."interacoes"
    ADD CONSTRAINT "interacoes_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."interacoes"
    ADD CONSTRAINT "interacoes_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."interacoes"
    ADD CONSTRAINT "interacoes_envio_id_fkey" FOREIGN KEY ("envio_id") REFERENCES "public"."envios"("id");



ALTER TABLE ONLY "public"."interacoes"
    ADD CONSTRAINT "interacoes_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "public"."interacoes"("id");



ALTER TABLE ONLY "public"."mensagens_fora_horario"
    ADD CONSTRAINT "mensagens_fora_horario_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."mensagens_fora_horario"
    ADD CONSTRAINT "mensagens_fora_horario_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."mensagens_grupo"
    ADD CONSTRAINT "mensagens_grupo_contato_id_fkey" FOREIGN KEY ("contato_id") REFERENCES "public"."contatos_grupo"("id");



ALTER TABLE ONLY "public"."mensagens_grupo"
    ADD CONSTRAINT "mensagens_grupo_grupo_id_fkey" FOREIGN KEY ("grupo_id") REFERENCES "public"."grupos_whatsapp"("id");



ALTER TABLE ONLY "public"."metricas_campanhas"
    ADD CONSTRAINT "metricas_campanhas_campanha_id_fkey" FOREIGN KEY ("campanha_id") REFERENCES "public"."campanhas"("id");



ALTER TABLE ONLY "public"."metricas_conversa"
    ADD CONSTRAINT "metricas_conversa_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."metricas_deteccao_bot"
    ADD CONSTRAINT "metricas_deteccao_bot_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."metricas_deteccao_bot"
    ADD CONSTRAINT "metricas_deteccao_bot_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."metricas_grupos_diarias"
    ADD CONSTRAINT "metricas_grupos_diarias_grupo_id_fkey" FOREIGN KEY ("grupo_id") REFERENCES "public"."grupos_whatsapp"("id");



ALTER TABLE ONLY "public"."policy_events"
    ADD CONSTRAINT "policy_events_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."policy_events"
    ADD CONSTRAINT "policy_events_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."policy_events"
    ADD CONSTRAINT "policy_events_interaction_id_fkey" FOREIGN KEY ("interaction_id") REFERENCES "public"."interacoes"("id");



ALTER TABLE ONLY "public"."prompts"
    ADD CONSTRAINT "prompts_especialidade_id_fkey" FOREIGN KEY ("especialidade_id") REFERENCES "public"."especialidades"("id");



ALTER TABLE ONLY "public"."prompts_historico"
    ADD CONSTRAINT "prompts_historico_prompt_id_fkey" FOREIGN KEY ("prompt_id") REFERENCES "public"."prompts"("id");



ALTER TABLE ONLY "public"."sugestoes_prompt"
    ADD CONSTRAINT "sugestoes_prompt_avaliacao_id_fkey" FOREIGN KEY ("avaliacao_id") REFERENCES "public"."avaliacoes_qualidade"("id");



ALTER TABLE ONLY "public"."sugestoes_prompt"
    ADD CONSTRAINT "sugestoes_prompt_conversa_id_fkey" FOREIGN KEY ("conversa_id") REFERENCES "public"."conversations"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "public"."clientes"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_especialidade_id_fkey" FOREIGN KEY ("especialidade_id") REFERENCES "public"."especialidades"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_forma_recebimento_id_fkey" FOREIGN KEY ("forma_recebimento_id") REFERENCES "public"."formas_recebimento"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_contato_responsavel_id_fkey" FOREIGN KEY ("contato_responsavel_id") REFERENCES "public"."contatos_grupo"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_duplicada_de_fkey" FOREIGN KEY ("duplicada_de") REFERENCES "public"."vagas_grupo"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_especialidade_id_fkey" FOREIGN KEY ("especialidade_id") REFERENCES "public"."especialidades"("id");



ALTER TABLE ONLY "public"."vagas_grupo_fontes"
    ADD CONSTRAINT "vagas_grupo_fontes_contato_id_fkey" FOREIGN KEY ("contato_id") REFERENCES "public"."contatos_grupo"("id");



ALTER TABLE ONLY "public"."vagas_grupo_fontes"
    ADD CONSTRAINT "vagas_grupo_fontes_grupo_id_fkey" FOREIGN KEY ("grupo_id") REFERENCES "public"."grupos_whatsapp"("id");



ALTER TABLE ONLY "public"."vagas_grupo_fontes"
    ADD CONSTRAINT "vagas_grupo_fontes_mensagem_id_fkey" FOREIGN KEY ("mensagem_id") REFERENCES "public"."mensagens_grupo"("id");



ALTER TABLE ONLY "public"."vagas_grupo_fontes"
    ADD CONSTRAINT "vagas_grupo_fontes_vaga_grupo_id_fkey" FOREIGN KEY ("vaga_grupo_id") REFERENCES "public"."vagas_grupo"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_forma_recebimento_id_fkey" FOREIGN KEY ("forma_recebimento_id") REFERENCES "public"."formas_recebimento"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_grupo_origem_id_fkey" FOREIGN KEY ("grupo_origem_id") REFERENCES "public"."grupos_whatsapp"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_hospital_id_fkey" FOREIGN KEY ("hospital_id") REFERENCES "public"."hospitais"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_mensagem_id_fkey" FOREIGN KEY ("mensagem_id") REFERENCES "public"."mensagens_grupo"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_periodo_id_fkey" FOREIGN KEY ("periodo_id") REFERENCES "public"."periodos"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_setor_id_fkey" FOREIGN KEY ("setor_id") REFERENCES "public"."setores"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_tipos_vaga_id_fkey" FOREIGN KEY ("tipos_vaga_id") REFERENCES "public"."tipos_vaga"("id");



ALTER TABLE ONLY "public"."vagas_grupo"
    ADD CONSTRAINT "vagas_grupo_vaga_importada_id_fkey" FOREIGN KEY ("vaga_importada_id") REFERENCES "public"."vagas"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_hospital_id_fkey" FOREIGN KEY ("hospital_id") REFERENCES "public"."hospitais"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_periodo_id_fkey" FOREIGN KEY ("periodo_id") REFERENCES "public"."periodos"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_setor_id_fkey" FOREIGN KEY ("setor_id") REFERENCES "public"."setores"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_tipos_vaga_id_fkey" FOREIGN KEY ("tipos_vaga_id") REFERENCES "public"."tipos_vaga"("id");



ALTER TABLE ONLY "public"."vagas"
    ADD CONSTRAINT "vagas_vaga_grupo_id_fkey" FOREIGN KEY ("vaga_grupo_id") REFERENCES "public"."vagas_grupo"("id");



CREATE POLICY "Allow all for authenticated" ON "public"."mensagens_fora_horario" USING (true);



CREATE POLICY "Allow all for service role" ON "public"."doctor_state" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can insert campanhas" ON "public"."campanhas" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert conversations" ON "public"."conversations" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert doctor_context" ON "public"."doctor_context" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert envios" ON "public"."envios" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert execucoes_campanhas" ON "public"."execucoes_campanhas" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert handoffs" ON "public"."handoffs" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert interacoes" ON "public"."interacoes" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert metricas_campanhas" ON "public"."metricas_campanhas" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can insert whatsapp_instances" ON "public"."whatsapp_instances" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Authenticated users can read campanhas" ON "public"."campanhas" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read conversations" ON "public"."conversations" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read doctor_context" ON "public"."doctor_context" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read envios" ON "public"."envios" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read execucoes_campanhas" ON "public"."execucoes_campanhas" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read handoffs" ON "public"."handoffs" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read interacoes" ON "public"."interacoes" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read metricas_campanhas" ON "public"."metricas_campanhas" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can read whatsapp_instances" ON "public"."whatsapp_instances" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Authenticated users can update campanhas" ON "public"."campanhas" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update conversations" ON "public"."conversations" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update doctor_context" ON "public"."doctor_context" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update envios" ON "public"."envios" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update execucoes_campanhas" ON "public"."execucoes_campanhas" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update interacoes" ON "public"."interacoes" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update metricas_campanhas" ON "public"."metricas_campanhas" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Authenticated users can update whatsapp_instances" ON "public"."whatsapp_instances" FOR UPDATE TO "authenticated" USING (true) WITH CHECK (true);



CREATE POLICY "Service role all access" ON "public"."clientes" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role all access log" ON "public"."clientes_log" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access" ON "public"."app_settings" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access campanhas" ON "public"."campanhas" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access conversations" ON "public"."conversations" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access doctor_context" ON "public"."doctor_context" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access envios" ON "public"."envios" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access execucoes_campanhas" ON "public"."execucoes_campanhas" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access handoffs" ON "public"."handoffs" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access interacoes" ON "public"."interacoes" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access metricas_campanhas" ON "public"."metricas_campanhas" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access on contatos_grupo" ON "public"."contatos_grupo" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access on especialidades_alias" ON "public"."especialidades_alias" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access on grupos_whatsapp" ON "public"."grupos_whatsapp" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access on hospitais_alias" ON "public"."hospitais_alias" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access on mensagens_grupo" ON "public"."mensagens_grupo" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access on vagas_grupo" ON "public"."vagas_grupo" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access on vagas_grupo_fontes" ON "public"."vagas_grupo_fontes" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Service role full access whatsapp_instances" ON "public"."whatsapp_instances" TO "service_role" USING (true) WITH CHECK (true);



ALTER TABLE "public"."app_settings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."avaliacoes_qualidade" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."briefing_config" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."briefing_historico" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."briefing_sync_log" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."briefings_pendentes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."business_alerts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."business_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."campanhas" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."clientes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."clientes_log" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conhecimento_julia" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."contatos_grupo" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conversations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."data_anomalies" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "deny_anon_access" ON "public"."touch_reconciliation_log" TO "anon" USING (false);



CREATE POLICY "deny_authenticated_access" ON "public"."touch_reconciliation_log" TO "authenticated" USING (false);



ALTER TABLE "public"."diretrizes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."doctor_context" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."doctor_state" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."envios" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."especialidades" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."especialidades_alias" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "especialidades_select_authenticated" ON "public"."especialidades" FOR SELECT TO "authenticated" USING (true);



COMMENT ON POLICY "especialidades_select_authenticated" ON "public"."especialidades" IS 'Permite leitura de especialidades para usuários autenticados. Escrita só via service_role.';



ALTER TABLE "public"."execucoes_campanhas" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."external_handoffs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."feature_flags" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."feedbacks_gestor" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."fila_mensagens" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."fila_processamento_grupos" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."formas_recebimento" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "formas_recebimento_select_authenticated" ON "public"."formas_recebimento" FOR SELECT TO "authenticated" USING (true);



COMMENT ON POLICY "formas_recebimento_select_authenticated" ON "public"."formas_recebimento" IS 'Permite leitura de formas de recebimento para usuários autenticados. Escrita só via service_role.';



ALTER TABLE "public"."grupos_whatsapp" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."handoff_used_tokens" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."handoffs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."hospitais" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."hospitais_alias" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "hospitais_select_authenticated" ON "public"."hospitais" FOR SELECT TO "authenticated" USING (true);



COMMENT ON POLICY "hospitais_select_authenticated" ON "public"."hospitais" IS 'Permite leitura de hospitais para usuários autenticados. Escrita só via service_role.';



ALTER TABLE "public"."interacoes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."julia_status" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."mensagens_fora_horario" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."mensagens_grupo" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."metricas_campanhas" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."metricas_conversa" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."metricas_deteccao_bot" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."metricas_grupos_diarias" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."metricas_pipeline_diarias" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."notificacoes_gestor" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."outbound_dedupe" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."periodos" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "periodos_select_authenticated" ON "public"."periodos" FOR SELECT TO "authenticated" USING (true);



COMMENT ON POLICY "periodos_select_authenticated" ON "public"."periodos" IS 'Permite leitura de períodos para usuários autenticados. Escrita só via service_role.';



ALTER TABLE "public"."policy_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."prompts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."prompts_historico" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."report_schedule" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."reports" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "service_role_full_access" ON "public"."touch_reconciliation_log" TO "service_role" USING (true) WITH CHECK (true);



ALTER TABLE "public"."setores" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "setores_select_authenticated" ON "public"."setores" FOR SELECT TO "authenticated" USING (true);



COMMENT ON POLICY "setores_select_authenticated" ON "public"."setores" IS 'Permite leitura de setores para usuários autenticados. Escrita só via service_role.';



ALTER TABLE "public"."slack_comandos" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."slack_sessoes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."sugestoes_prompt" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tipos_vaga" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "tipos_vaga_select_authenticated" ON "public"."tipos_vaga" FOR SELECT TO "authenticated" USING (true);



COMMENT ON POLICY "tipos_vaga_select_authenticated" ON "public"."tipos_vaga" IS 'Permite leitura de tipos de vaga para usuários autenticados. Escrita só via service_role.';



ALTER TABLE "public"."touch_reconciliation_log" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."vagas" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."vagas_grupo" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."vagas_grupo_fontes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."whatsapp_instances" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";





GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_in"("cstring") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_out"("public"."gtrgm") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "service_role";

























































































































































REVOKE ALL ON FUNCTION "public"."audit_outbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."audit_outbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."audit_pipeline_inbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."audit_pipeline_inbound_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."audit_status_transition_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."audit_status_transition_coverage"("p_start" timestamp with time zone, "p_end" timestamp with time zone) TO "service_role";



GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."buscar_alvos_campanha"("p_filtros" "jsonb", "p_dias_sem_contato" integer, "p_excluir_cooling" boolean, "p_excluir_em_atendimento" boolean, "p_contact_cap" integer, "p_limite" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."buscar_candidatos_touch_reconciliation"("p_desde" timestamp with time zone, "p_limite" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_conhecimento"("query_embedding" "public"."vector", "tipo_filtro" "text", "subtipo_filtro" "text", "limite" integer, "threshold" double precision) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_conhecimento"("query_embedding" "public"."vector", "tipo_filtro" "text", "subtipo_filtro" "text", "limite" integer, "threshold" double precision) TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_especialidade_por_alias"("p_texto" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_especialidade_por_alias"("p_texto" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_especialidade_por_similaridade"("p_texto" "text", "p_threshold" double precision) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_especialidade_por_similaridade"("p_texto" "text", "p_threshold" double precision) TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_hospital_por_alias"("p_texto" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_hospital_por_alias"("p_texto" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_hospital_por_similaridade"("p_texto" "text", "p_threshold" double precision) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_hospital_por_similaridade"("p_texto" "text", "p_threshold" double precision) TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_memorias_recentes"("p_cliente_id" "uuid", "p_limite" integer, "p_tipo" character varying) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_memorias_recentes"("p_cliente_id" "uuid", "p_limite" integer, "p_tipo" character varying) TO "service_role";



REVOKE ALL ON FUNCTION "public"."buscar_memorias_similares"("p_cliente_id" "uuid", "p_embedding" "public"."vector", "p_limite" integer, "p_threshold" double precision) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."buscar_memorias_similares"("p_cliente_id" "uuid", "p_embedding" "public"."vector", "p_limite" integer, "p_threshold" double precision) TO "service_role";



REVOKE ALL ON FUNCTION "public"."check_single_active_prompt"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."check_single_active_prompt"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cleanup_old_dedupe_entries"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."consolidar_metricas_pipeline"("p_data" "date") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."consolidar_metricas_pipeline"("p_data" "date") TO "service_role";



REVOKE ALL ON FUNCTION "public"."contar_reservadas_vencidas"("limite_ts" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."contar_reservadas_vencidas"("limite_ts" timestamp with time zone) TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "service_role";



REVOKE ALL ON FUNCTION "public"."count_business_events"("p_hours" integer, "p_hospital_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."count_business_events"("p_hours" integer, "p_hospital_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."emit_offer_accepted"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."emit_offer_accepted"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."emit_shift_completed"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."emit_shift_completed"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_conversion_rates"("p_hours" integer, "p_hospital_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_conversion_rates"("p_hours" integer, "p_hospital_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_funnel_invariant_violations"("p_days" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_funnel_invariant_violations"("p_days" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_funnel_rates"("p_hours" integer, "p_hospital_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_funnel_rates"("p_hours" integer, "p_hospital_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_health_score_components"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_health_score_components"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_time_to_fill_breakdown"("p_days" integer, "p_hospital_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_time_to_fill_breakdown"("p_days" integer, "p_hospital_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_query_trgm"("text", "internal", smallint, "internal", "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_extract_value_trgm"("text", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_trgm_consistent"("internal", smallint, "text", integer, "internal", "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gin_trgm_triconsistent"("internal", smallint, "text", integer, "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_compress"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_consistent"("internal", "text", smallint, "oid", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_decompress"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_distance"("internal", "text", smallint, "oid", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_options"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_penalty"("internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_picksplit"("internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gtrgm_union"("internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "service_role";



REVOKE ALL ON FUNCTION "public"."incrementar_mensagens_contato"("p_contato_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."incrementar_mensagens_contato"("p_contato_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."incrementar_mensagens_grupo"("p_grupo_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."incrementar_mensagens_grupo"("p_grupo_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."incrementar_metricas_grupo"("p_data" "date", "p_grupo_id" "uuid", "p_mensagens" integer, "p_vagas" integer, "p_tokens_in" integer, "p_tokens_out" integer, "p_tempo_medio" integer, "p_confianca" numeric, "p_custo" numeric) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."incrementar_metricas_grupo"("p_data" "date", "p_grupo_id" "uuid", "p_mensagens" integer, "p_vagas" integer, "p_tokens_in" integer, "p_tokens_out" integer, "p_tempo_medio" integer, "p_confianca" numeric, "p_custo" numeric) TO "service_role";



REVOKE ALL ON FUNCTION "public"."incrementar_vezes_usado"("p_tabela" "text", "p_alias_normalizado" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."incrementar_vezes_usado"("p_tabela" "text", "p_alias_normalizado" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."inserir_intent_se_novo"("p_fingerprint" "text", "p_cliente_id" "uuid", "p_intent_type" "text", "p_reference_id" "uuid", "p_expires_at" timestamp with time zone) TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "service_role";



REVOKE ALL ON FUNCTION "public"."log_clientes_changes"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."log_clientes_changes"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."marcar_vaga_realizada"("p_vaga_id" "uuid", "p_realizada_por" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."marcar_vaga_realizada"("p_vaga_id" "uuid", "p_realizada_por" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."normalizar_alias"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."normalizar_alias"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."reconcile_all"("p_hours" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reconcile_all"("p_hours" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."reconcile_db_to_events"("p_start" timestamp with time zone, "p_end" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reconcile_db_to_events"("p_start" timestamp with time zone, "p_end" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."reconcile_events_to_db"("p_start" timestamp with time zone, "p_end" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reconcile_events_to_db"("p_start" timestamp with time zone, "p_end" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."registrar_alias_especialidade"("p_especialidade_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."registrar_alias_especialidade"("p_especialidade_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) TO "service_role";



REVOKE ALL ON FUNCTION "public"."registrar_alias_hospital"("p_hospital_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."registrar_alias_hospital"("p_hospital_id" "uuid", "p_alias" "text", "p_origem" "text", "p_confianca" double precision) TO "service_role";



REVOKE ALL ON FUNCTION "public"."registrar_primeira_mensagem_grupo"("p_grupo_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."registrar_primeira_mensagem_grupo"("p_grupo_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "postgres";
GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "anon";
GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_limit"(real) TO "service_role";



GRANT ALL ON FUNCTION "public"."show_limit"() TO "postgres";
GRANT ALL ON FUNCTION "public"."show_limit"() TO "anon";
GRANT ALL ON FUNCTION "public"."show_limit"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."show_limit"() TO "service_role";



GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "postgres";
GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "anon";
GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."show_trgm"("text") TO "service_role";



GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."similarity"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."similarity_dist"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."similarity_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



REVOKE ALL ON FUNCTION "public"."stats_vagas_grupo"("data_inicio" "date") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."stats_vagas_grupo"("data_inicio" "date") TO "service_role";



REVOKE ALL ON FUNCTION "public"."status_fila_grupos"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."status_fila_grupos"() TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_dist_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."strict_word_similarity_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."sync_cliente_to_bitrix"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."sync_cliente_to_bitrix"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."top_grupos_vagas"("data_inicio" "date", "limite" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."top_grupos_vagas"("data_inicio" "date", "limite" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."unaccent"("text") TO "postgres";
GRANT ALL ON FUNCTION "public"."unaccent"("text") TO "anon";
GRANT ALL ON FUNCTION "public"."unaccent"("text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."unaccent"("text") TO "service_role";



GRANT ALL ON FUNCTION "public"."unaccent"("regdictionary", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."unaccent"("regdictionary", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."unaccent"("regdictionary", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."unaccent"("regdictionary", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."unaccent_init"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."unaccent_init"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."unaccent_init"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."unaccent_init"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."unaccent_lexize"("internal", "internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."unaccent_lexize"("internal", "internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."unaccent_lexize"("internal", "internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."unaccent_lexize"("internal", "internal", "internal", "internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."update_app_settings_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_conhecimento_updated_at"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_conhecimento_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_conversation_on_new_message"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_conversation_on_new_message"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_data_anomalies_updated_at"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_data_anomalies_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_doctor_state_updated_at"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_doctor_state_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_external_handoffs_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_fila_processamento_updated_at"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_fila_processamento_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_updated_at_column"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."validar_valor_vaga"() TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_commutator_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_dist_op"("text", "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "postgres";
GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "anon";
GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."word_similarity_op"("text", "text") TO "service_role";












GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "service_role";









GRANT ALL ON TABLE "public"."app_settings" TO "service_role";



GRANT ALL ON TABLE "public"."avaliacoes_qualidade" TO "service_role";



GRANT ALL ON TABLE "public"."briefing_config" TO "service_role";



GRANT ALL ON TABLE "public"."briefing_historico" TO "service_role";



GRANT ALL ON TABLE "public"."briefing_sync_log" TO "service_role";



GRANT ALL ON TABLE "public"."briefings_pendentes" TO "service_role";



GRANT ALL ON TABLE "public"."business_alerts" TO "service_role";



GRANT ALL ON TABLE "public"."business_events" TO "service_role";



GRANT ALL ON TABLE "public"."campaign_contact_history" TO "service_role";



GRANT ALL ON TABLE "public"."envios" TO "service_role";



GRANT ALL ON TABLE "public"."fila_mensagens" TO "service_role";



GRANT ALL ON TABLE "public"."campaign_sends_raw" TO "service_role";



GRANT ALL ON TABLE "public"."campaign_sends" TO "service_role";



GRANT ALL ON TABLE "public"."campaign_metrics" TO "service_role";



GRANT ALL ON TABLE "public"."campanhas" TO "service_role";



GRANT ALL ON SEQUENCE "public"."campanhas_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."clientes" TO "service_role";



GRANT ALL ON TABLE "public"."clientes_log" TO "service_role";



GRANT ALL ON SEQUENCE "public"."clientes_log_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."conhecimento_julia" TO "service_role";



GRANT ALL ON TABLE "public"."contatos_grupo" TO "service_role";



GRANT ALL ON TABLE "public"."conversations" TO "service_role";



GRANT ALL ON TABLE "public"."data_anomalies" TO "service_role";



GRANT ALL ON TABLE "public"."diretrizes" TO "service_role";



GRANT ALL ON TABLE "public"."doctor_context" TO "service_role";



GRANT ALL ON TABLE "public"."doctor_state" TO "service_role";



GRANT ALL ON SEQUENCE "public"."envios_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."especialidades" TO "service_role";



GRANT ALL ON TABLE "public"."especialidades_alias" TO "service_role";



GRANT ALL ON TABLE "public"."execucoes_campanhas" TO "service_role";



GRANT ALL ON SEQUENCE "public"."execucoes_campanhas_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."external_contacts" TO "service_role";



GRANT ALL ON TABLE "public"."external_handoffs" TO "service_role";



GRANT ALL ON TABLE "public"."feature_flags" TO "service_role";



GRANT ALL ON TABLE "public"."feedbacks_gestor" TO "service_role";



GRANT ALL ON TABLE "public"."fila_processamento_grupos" TO "service_role";



GRANT ALL ON TABLE "public"."formas_recebimento" TO "service_role";



GRANT ALL ON TABLE "public"."interacoes" TO "service_role";



GRANT ALL ON TABLE "public"."funil_conversao" TO "service_role";



GRANT ALL ON TABLE "public"."grupos_whatsapp" TO "service_role";



GRANT ALL ON TABLE "public"."handoff_used_tokens" TO "service_role";



GRANT ALL ON TABLE "public"."handoffs" TO "service_role";



GRANT ALL ON TABLE "public"."hospitais" TO "service_role";



GRANT ALL ON TABLE "public"."hospitais_alias" TO "service_role";



GRANT ALL ON TABLE "public"."intent_log" TO "service_role";



GRANT ALL ON SEQUENCE "public"."interacoes_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."julia_status" TO "service_role";



GRANT ALL ON TABLE "public"."julia_status_atual" TO "service_role";



GRANT ALL ON TABLE "public"."medicos_travados" TO "service_role";



GRANT ALL ON TABLE "public"."mensagens_fora_horario" TO "service_role";



GRANT ALL ON TABLE "public"."mensagens_grupo" TO "service_role";



GRANT ALL ON TABLE "public"."metricas_campanhas" TO "service_role";



GRANT ALL ON SEQUENCE "public"."metricas_campanhas_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."metricas_conversa" TO "service_role";



GRANT ALL ON TABLE "public"."metricas_deteccao_bot" TO "service_role";



GRANT ALL ON TABLE "public"."metricas_grupos_diarias" TO "service_role";



GRANT ALL ON TABLE "public"."metricas_pipeline_diarias" TO "service_role";



GRANT ALL ON TABLE "public"."notificacoes_gestor" TO "service_role";



GRANT ALL ON TABLE "public"."outbound_dedupe" TO "service_role";



GRANT ALL ON TABLE "public"."periodos" TO "service_role";



GRANT ALL ON TABLE "public"."policy_events" TO "service_role";



GRANT ALL ON TABLE "public"."prompts" TO "service_role";



GRANT ALL ON TABLE "public"."prompts_historico" TO "service_role";



GRANT ALL ON TABLE "public"."report_schedule" TO "service_role";



GRANT ALL ON TABLE "public"."reports" TO "service_role";



GRANT ALL ON TABLE "public"."setores" TO "service_role";



GRANT ALL ON TABLE "public"."slack_comandos" TO "service_role";



GRANT ALL ON TABLE "public"."slack_sessoes" TO "service_role";



GRANT ALL ON TABLE "public"."sugestoes_prompt" TO "service_role";



GRANT ALL ON TABLE "public"."timeline_medico" TO "service_role";



GRANT ALL ON TABLE "public"."tipos_vaga" TO "service_role";



GRANT ALL ON TABLE "public"."touch_reconciliation_log" TO "service_role";



GRANT ALL ON TABLE "public"."v_conversations_list" TO "service_role";



GRANT ALL ON TABLE "public"."vagas" TO "service_role";



GRANT ALL ON TABLE "public"."vagas_disponiveis" TO "service_role";



GRANT ALL ON TABLE "public"."vagas_grupo" TO "service_role";



GRANT ALL ON TABLE "public"."vagas_grupo_fontes" TO "service_role";



GRANT ALL ON TABLE "public"."whatsapp_instances" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































