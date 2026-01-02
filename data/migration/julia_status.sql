--
-- PostgreSQL database dump
--

\restrict zqPVq6eTCWSIKafhRqogifThf8vt7QZbNhExNvBtIymUhNkBwffo4UkUNn06xSf

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
-- Data for Name: julia_status; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.julia_status (id, status, motivo, detalhes, alterado_por, alterado_via, created_at) VALUES ('952c12ac-c9f8-4653-b583-c25528df755b', 'ativo', 'Deploy Railway completo - ativando para teste', NULL, NULL, 'manual', '2025-12-30 19:00:26.394885+00') ON CONFLICT DO NOTHING;


--
-- PostgreSQL database dump complete
--

\unrestrict zqPVq6eTCWSIKafhRqogifThf8vt7QZbNhExNvBtIymUhNkBwffo4UkUNn06xSf

