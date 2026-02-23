-- Adiciona coluna use_agent_mode na tabela ai_config
-- Execute este script no banco de dados PostgreSQL

-- Adicionar coluna (com valor padrao TRUE para ativar o agente por padrao)
ALTER TABLE ai_config
ADD COLUMN IF NOT EXISTS use_agent_mode BOOLEAN DEFAULT TRUE;

-- Atualizar registros existentes para usar o agente
UPDATE ai_config SET use_agent_mode = TRUE WHERE use_agent_mode IS NULL;
