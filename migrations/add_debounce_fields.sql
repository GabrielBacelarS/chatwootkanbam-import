-- Migration: Adicionar campos para debounce de mensagens
-- Data: 2026-02-13

-- ========== TABELA ai_conversations ==========

-- Adicionar campo para mensagens pendentes (debounce)
ALTER TABLE ai_conversations
ADD COLUMN IF NOT EXISTS pending_messages JSONB DEFAULT '[]'::jsonb;

-- Adicionar campo para timestamp da ultima mensagem
ALTER TABLE ai_conversations
ADD COLUMN IF NOT EXISTS last_message_at DOUBLE PRECISION;

-- Criar indice para performance
CREATE INDEX IF NOT EXISTS idx_ai_conversations_last_message
ON ai_conversations(client_slug, conversation_id, last_message_at);

-- ========== TABELA ai_config ==========

-- Adicionar campo para tempo de debounce configuravel (padrao 10 segundos)
-- Permite que cada cliente defina quanto tempo esperar antes de responder
ALTER TABLE ai_config
ADD COLUMN IF NOT EXISTS debounce_seconds DOUBLE PRECISION DEFAULT 10.0;
