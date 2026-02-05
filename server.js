const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const pgSession = require('connect-pg-simple')(session);

const app = express();
const PORT = process.env.PORT || 3000;
const VERSION = 'v7';

// ========================================
// SISTEMA DE LOGS
// ========================================
function log(type, message, details = '') {
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const icons = {
        'info': 'ℹ️',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'api': '🔄',
        'db': '🗄️',
        'auth': '🔐',
        'import': '📥'
    };
    const icon = icons[type] || '📋';
    console.log(`[${timestamp}] ${icon} ${message}${details ? ' | ' + details : ''}`);
}

log('info', `Iniciando Closefy Kanban Importer ${VERSION}`);

// Arquivo de dados dos clientes (fallback local)
const DATA_FILE = path.join(__dirname, 'clients.json');

// Credenciais do admin (usar variáveis de ambiente em produção)
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || 'gbacelar099@gmail.com';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'gABRIEL1!';

// ========================================
// CONFIGURAÇÃO DO POSTGRESQL
// ========================================
let pool = null;
let usePostgres = false;

if (process.env.DATABASE_URL) {
    pool = new Pool({
        connectionString: process.env.DATABASE_URL,
        ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    });
    usePostgres = true;
    log('db', 'Conectando ao PostgreSQL');
} else {
    log('db', 'Usando arquivo JSON local');
}

// Inicializar tabela no PostgreSQL
async function initDatabase() {
    if (!usePostgres) return;

    try {
        await pool.query(`
            CREATE TABLE IF NOT EXISTS clients (
                slug VARCHAR(100) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                api_url VARCHAR(500) NOT NULL,
                account_id VARCHAR(50) NOT NULL,
                api_token VARCHAR(500) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        `);
        log('db', 'Tabela clients criada/verificada');
    } catch (error) {
        log('error', 'Erro ao criar tabela', error.message);
    }
}

// ========================================
// FUNÇÕES DE DADOS (PostgreSQL + JSON fallback)
// ========================================
async function loadClients() {
    if (usePostgres) {
        try {
            const result = await pool.query('SELECT * FROM clients ORDER BY name');
            const clients = {};
            result.rows.forEach(row => {
                clients[row.slug] = {
                    name: row.name,
                    apiUrl: row.api_url,
                    accountId: row.account_id,
                    apiToken: row.api_token,
                    createdAt: row.created_at,
                    updatedAt: row.updated_at
                };
            });
            return clients;
        } catch (error) {
            console.error('Erro ao carregar clients do PostgreSQL:', error);
            return {};
        }
    } else {
        try {
            if (fs.existsSync(DATA_FILE)) {
                return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
            }
        } catch (e) {
            console.error('Erro ao carregar clients:', e);
        }
        return {};
    }
}

async function saveClient(slug, clientData) {
    if (usePostgres) {
        try {
            await pool.query(`
                INSERT INTO clients (slug, name, api_url, account_id, api_token, updated_at)
                VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    api_url = EXCLUDED.api_url,
                    account_id = EXCLUDED.account_id,
                    api_token = EXCLUDED.api_token,
                    updated_at = CURRENT_TIMESTAMP
            `, [slug, clientData.name, clientData.apiUrl, clientData.accountId, clientData.apiToken]);
        } catch (error) {
            console.error('Erro ao salvar client no PostgreSQL:', error);
            throw error;
        }
    } else {
        const clients = await loadClients();
        clients[slug] = {
            ...clientData,
            createdAt: clients[slug]?.createdAt || new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        fs.writeFileSync(DATA_FILE, JSON.stringify(clients, null, 2));
    }
}

async function deleteClient(slug) {
    if (usePostgres) {
        try {
            await pool.query('DELETE FROM clients WHERE slug = $1', [slug]);
        } catch (error) {
            console.error('Erro ao deletar client do PostgreSQL:', error);
            throw error;
        }
    } else {
        const clients = await loadClients();
        delete clients[slug];
        fs.writeFileSync(DATA_FILE, JSON.stringify(clients, null, 2));
    }
}

async function renameClientSlug(oldSlug, newSlug, clientData) {
    if (usePostgres) {
        try {
            await pool.query('DELETE FROM clients WHERE slug = $1', [oldSlug]);
            await saveClient(newSlug, clientData);
        } catch (error) {
            console.error('Erro ao renomear client no PostgreSQL:', error);
            throw error;
        }
    } else {
        const clients = await loadClients();
        delete clients[oldSlug];
        clients[newSlug] = {
            ...clientData,
            updatedAt: new Date().toISOString()
        };
        fs.writeFileSync(DATA_FILE, JSON.stringify(clients, null, 2));
    }
}

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
// Configuração de sessão (usa PostgreSQL em produção)
const sessionConfig = {
    secret: process.env.SESSION_SECRET || 'chatwoot-importer-secret-key-2024',
    resave: false,
    saveUninitialized: false,
    cookie: {
        maxAge: 24 * 60 * 60 * 1000,
        secure: false // Ajuste para true se usar HTTPS
    }
};

// Usa PostgreSQL para sessões em produção
if (usePostgres) {
    sessionConfig.store = new pgSession({
        pool: pool,
        tableName: 'user_sessions',
        createTableIfMissing: true
    });
    log('db', 'Sessões armazenadas no PostgreSQL');
}

app.use(session(sessionConfig));

// Headers para permitir iframe
app.use((req, res, next) => {
    res.setHeader('X-Frame-Options', 'ALLOWALL');
    res.setHeader('Content-Security-Policy', "frame-ancestors *");
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, api_access_token');
    if (req.method === 'OPTIONS') {
        return res.sendStatus(200);
    }
    next();
});

// Servir arquivos estáticos
app.use('/static', express.static(__dirname));

// ========================================
// MIDDLEWARE DE AUTENTICAÇÃO
// ========================================
function requireAdmin(req, res, next) {
    if (req.session && req.session.isAdmin) {
        next();
    } else {
        res.redirect('/admin/login');
    }
}

// ========================================
// HEALTH CHECK (importante para Railway/EasyPanel)
// ========================================
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ========================================
// ROTAS DE ADMIN
// ========================================

// Página de login
app.get('/admin/login', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 min-h-screen flex items-center justify-center">
    <div class="bg-gray-800 p-8 rounded-xl shadow-2xl w-full max-w-md">
        <div class="text-center mb-8">
            <div class="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-white">Painel Admin</h1>
            <p class="text-gray-400">Importador de Contatos <span class="text-xs bg-blue-500 px-2 py-0.5 rounded">${VERSION}</span></p>
        </div>

        ${req.query.error ? '<div class="bg-red-500/20 border border-red-500 text-red-400 p-3 rounded-lg mb-4 text-center">Email ou senha incorretos</div>' : ''}

        <form method="POST" action="/admin/login" class="space-y-4">
            <div>
                <label class="block text-gray-400 text-sm mb-1">Email</label>
                <input type="email" name="email" required
                    class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="seu@email.com">
            </div>
            <div>
                <label class="block text-gray-400 text-sm mb-1">Senha</label>
                <input type="password" name="password" required
                    class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="••••••••">
            </div>
            <button type="submit"
                class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg transition duration-200">
                Entrar
            </button>
        </form>
    </div>
</body>
</html>
    `);
});

// Processar login
app.post('/admin/login', (req, res) => {
    const { email, password } = req.body;
    if (email === ADMIN_EMAIL && password === ADMIN_PASSWORD) {
        req.session.isAdmin = true;
        log('auth', 'Login realizado com sucesso', email);
        res.redirect('/admin');
    } else {
        log('warning', 'Tentativa de login falhou', email);
        res.redirect('/admin/login?error=1');
    }
});

// Logout
app.get('/admin/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/admin/login');
});

// Painel Admin Principal
app.get('/admin', requireAdmin, async (req, res) => {
    const clients = await loadClients();
    const clientsList = Object.entries(clients).map(([slug, data]) => `
        <tr class="border-b border-gray-700 hover:bg-gray-750">
            <td class="px-6 py-4">
                <div class="font-medium text-white">${data.name}</div>
                <div class="text-sm text-gray-400">/${slug}</div>
            </td>
            <td class="px-6 py-4 text-gray-300">${data.apiUrl}</td>
            <td class="px-6 py-4 text-gray-300">${data.accountId}</td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs rounded-full ${data.apiToken ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}">
                    ${data.apiToken ? 'Configurado' : 'Pendente'}
                </span>
            </td>
            <td class="px-6 py-4">
                <div class="flex gap-2">
                    <a href="/admin/edit/${slug}" class="text-blue-400 hover:text-blue-300">Editar</a>
                    <a href="/${slug}" target="_blank" class="text-green-400 hover:text-green-300">Abrir</a>
                    <button onclick="deleteClient('${slug}')" class="text-red-400 hover:text-red-300">Excluir</button>
                </div>
            </td>
        </tr>
    `).join('');

    const dbStatus = usePostgres ?
        '<span class="text-green-400">PostgreSQL</span>' :
        '<span class="text-yellow-400">JSON Local</span>';

    res.send(`
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - Importador de Contatos</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 min-h-screen">
    <nav class="bg-gray-800 border-b border-gray-700">
        <div class="container mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                    </svg>
                </div>
                <div>
                    <h1 class="text-xl font-bold text-white">Painel Admin <span class="text-xs bg-blue-500 text-white px-2 py-1 rounded-full ml-2">${VERSION}</span></h1>
                    <p class="text-sm text-gray-400">Gerenciar Clientes | DB: ${dbStatus}</p>
                </div>
            </div>
            <a href="/admin/logout" class="text-gray-400 hover:text-white flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                </svg>
                Sair
            </a>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-8">
        <!-- Stats -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                        </svg>
                    </div>
                    <div>
                        <p class="text-3xl font-bold text-white">${Object.keys(clients).length}</p>
                        <p class="text-gray-400">Clientes</p>
                    </div>
                </div>
            </div>
            <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <div>
                        <p class="text-3xl font-bold text-white">${Object.values(clients).filter(c => c.apiToken).length}</p>
                        <p class="text-gray-400">Configurados</p>
                    </div>
                </div>
            </div>
            <div class="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                        </svg>
                    </div>
                    <div>
                        <p class="text-sm font-mono text-white break-all">${req.headers.host}</p>
                        <p class="text-gray-400">URL Base</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-xl font-bold text-white">Clientes Cadastrados</h2>
            <a href="/admin/new" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
                Novo Cliente
            </a>
        </div>

        <!-- Tabela -->
        <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <table class="w-full">
                <thead class="bg-gray-750">
                    <tr class="border-b border-gray-700">
                        <th class="px-6 py-4 text-left text-sm font-medium text-gray-400">Cliente</th>
                        <th class="px-6 py-4 text-left text-sm font-medium text-gray-400">URL Chatwoot</th>
                        <th class="px-6 py-4 text-left text-sm font-medium text-gray-400">Account ID</th>
                        <th class="px-6 py-4 text-left text-sm font-medium text-gray-400">Status</th>
                        <th class="px-6 py-4 text-left text-sm font-medium text-gray-400">Ações</th>
                    </tr>
                </thead>
                <tbody>
                    ${clientsList || '<tr><td colspan="5" class="px-6 py-8 text-center text-gray-500">Nenhum cliente cadastrado</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function deleteClient(slug) {
            if (confirm('Tem certeza que deseja excluir este cliente?')) {
                fetch('/admin/delete/' + slug, { method: 'POST' })
                    .then(() => window.location.reload());
            }
        }
    </script>
</body>
</html>
    `);
});

// Novo Cliente
app.get('/admin/new', requireAdmin, (req, res) => {
    res.send(getClientForm());
});

// Editar Cliente
app.get('/admin/edit/:slug', requireAdmin, async (req, res) => {
    const clients = await loadClients();
    const client = clients[req.params.slug];
    if (!client) {
        return res.redirect('/admin');
    }
    res.send(getClientForm(req.params.slug, client));
});

// Salvar Cliente
app.post('/admin/save', requireAdmin, async (req, res) => {
    const { originalSlug, slug, name, apiUrl, accountId, apiToken } = req.body;

    const clientData = {
        name,
        apiUrl: apiUrl.replace(/\/$/, ''),
        accountId,
        apiToken
    };

    // Se mudou o slug, remove o antigo
    if (originalSlug && originalSlug !== slug) {
        await renameClientSlug(originalSlug, slug, clientData);
        log('info', 'Cliente renomeado', `${originalSlug} -> ${slug}`);
    } else {
        await saveClient(slug, clientData);
        log('success', 'Cliente salvo', `${slug} (${name})`);
    }

    res.redirect('/admin');
});

// Deletar Cliente
app.post('/admin/delete/:slug', requireAdmin, async (req, res) => {
    await deleteClient(req.params.slug);
    log('warning', 'Cliente deletado', req.params.slug);
    res.json({ success: true });
});

// Formulário de Cliente
function getClientForm(slug = '', client = {}) {
    return `
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${slug ? 'Editar' : 'Novo'} Cliente - Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 min-h-screen">
    <nav class="bg-gray-800 border-b border-gray-700">
        <div class="container mx-auto px-4 py-4">
            <a href="/admin" class="text-gray-400 hover:text-white flex items-center gap-2 w-fit">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
                </svg>
                Voltar
            </a>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-8 max-w-2xl">
        <div class="bg-gray-800 rounded-xl p-8 border border-gray-700">
            <h1 class="text-2xl font-bold text-white mb-6">${slug ? 'Editar' : 'Novo'} Cliente</h1>

            <form method="POST" action="/admin/save" class="space-y-6">
                <input type="hidden" name="originalSlug" value="${slug}">

                <div>
                    <label class="block text-gray-400 text-sm mb-2">Nome do Cliente</label>
                    <input type="text" name="name" value="${client.name || ''}" required
                        class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                        placeholder="Ex: Balboa">
                </div>

                <div>
                    <label class="block text-gray-400 text-sm mb-2">Slug (URL)</label>
                    <div class="flex items-center gap-2">
                        <span class="text-gray-500">/</span>
                        <input type="text" name="slug" value="${slug}" required pattern="[a-z0-9-]+"
                            class="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                            placeholder="balboa">
                    </div>
                    <p class="text-xs text-gray-500 mt-1">Apenas letras minúsculas, números e hífens</p>
                </div>

                <div>
                    <label class="block text-gray-400 text-sm mb-2">URL do Chatwoot</label>
                    <input type="url" name="apiUrl" value="${client.apiUrl || ''}" required
                        class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                        placeholder="https://chat.empresa.com">
                </div>

                <div>
                    <label class="block text-gray-400 text-sm mb-2">Account ID</label>
                    <input type="number" name="accountId" value="${client.accountId || ''}" required
                        class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                        placeholder="1">
                </div>

                <div>
                    <label class="block text-gray-400 text-sm mb-2">API Access Token</label>
                    <input type="text" name="apiToken" value="${client.apiToken || ''}" required
                        class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:ring-2 focus:ring-blue-500"
                        placeholder="Token de acesso da API">
                    <p class="text-xs text-gray-500 mt-1">Encontre em: Chatwoot → Perfil → Access Token</p>
                </div>

                <div class="flex gap-4 pt-4">
                    <a href="/admin" class="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-medium py-3 rounded-lg transition text-center">
                        Cancelar
                    </a>
                    <button type="submit" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg transition">
                        Salvar
                    </button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
    `;
}

// ========================================
// ROTA DO CLIENTE (IMPORTADOR)
// ========================================
app.get('/:slug', async (req, res) => {
    const clients = await loadClients();
    const client = clients[req.params.slug];

    if (!client) {
        return res.status(404).send(`
<!DOCTYPE html>
<html>
<head>
    <title>Cliente não encontrado</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 min-h-screen flex items-center justify-center">
    <div class="text-center">
        <h1 class="text-6xl font-bold text-gray-700 mb-4">404</h1>
        <p class="text-gray-400 text-xl">Cliente não encontrado</p>
        <a href="/admin" class="text-blue-400 hover:text-blue-300 mt-4 inline-block">Ir para Admin</a>
    </div>
</body>
</html>
        `);
    }

    // Ler o index.html e injetar as configurações
    let html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

    // Injetar configurações do cliente
    const configScript = `
    <script>
        window.CLIENT_CONFIG = {
            name: "${client.name}",
            apiUrl: "${client.apiUrl}",
            accountId: "${client.accountId}",
            apiToken: "${client.apiToken}"
        };
    </script>
    `;

    // Inserir antes do </head>
    html = html.replace('</head>', configScript + '</head>');

    res.send(html);
});

// ========================================
// PROXY API - RESOLVE CORS
// ========================================

// Proxy genérico para API do Chatwoot
app.all('/proxy/api/*', async (req, res) => {
    try {
        const { apiUrl, apiToken } = req.body._config || req.query;

        if (!apiUrl || !apiToken) {
            return res.status(400).json({ error: 'Missing apiUrl or apiToken' });
        }

        // Remove /proxy da URL
        const endpoint = req.path.replace('/proxy/api', '/api');
        const url = `${apiUrl}${endpoint}`;

        // Prepara o body (remove _config)
        let body = null;
        if (req.body && Object.keys(req.body).length > 0) {
            const { _config, ...rest } = req.body;
            if (Object.keys(rest).length > 0) {
                body = JSON.stringify(rest);
            }
        }

        // Faz a requisição para o Chatwoot
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: req.method,
            headers: {
                'api_access_token': apiToken,
                'Content-Type': 'application/json'
            },
            body: body
        });

        const data = await response.json();
        res.status(response.status).json(data);

    } catch (error) {
        log('error', 'Proxy error', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Proxy simplificado por slug do cliente
app.all('/api/:slug/*', async (req, res) => {
    try {
        const clients = await loadClients();
        const client = clients[req.params.slug];

        if (!client) {
            log('warning', 'Cliente não encontrado', req.params.slug);
            return res.status(404).json({ error: 'Cliente não encontrado' });
        }

        // Monta a URL da API do Chatwoot
        const endpoint = req.path.replace(`/api/${req.params.slug}`, '');
        const url = `${client.apiUrl}/api/v1/accounts/${client.accountId}${endpoint}`;

        log('api', `${req.method} ${endpoint}`, req.params.slug);

        // Prepara o body
        let body = null;
        if (req.body && Object.keys(req.body).length > 0) {
            body = JSON.stringify(req.body);
        }

        // Faz a requisição
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: req.method,
            headers: {
                'api_access_token': client.apiToken,
                'Content-Type': 'application/json'
            },
            body: body
        });

        const data = await response.json();
        res.status(response.status).json(data);

    } catch (error) {
        log('error', 'Proxy error', error.message);
        res.status(500).json({ error: error.message });
    }
});

// ========================================
// ROTA RAIZ
// ========================================
app.get('/', (req, res) => {
    res.redirect('/admin');
});

// ========================================
// INICIAR SERVIDOR
// ========================================
async function startServer() {
    await initDatabase();

    app.listen(PORT, '0.0.0.0', () => {
        console.log(`
╔═══════════════════════════════════════════════════════════╗
║   Closefy Kanban Importer ${VERSION}                          ║
╠═══════════════════════════════════════════════════════════╣
║   URL: http://localhost:${PORT}                              ║
║   Admin: http://localhost:${PORT}/admin                      ║
║   Health: http://localhost:${PORT}/health                    ║
║   Database: ${usePostgres ? 'PostgreSQL' : 'JSON Local'}                                    ║
╚═══════════════════════════════════════════════════════════╝
        `);
        log('success', `Servidor iniciado na porta ${PORT}`);
    });
}

startServer();
