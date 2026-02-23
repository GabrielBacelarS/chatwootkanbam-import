# Closefy - Sistema de Integração Chatwoot

Sistema completo de integração com Chatwoot incluindo:
- **IA Conversacional** com OpenAI/Gemini
- **RAG** (Retrieval Augmented Generation) com base de conhecimento de produtos
- **Kanban** de conversas
- **Disparador** de mensagens em massa
- **Round-robin** para distribuição de atendimentos

## Estrutura do Projeto

```
closefy-kanban-import/
├── backend/              # API FastAPI (Python)
│   ├── api/routes/       # Endpoints da API
│   ├── core/             # Configurações e database
│   ├── models/           # Modelos SQLAlchemy
│   ├── services/         # Serviços (IA, Chatwoot, MinIO, RAG)
│   ├── tasks/            # Background tasks (Celery)
│   └── main.py           # Entrada da aplicação
├── frontend/             # Interface Vue.js + PrimeVue
│   ├── src/
│   │   ├── views/        # Páginas
│   │   ├── api/          # Cliente HTTP
│   │   └── styles/       # Estilos
│   └── package.json
├── docker/               # Configurações Docker
│   ├── Dockerfile        # Build da aplicação
│   ├── docker-compose.yml      # Produção
│   └── docker-compose.dev.yml  # Desenvolvimento
├── docs/                 # Documentação e exemplos
└── requirements.txt      # Dependências Python
```

## Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- MinIO (para armazenamento de arquivos)

## Instalação

### 1. Clone e configure

```bash
git clone <repo>
cd closefy-kanban-import
cp .env.example .env
# Edite .env com suas configurações
```

### 2. Inicie os serviços (Docker)

```bash
# Desenvolvimento (apenas DB, Redis e MinIO)
docker-compose -f docker/docker-compose.dev.yml up -d

# Produção (todos os serviços)
docker-compose -f docker/docker-compose.yml up -d
```

### 3. Backend (Python)

```bash
pip install -r requirements.txt
python run.py
# ou
uvicorn backend.main:app --reload --port 3000
```

### 4. Frontend (Vue)

```bash
cd frontend
npm install --include=dev
npm run dev
```

## Acessos

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:3000 |
| API Docs | http://localhost:3000/docs |
| MinIO Console | http://localhost:9001 |

## Funcionalidades

### IA Conversacional
- Integração com OpenAI (GPT-4) e Google Gemini
- Histórico de conversas persistente
- Base de conhecimento customizável
- Transcrição de áudio (Whisper)
- Quebra inteligente de mensagens

### RAG de Produtos
- Cadastro de produtos com imagens
- Embeddings para busca semântica
- Integração automática com respostas da IA

### Kanban
- Visualização de conversas por status
- Integração em tempo real com Chatwoot

### Disparador
- Envio de mensagens em massa
- Upload de planilha de contatos
- Intervalo configurável entre envios
- Round-robin para distribuição

## Licença

Proprietário - STG Digital
