-- Migracao: Adicionar campo split_mode na tabela ai_config
-- Data: 2026-02-19
-- Descricao: Adiciona opcoes de modo de quebra de mensagens

-- Adicionar coluna split_mode (se nao existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_config' AND column_name = 'split_mode'
    ) THEN
        ALTER TABLE ai_config ADD COLUMN split_mode VARCHAR(20) DEFAULT 'smart';
    END IF;
END $$;

-- Atualizar registros existentes para usar 'smart' como padrao
UPDATE ai_config SET split_mode = 'smart' WHERE split_mode IS NULL;

-- Comentario explicativo
COMMENT ON COLUMN ai_config.split_mode IS 'Modo de quebra de mensagens: none, paragraph, sentence, character, smart';
