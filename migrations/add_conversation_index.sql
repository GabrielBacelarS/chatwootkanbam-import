-- Migração: Adicionar índice único em ai_conversations
-- Evita duplicatas de (client_slug, conversation_id)

-- Primeiro, remover possíveis duplicatas mantendo apenas o registro mais recente
DELETE FROM ai_conversations a
USING ai_conversations b
WHERE a.id < b.id
  AND a.client_slug = b.client_slug
  AND a.conversation_id = b.conversation_id;

-- Criar constraint única
ALTER TABLE ai_conversations
ADD CONSTRAINT uq_client_conversation UNIQUE (client_slug, conversation_id);

-- Criar índice para buscas rápidas
CREATE INDEX IF NOT EXISTS ix_ai_conversations_lookup
ON ai_conversations (client_slug, conversation_id);
