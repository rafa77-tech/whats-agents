-- Backup de índices removidos em 2026-02-09
-- Sprint 57 - Epic 4: Limpeza de Índices Não Utilizados
--
-- Estes índices foram removidos por terem 0 scans nas estatísticas.
-- Para restaurar, execute os comandos abaixo.

-- idx_clientes_estado (272 KB, 0 scans)
-- Motivo remoção: Coluna 'estado' raramente usada em WHERE
CREATE INDEX idx_clientes_estado ON public.clientes USING btree (estado);

-- idx_log_cliente_id (1.2 MB, 0 scans)
-- Motivo remoção: Tabela de log não é consultada frequentemente
CREATE INDEX idx_log_cliente_id ON public.clientes_log USING btree (cliente_id);

-- idx_log_timestamp (1.2 MB, 0 scans)
-- Motivo remoção: Tabela de log não é consultada frequentemente
CREATE INDEX idx_log_timestamp ON public.clientes_log USING btree ("timestamp" DESC);

-- idx_vagas_grupo_fontes_grupo (376 KB, 0 scans)
-- Motivo remoção: FK já indexada por outro índice ou não usada em queries
CREATE INDEX idx_vagas_grupo_fontes_grupo ON public.vagas_grupo_fontes USING btree (grupo_id);

-- idx_vagas_grupo_hospital (1.4 MB, 0 scans)
-- Motivo remoção: FK já coberta por outro índice
CREATE INDEX idx_vagas_grupo_hospital ON public.vagas_grupo USING btree (hospital_id);

-- Total economizado: ~4.4 MB
