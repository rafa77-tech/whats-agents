--
-- PostgreSQL database dump
--

\restrict pcLXRVndXyrYILKgps0d7PkTCLrTs9prAvJ8tyARBfCaD7FzIzVW1ShPq08pvMg

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: diretrizes; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.diretrizes (id, tipo, conteudo, contexto, cliente_id, vaga_id, prioridade, origem, criado_por, ativo, expira_em, created_at, updated_at) VALUES ('b83cbba7-bd49-4ed6-9c3f-23fe70432fe5', 'foco_semana', 'Prioridade 1: Anestesistas da Grande São Paulo
Prioridade 2: Follow-up de médicos que não responderam', NULL, NULL, NULL, 10, 'google_docs', NULL, true, NULL, '2025-12-10 14:32:25.207457+00', '2025-12-17 00:00:02.807615+00') ON CONFLICT DO NOTHING;
INSERT INTO public.diretrizes (id, tipo, conteudo, contexto, cliente_id, vaga_id, prioridade, origem, criado_por, ativo, expira_em, created_at, updated_at) VALUES ('f6ac84e1-dccc-4cca-b4c9-a21b3ed79611', 'tom_semana', 'Ser objetiva e direta
Pode oferecer até 10% a mais se necessário', NULL, NULL, NULL, 9, 'google_docs', NULL, true, NULL, '2025-12-10 14:32:25.295664+00', '2025-12-17 00:00:02.924886+00') ON CONFLICT DO NOTHING;
INSERT INTO public.diretrizes (id, tipo, conteudo, contexto, cliente_id, vaga_id, prioridade, origem, criado_por, ativo, expira_em, created_at, updated_at) VALUES ('5bb6af10-5848-41e3-bb6b-b889c6755739', 'margem_negociacao', '10', NULL, NULL, NULL, 8, 'google_docs', NULL, true, NULL, '2025-12-10 14:32:25.710498+00', '2025-12-17 00:00:03.007121+00') ON CONFLICT DO NOTHING;
INSERT INTO public.diretrizes (id, tipo, conteudo, contexto, cliente_id, vaga_id, prioridade, origem, criado_por, ativo, expira_em, created_at, updated_at) VALUES ('fffd2fab-7d1b-4dba-8958-561789181c7e', 'observacoes', 'Semana de testes iniciais', NULL, NULL, NULL, 5, 'google_docs', NULL, true, NULL, '2025-12-10 14:32:25.787887+00', '2025-12-17 00:00:03.098064+00') ON CONFLICT DO NOTHING;


--
-- PostgreSQL database dump complete
--

\unrestrict pcLXRVndXyrYILKgps0d7PkTCLrTs9prAvJ8tyARBfCaD7FzIzVW1ShPq08pvMg

