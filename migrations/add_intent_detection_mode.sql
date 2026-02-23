-- Migracao: Adicionar campo intent_detection_mode na tabela ai_config
-- Data: 2026-02-19
-- Descricao: Adiciona modo de deteccao de intencao (keywords, auto, always)

-- Adicionar coluna intent_detection_mode (se nao existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_config' AND column_name = 'intent_detection_mode'
    ) THEN
        ALTER TABLE ai_config ADD COLUMN intent_detection_mode VARCHAR(20) DEFAULT 'keywords';
    END IF;
END $$;

-- Atualizar registros existentes para usar 'keywords' como padrao (comportamento anterior)
UPDATE ai_config SET intent_detection_mode = 'keywords' WHERE intent_detection_mode IS NULL;

-- Comentario explicativo
COMMENT ON COLUMN ai_config.intent_detection_mode IS 'Modo de deteccao de intencao: keywords, auto, always';
