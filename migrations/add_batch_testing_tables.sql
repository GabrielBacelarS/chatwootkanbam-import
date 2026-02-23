-- Migracao: Tabelas para testes em lote de agentes IA
-- Execute: docker exec -i docker-closefy_db-1 psql -U closefy -d closefydb -f migrations/add_batch_testing_tables.sql

-- Casos de teste
CREATE TABLE IF NOT EXISTS ai_test_cases (
    id SERIAL PRIMARY KEY,
    client_slug VARCHAR(100) REFERENCES clients(slug) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    input_message TEXT NOT NULL,
    expected_tools VARCHAR[] DEFAULT '{}',
    expected_keywords VARCHAR[] DEFAULT '{}',
    should_not_contain VARCHAR[] DEFAULT '{}',
    expected_tool_args JSONB,
    weight_tools INTEGER DEFAULT 10,
    weight_keywords INTEGER DEFAULT 10,
    weight_no_errors INTEGER DEFAULT 10,
    weight_quality INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_test_cases_client ON ai_test_cases(client_slug);
CREATE INDEX IF NOT EXISTS idx_test_cases_category ON ai_test_cases(category);
CREATE INDEX IF NOT EXISTS idx_test_cases_active ON ai_test_cases(client_slug, is_active);

-- Execucoes de testes
CREATE TABLE IF NOT EXISTS ai_test_runs (
    id SERIAL PRIMARY KEY,
    client_slug VARCHAR(100) REFERENCES clients(slug) ON DELETE CASCADE,
    concurrent_tests INTEGER,
    total_tests INTEGER,
    status VARCHAR(20) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    passed_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    average_score FLOAT,
    total_execution_time_ms INTEGER,
    total_tokens_used INTEGER,
    estimated_cost FLOAT
);

CREATE INDEX IF NOT EXISTS idx_test_runs_client ON ai_test_runs(client_slug);
CREATE INDEX IF NOT EXISTS idx_test_runs_status ON ai_test_runs(status);

-- Resultados individuais
CREATE TABLE IF NOT EXISTS ai_test_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES ai_test_runs(id) ON DELETE CASCADE,
    test_case_id INTEGER REFERENCES ai_test_cases(id) ON DELETE CASCADE,
    ai_response TEXT,
    tools_used VARCHAR[] DEFAULT '{}',
    execution_time_ms INTEGER,
    score FLOAT,
    score_breakdown JSONB,
    issues VARCHAR[] DEFAULT '{}',
    tokens_input INTEGER,
    tokens_output INTEGER
);

CREATE INDEX IF NOT EXISTS idx_test_results_run ON ai_test_results(run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_case ON ai_test_results(test_case_id);

SELECT 'Tabelas de batch testing criadas com sucesso!' as resultado;
