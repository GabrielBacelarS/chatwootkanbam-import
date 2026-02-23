-- Adiciona coluna product_keywords na tabela ai_config
-- Execute este script no banco de dados PostgreSQL
-- Esta coluna permite configurar palavras-chave por tipo de negocio

-- Adicionar coluna (com valor padrao generico)
ALTER TABLE ai_config
ADD COLUMN IF NOT EXISTS product_keywords TEXT[] DEFAULT ARRAY[
    'produto', 'produtos', 'estoque', 'disponivel', 'disponiveis',
    'tem', 'temos', 'quais', 'preco', 'precos', 'quanto', 'valor',
    'valores', 'opcao', 'opcoes', 'ver', 'mostrar', 'conhecer', 'saber'
];

-- Comentario explicativo
COMMENT ON COLUMN ai_config.product_keywords IS 'Keywords que forcam uso de tools. Configure por tipo de negocio: veiculos, ar condicionado, roupas, etc.';
