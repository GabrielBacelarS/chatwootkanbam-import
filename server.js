const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const pgSession = require('connect-pg-simple')(session);
const multer = require('multer');
const FormDataLib = require('form-data');
const uploadMulter = multer({ storage: multer.memoryStorage(), limits: { fileSize: 40 * 1024 * 1024 } });

const app = express();
const PORT = process.env.PORT || 3000;
const VERSION = 'v8';

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
    const dbUrl = process.env.DATABASE_URL;
    const disableSSL = dbUrl.includes('sslmode=disable');
    pool = new Pool({
        connectionString: dbUrl,
        ssl: disableSSL ? false : (process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false)
    });
    usePostgres = true;
    log('db', 'Conectando ao PostgreSQL');
} else {
    log('db', 'Usando arquivo JSON local');
}

// Inicializar tabela no PostgreSQL (com retry para Swarm)
async function initDatabase() {
    if (!usePostgres) return;

    const maxRetries = 15;
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
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

            // Tabela de permissões de usuário
            await pool.query(`
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id SERIAL PRIMARY KEY,
                    client_slug VARCHAR(100) REFERENCES clients(slug) ON DELETE CASCADE,
                    chatwoot_user_id INTEGER NOT NULL,
                    user_name VARCHAR(255),
                    user_email VARCHAR(255),
                    user_role VARCHAR(50),
                    allowed_labels TEXT[],
                    allowed_boards TEXT[],
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(client_slug, chatwoot_user_id)
                )
            `);
            // Adicionar coluna allowed_boards se não existir (para bancos existentes)
            await pool.query(`
                ALTER TABLE user_permissions ADD COLUMN IF NOT EXISTS allowed_boards TEXT[] DEFAULT '{}'
            `);
            log('db', 'Tabela user_permissions criada/verificada');

            // Tabela de boards (Kanban)
            await pool.query(`
                CREATE TABLE IF NOT EXISTS kanban_boards (
                    id VARCHAR(100) PRIMARY KEY,
                    client_slug VARCHAR(100) REFERENCES clients(slug) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    columns JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);
            log('db', 'Tabela kanban_boards criada/verificada');
            return;
        } catch (error) {
            log('warning', `Tentativa ${attempt}/${maxRetries} - PostgreSQL não pronto`, error.message);
            if (attempt < maxRetries) {
                await new Promise(r => setTimeout(r, 3000));
            } else {
                log('error', 'PostgreSQL indisponível após todas tentativas, usando JSON local como fallback');
                usePostgres = false;
            }
        }
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

// ========================================
// FUNÇÕES DE PERMISSÕES DE USUÁRIO
// ========================================
async function getUserPermissions(clientSlug) {
    if (!usePostgres) return [];
    try {
        const result = await pool.query(
            'SELECT * FROM user_permissions WHERE client_slug = $1 ORDER BY user_name',
            [clientSlug]
        );
        return result.rows;
    } catch (error) {
        console.error('Erro ao carregar permissões:', error);
        return [];
    }
}

async function getUserPermission(clientSlug, chatwootUserId) {
    if (!usePostgres) return null;
    try {
        const result = await pool.query(
            'SELECT * FROM user_permissions WHERE client_slug = $1 AND chatwoot_user_id = $2',
            [clientSlug, chatwootUserId]
        );
        return result.rows[0] || null;
    } catch (error) {
        console.error('Erro ao carregar permissão:', error);
        return null;
    }
}

async function saveUserPermission(clientSlug, userData) {
    if (!usePostgres) return;
    try {
        await pool.query(`
            INSERT INTO user_permissions (client_slug, chatwoot_user_id, user_name, user_email, user_role, allowed_labels, allowed_boards, is_admin)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (client_slug, chatwoot_user_id)
            DO UPDATE SET user_name = $3, user_email = $4, user_role = $5, allowed_labels = $6, allowed_boards = $7, is_admin = $8, updated_at = CURRENT_TIMESTAMP
        `, [clientSlug, userData.chatwoot_user_id, userData.user_name, userData.user_email, userData.user_role, userData.allowed_labels || [], userData.allowed_boards || [], userData.is_admin || false]);
    } catch (error) {
        console.error('Erro ao salvar permissão:', error);
        throw error;
    }
}

async function deleteUserPermission(clientSlug, chatwootUserId) {
    if (!usePostgres) return;
    try {
        await pool.query(
            'DELETE FROM user_permissions WHERE client_slug = $1 AND chatwoot_user_id = $2',
            [clientSlug, chatwootUserId]
        );
    } catch (error) {
        console.error('Erro ao deletar permissão:', error);
        throw error;
    }
}

// ========================================
// FUNÇÕES DE BOARDS (Kanban)
// ========================================
async function getBoards(clientSlug) {
    if (!usePostgres) return [];
    try {
        const result = await pool.query(
            'SELECT * FROM kanban_boards WHERE client_slug = $1 ORDER BY created_at',
            [clientSlug]
        );
        return result.rows.map(row => ({
            id: row.id,
            name: row.name,
            columns: row.columns,
            createdAt: row.created_at
        }));
    } catch (error) {
        console.error('Erro ao carregar boards:', error);
        return [];
    }
}

async function getBoard(clientSlug, boardId) {
    if (!usePostgres) return null;
    try {
        const result = await pool.query(
            'SELECT * FROM kanban_boards WHERE client_slug = $1 AND id = $2',
            [clientSlug, boardId]
        );
        if (result.rows.length === 0) return null;
        const row = result.rows[0];
        return {
            id: row.id,
            name: row.name,
            columns: row.columns,
            createdAt: row.created_at
        };
    } catch (error) {
        console.error('Erro ao carregar board:', error);
        return null;
    }
}

async function saveBoard(clientSlug, board) {
    if (!usePostgres) return;
    try {
        await pool.query(`
            INSERT INTO kanban_boards (id, client_slug, name, columns, updated_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                columns = EXCLUDED.columns,
                updated_at = CURRENT_TIMESTAMP
        `, [board.id, clientSlug, board.name, JSON.stringify(board.columns)]);
    } catch (error) {
        console.error('Erro ao salvar board:', error);
        throw error;
    }
}

async function deleteBoard(clientSlug, boardId) {
    if (!usePostgres) return;
    try {
        await pool.query(
            'DELETE FROM kanban_boards WHERE client_slug = $1 AND id = $2',
            [clientSlug, boardId]
        );
    } catch (error) {
        console.error('Erro ao deletar board:', error);
        throw error;
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
                <div class="flex gap-2 items-center">
                    <a href="/admin/edit/${slug}" class="text-blue-400 hover:text-blue-300 text-sm">Editar</a>
                    <div class="relative inline-block" data-dropdown>
                        <button onclick="toggleDropdown(this)" class="bg-green-600 hover:bg-green-700 text-white text-sm px-3 py-1.5 rounded-lg flex items-center gap-1 transition">
                            Abrir
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                        </button>
                        <div class="dropdown-menu hidden absolute right-0 mt-1 w-48 bg-gray-700 rounded-lg shadow-xl border border-gray-600 z-50 overflow-hidden">
                            <a href="/${slug}" target="_blank" class="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-600 transition">
                                <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
                                Importação
                            </a>
                            <a href="/kanban/${slug}" target="_blank" class="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-600 transition">
                                <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7"/></svg>
                                Kanban
                            </a>
                            <a href="/disparador/${slug}" target="_blank" class="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-600 transition">
                                <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
                                Disparador
                            </a>
                            <div class="border-t border-gray-600"></div>
                            <a href="/admin/${slug}/usuarios" class="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-600 transition">
                                <svg class="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"/></svg>
                                Usuários
                            </a>
                        </div>
                    </div>
                    <button onclick="deleteClient('${slug}')" class="text-red-400 hover:text-red-300 text-sm">Excluir</button>
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
    <title>Admin - Importador de Contatos com Labels</title>
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
        <div class="bg-gray-800 rounded-xl border border-gray-700">
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
        function toggleDropdown(btn) {
            var menu = btn.nextElementSibling;
            document.querySelectorAll('.dropdown-menu').forEach(function(m) {
                if (m !== menu) m.classList.add('hidden');
            });
            menu.classList.toggle('hidden');
        }
        document.addEventListener('click', function(e) {
            if (!e.target.closest('[data-dropdown]')) {
                document.querySelectorAll('.dropdown-menu').forEach(function(m) {
                    m.classList.add('hidden');
                });
            }
        });
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
// GESTÃO DE USUÁRIOS E PERMISSÕES
// ========================================
app.get('/admin/:slug/usuarios', requireAdmin, async (req, res) => {
    const clients = await loadClients();
    const client = clients[req.params.slug];

    if (!client) {
        return res.redirect('/admin');
    }

    const permissions = await getUserPermissions(req.params.slug);

    res.send(`
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Usuários - ${client.name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>body { font-family: 'Inter', sans-serif; }</style>
</head>
<body class="bg-gray-900 min-h-screen">
    <nav class="bg-gray-800 border-b border-gray-700">
        <div class="container mx-auto px-4 py-4 flex justify-between items-center">
            <a href="/admin" class="text-gray-400 hover:text-white flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
                </svg>
                Voltar
            </a>
            <h1 class="text-white font-semibold">Usuários - ${client.name}</h1>
            <div></div>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-8">
        <div class="bg-gray-800 rounded-xl p-6 border border-gray-700 mb-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-white">Usuários do Chatwoot</h2>
                <button onclick="syncUsers()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Sincronizar do Chatwoot
                </button>
            </div>
            <p class="text-gray-400 text-sm">Clique em "Sincronizar" para carregar os usuários da conta Chatwoot e configurar suas permissões de acesso.</p>
        </div>

        <div id="usersContainer" class="grid gap-4">
            ${permissions.length === 0 ? `
                <div class="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
                    <svg class="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                    </svg>
                    <p class="text-gray-400">Nenhum usuário sincronizado ainda.</p>
                    <p class="text-gray-500 text-sm mt-2">Clique em "Sincronizar do Chatwoot" para carregar.</p>
                </div>
            ` : permissions.map(p => `
                <div class="bg-gray-800 rounded-xl p-4 border border-gray-700 flex items-center justify-between" data-user-id="${p.chatwoot_user_id}">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                            ${(p.user_name || 'U').charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <div class="text-white font-medium">${p.user_name || 'Sem nome'}</div>
                            <div class="text-gray-400 text-sm">${p.user_email || ''}</div>
                            <div class="flex items-center gap-2 mt-1">
                                <span class="px-2 py-0.5 text-xs rounded-full ${p.user_role === 'administrator' ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'}">
                                    ${p.user_role === 'administrator' ? 'Administrador' : 'Agente'}
                                </span>
                                ${p.is_admin ? '<span class="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400">Acesso Total</span>' : ''}
                            </div>
                        </div>
                    </div>
                    <button onclick="editPermissions(${p.chatwoot_user_id}, '${p.user_name}', ${JSON.stringify(p.allowed_labels || []).replace(/"/g, '&quot;')}, ${p.is_admin})"
                        class="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm">
                        Editar Permissões
                    </button>
                </div>
            `).join('')}
        </div>
    </div>

    <!-- Modal de Permissões -->
    <div id="permModal" class="fixed inset-0 bg-black/50 hidden items-center justify-center z-50">
        <div class="bg-gray-800 rounded-xl p-6 w-full max-w-lg mx-4 border border-gray-700">
            <h3 class="text-lg font-semibold text-white mb-4">Editar Permissões - <span id="modalUserName"></span></h3>

            <div class="mb-4">
                <label class="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" id="isAdminCheck" class="w-5 h-5 rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-500">
                    <span class="text-white">Acesso Total (Admin)</span>
                </label>
                <p class="text-gray-500 text-sm mt-1 ml-8">Pode ver todas as labels no Kanban e Disparador</p>
            </div>

            <div id="labelsSection">
                <label class="block text-gray-400 text-sm mb-2">Labels Permitidas</label>
                <div id="labelsList" class="space-y-2 max-h-60 overflow-y-auto bg-gray-900 rounded-lg p-3">
                    <p class="text-gray-500 text-sm">Carregando labels...</p>
                </div>
            </div>

            <div class="flex gap-3 mt-6">
                <button onclick="closeModal()" class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg">Cancelar</button>
                <button onclick="savePermissions()" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg">Salvar</button>
            </div>
        </div>
    </div>

    <script>
        const slug = '${req.params.slug}';
        let currentUserId = null;
        let allLabels = [];

        async function syncUsers() {
            try {
                const btn = event.target.closest('button');
                btn.disabled = true;
                btn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Sincronizando...';

                const res = await fetch('/admin/' + slug + '/usuarios/sync', { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    window.location.reload();
                } else {
                    alert('Erro ao sincronizar: ' + (data.error || 'Erro desconhecido'));
                    btn.disabled = false;
                    btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Sincronizar do Chatwoot';
                }
            } catch (e) {
                alert('Erro: ' + e.message);
            }
        }

        async function loadLabels() {
            try {
                const res = await fetch('/api/' + slug + '/labels');
                const data = await res.json();
                allLabels = data.payload || data || [];
            } catch (e) {
                console.error('Erro ao carregar labels:', e);
                allLabels = [];
            }
        }

        async function editPermissions(userId, userName, allowedLabels, isAdmin) {
            currentUserId = userId;
            document.getElementById('modalUserName').textContent = userName;
            document.getElementById('isAdminCheck').checked = isAdmin;

            await loadLabels();

            const labelsList = document.getElementById('labelsList');
            if (allLabels.length === 0) {
                labelsList.innerHTML = '<p class="text-gray-500 text-sm">Nenhuma label encontrada</p>';
            } else {
                labelsList.innerHTML = allLabels.map(label => {
                    const checked = allowedLabels.includes(label.title) ? 'checked' : '';
                    return '<label class="flex items-center gap-3 cursor-pointer p-2 hover:bg-gray-800 rounded"><input type="checkbox" class="label-check w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-600" value="' + label.title + '" ' + checked + '><span class="text-white">' + label.title + '</span></label>';
                }).join('');
            }

            document.getElementById('permModal').classList.remove('hidden');
            document.getElementById('permModal').classList.add('flex');
        }

        function closeModal() {
            document.getElementById('permModal').classList.add('hidden');
            document.getElementById('permModal').classList.remove('flex');
            currentUserId = null;
        }

        async function savePermissions() {
            const isAdmin = document.getElementById('isAdminCheck').checked;
            const allowedLabels = Array.from(document.querySelectorAll('.label-check:checked')).map(c => c.value);

            try {
                const res = await fetch('/admin/' + slug + '/usuarios/' + currentUserId + '/permissions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_admin: isAdmin, allowed_labels: allowedLabels })
                });
                const data = await res.json();
                if (data.success) {
                    window.location.reload();
                } else {
                    alert('Erro ao salvar: ' + (data.error || 'Erro desconhecido'));
                }
            } catch (e) {
                alert('Erro: ' + e.message);
            }
        }

        document.getElementById('isAdminCheck').addEventListener('change', function() {
            document.getElementById('labelsSection').style.opacity = this.checked ? '0.5' : '1';
            document.getElementById('labelsSection').style.pointerEvents = this.checked ? 'none' : 'auto';
        });
    </script>
</body>
</html>
    `);
});

// Sincronizar usuários do Chatwoot
app.post('/admin/:slug/usuarios/sync', requireAdmin, async (req, res) => {
    try {
        const clients = await loadClients();
        const client = clients[req.params.slug];

        if (!client) {
            return res.status(404).json({ error: 'Cliente não encontrado' });
        }

        let users = [];

        // Tentar primeiro /agents (mais comum)
        try {
            const agentsResponse = await fetch(`${client.apiUrl}/api/v1/accounts/${client.accountId}/agents`, {
                headers: { 'api_access_token': client.apiToken }
            });
            if (agentsResponse.ok) {
                users = await agentsResponse.json();
                log('api', `Buscados ${users.length} agentes via /agents`, req.params.slug);
            }
        } catch (e) {
            log('warning', 'Endpoint /agents falhou', e.message);
        }

        // Se /agents falhou, tentar /account_users
        if (users.length === 0) {
            try {
                const accountUsersResponse = await fetch(`${client.apiUrl}/api/v1/accounts/${client.accountId}/account_users`, {
                    headers: { 'api_access_token': client.apiToken }
                });
                if (accountUsersResponse.ok) {
                    users = await accountUsersResponse.json();
                    log('api', `Buscados ${users.length} usuários via /account_users`, req.params.slug);
                }
            } catch (e) {
                log('warning', 'Endpoint /account_users falhou', e.message);
            }
        }

        // Se ainda não temos usuários, tentar /team_members
        if (users.length === 0) {
            try {
                const teamResponse = await fetch(`${client.apiUrl}/api/v1/accounts/${client.accountId}/team_members`, {
                    headers: { 'api_access_token': client.apiToken }
                });
                if (teamResponse.ok) {
                    users = await teamResponse.json();
                    log('api', `Buscados ${users.length} membros via /team_members`, req.params.slug);
                }
            } catch (e) {
                log('warning', 'Endpoint /team_members falhou', e.message);
            }
        }

        if (users.length === 0) {
            return res.status(400).json({ error: 'Não foi possível buscar usuários do Chatwoot. Verifique a URL e token da API.' });
        }

        // Salvar cada usuário
        let synced = 0;
        for (const user of users) {
            const userId = user.id || user.user_id;
            if (!userId) continue;

            const existing = await getUserPermission(req.params.slug, userId);
            await saveUserPermission(req.params.slug, {
                chatwoot_user_id: userId,
                user_name: user.name || user.available_name || user.email || '',
                user_email: user.email || '',
                user_role: user.role || 'agent',
                allowed_labels: existing ? existing.allowed_labels : [],
                allowed_boards: existing ? existing.allowed_boards : [],
                is_admin: existing ? existing.is_admin : (user.role === 'administrator')
            });
            synced++;
        }

        log('success', `Sincronizados ${synced} usuários`, req.params.slug);
        res.json({ success: true, synced: synced });

    } catch (error) {
        log('error', 'Erro ao sincronizar usuários', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Salvar permissões de um usuário
app.post('/admin/:slug/usuarios/:userId/permissions', requireAdmin, async (req, res) => {
    try {
        const userId = parseInt(req.params.userId);
        if (isNaN(userId) || userId <= 0) {
            return res.status(400).json({ error: 'ID de usuário inválido' });
        }

        const { is_admin, allowed_labels, allowed_boards } = req.body;
        const existing = await getUserPermission(req.params.slug, userId);

        if (!existing) {
            return res.status(404).json({ error: 'Usuário não encontrado' });
        }

        await saveUserPermission(req.params.slug, {
            chatwoot_user_id: userId,
            user_name: existing.user_name,
            user_email: existing.user_email,
            user_role: existing.user_role,
            allowed_labels: allowed_labels || existing.allowed_labels || [],
            allowed_boards: allowed_boards || existing.allowed_boards || [],
            is_admin: is_admin || false
        });

        log('success', `Permissões atualizadas para usuário ${userId}`, req.params.slug);
        res.json({ success: true });

    } catch (error) {
        log('error', 'Erro ao salvar permissões', error.message);
        res.status(500).json({ error: error.message });
    }
});

// API para obter permissões de um usuário (usado pelo kanban/disparador)
app.get('/api/:slug/user-permissions/:userId', async (req, res) => {
    try {
        const userId = parseInt(req.params.userId);
        if (isNaN(userId) || userId <= 0) {
            return res.json({ found: false, error: 'ID de usuário inválido' });
        }

        const permission = await getUserPermission(req.params.slug, userId);
        if (!permission) {
            return res.json({ found: false });
        }
        res.json({
            found: true,
            chatwoot_user_id: permission.chatwoot_user_id,
            is_admin: permission.is_admin,
            allowed_labels: permission.allowed_labels || [],
            allowed_boards: permission.allowed_boards || [],
            user_name: permission.user_name,
            user_role: permission.user_role
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API para listar usuários (usado pelo kanban/disparador para seleção)
app.get('/api/:slug/users', async (req, res) => {
    try {
        const permissions = await getUserPermissions(req.params.slug);
        res.json(permissions.map(p => ({
            id: p.chatwoot_user_id,
            chatwoot_user_id: p.chatwoot_user_id,
            name: p.user_name,
            email: p.user_email,
            role: p.user_role,
            is_admin: p.is_admin,
            allowed_labels: p.allowed_labels || [],
            allowed_boards: p.allowed_boards || []
        })));
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API para sincronizar usuários (chamado pelo kanban)
app.post('/api/:slug/sync-users', async (req, res) => {
    try {
        const clients = await loadClients();
        const client = clients[req.params.slug];

        if (!client) {
            return res.status(404).json({ error: 'Cliente não encontrado' });
        }

        let users = [];

        // Tentar primeiro /agents (mais comum)
        try {
            const agentsResponse = await fetch(`${client.apiUrl}/api/v1/accounts/${client.accountId}/agents`, {
                headers: { 'api_access_token': client.apiToken }
            });
            if (agentsResponse.ok) {
                users = await agentsResponse.json();
                log('api', `Buscados ${users.length} agentes via /agents`, req.params.slug);
            }
        } catch (e) {
            log('warning', 'Endpoint /agents falhou', e.message);
        }

        // Se /agents falhou, tentar /account_users
        if (users.length === 0) {
            try {
                const accountUsersResponse = await fetch(`${client.apiUrl}/api/v1/accounts/${client.accountId}/account_users`, {
                    headers: { 'api_access_token': client.apiToken }
                });
                if (accountUsersResponse.ok) {
                    users = await accountUsersResponse.json();
                    log('api', `Buscados ${users.length} usuários via /account_users`, req.params.slug);
                }
            } catch (e) {
                log('warning', 'Endpoint /account_users falhou', e.message);
            }
        }

        if (users.length === 0) {
            return res.status(400).json({ error: 'Não foi possível buscar usuários do Chatwoot. Verifique a URL e token da API.' });
        }

        // Salvar cada usuário
        let synced = 0;
        for (const user of users) {
            const userId = user.id || user.user_id;
            if (!userId) continue;

            const existing = await getUserPermission(req.params.slug, userId);
            await saveUserPermission(req.params.slug, {
                chatwoot_user_id: userId,
                user_name: user.name || user.available_name || user.email || '',
                user_email: user.email || '',
                user_role: user.role || 'agent',
                allowed_labels: existing ? existing.allowed_labels : [],
                allowed_boards: existing ? existing.allowed_boards : [],
                is_admin: existing ? existing.is_admin : (user.role === 'administrator')
            });
            synced++;
        }

        log('success', `Sincronizados ${synced} usuários via API`, req.params.slug);
        res.json({ success: true, synced: synced });

    } catch (error) {
        log('error', 'Erro ao sincronizar usuários via API', error.message);
        res.status(500).json({ error: error.message });
    }
});

// ========================================
// API DE BOARDS (Kanban)
// ========================================

// Listar todos os boards de um cliente
app.get('/api/:slug/boards', async (req, res) => {
    try {
        const boards = await getBoards(req.params.slug);
        res.json(boards);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Obter um board específico
app.get('/api/:slug/boards/:boardId', async (req, res) => {
    try {
        const board = await getBoard(req.params.slug, req.params.boardId);
        if (!board) {
            return res.status(404).json({ error: 'Board não encontrado' });
        }
        res.json(board);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Criar ou atualizar um board
app.post('/api/:slug/boards', async (req, res) => {
    try {
        const { id, name, columns } = req.body;
        if (!id || !name || !columns) {
            return res.status(400).json({ error: 'Campos obrigatórios: id, name, columns' });
        }
        await saveBoard(req.params.slug, { id, name, columns });
        log('success', `Board salvo: ${name}`, req.params.slug);
        res.json({ success: true, id });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Atualizar um board existente
app.put('/api/:slug/boards/:boardId', async (req, res) => {
    try {
        const { name, columns } = req.body;
        const existing = await getBoard(req.params.slug, req.params.boardId);
        if (!existing) {
            return res.status(404).json({ error: 'Board não encontrado' });
        }
        await saveBoard(req.params.slug, {
            id: req.params.boardId,
            name: name || existing.name,
            columns: columns || existing.columns
        });
        log('success', `Board atualizado: ${name || existing.name}`, req.params.slug);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Deletar um board
app.delete('/api/:slug/boards/:boardId', async (req, res) => {
    try {
        await deleteBoard(req.params.slug, req.params.boardId);
        log('success', `Board deletado: ${req.params.boardId}`, req.params.slug);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API para salvar permissões de usuário (chamado pelo kanban)
app.post('/api/:slug/user-permissions/:userId', async (req, res) => {
    try {
        const userId = parseInt(req.params.userId);
        if (isNaN(userId) || userId <= 0) {
            return res.status(400).json({ error: 'ID de usuário inválido' });
        }

        const { is_admin, allowed_labels, allowed_boards } = req.body;
        const existing = await getUserPermission(req.params.slug, userId);

        if (!existing) {
            return res.status(404).json({ error: 'Usuário não encontrado' });
        }

        await saveUserPermission(req.params.slug, {
            chatwoot_user_id: userId,
            user_name: existing.user_name,
            user_email: existing.user_email,
            user_role: existing.user_role,
            allowed_labels: allowed_labels || existing.allowed_labels || [],
            allowed_boards: allowed_boards || existing.allowed_boards || [],
            is_admin: is_admin || false
        });

        log('success', `Permissões atualizadas para usuário ${userId} via API`, req.params.slug);
        res.json({ success: true });

    } catch (error) {
        log('error', 'Erro ao salvar permissões via API', error.message);
        res.status(500).json({ error: error.message });
    }
});

// ========================================
// ROTA DO KANBAN (Dashboard App)
// ========================================
app.get('/kanban/:slug', async (req, res) => {
    const clients = await loadClients();
    const client = clients[req.params.slug];

    if (!client) {
        return res.status(404).json({ error: 'Cliente não encontrado' });
    }

    let html = fs.readFileSync(path.join(__dirname, 'kanban.html'), 'utf8');

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

    html = html.replace('</head>', configScript + '</head>');
    res.send(html);
});

// ========================================
// ROTA DO DISPARADOR (Mass Message Dispatcher)
// ========================================
app.get('/disparador/:slug', async (req, res) => {
    const clients = await loadClients();
    const client = clients[req.params.slug];

    if (!client) {
        return res.status(404).json({ error: 'Cliente não encontrado' });
    }

    let html = fs.readFileSync(path.join(__dirname, 'disparador.html'), 'utf8');

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

    html = html.replace('</head>', configScript + '</head>');
    res.send(html);
});

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
// PROXY MULTIPART - UPLOAD DE MÍDIA
// ========================================
app.post('/api/:slug/conversations/:convId/messages/upload',
    uploadMulter.array('attachments[]', 5),
    async (req, res) => {
    try {
        const clients = await loadClients();
        const client = clients[req.params.slug];

        if (!client) {
            return res.status(404).json({ error: 'Cliente não encontrado' });
        }

        const url = `${client.apiUrl}/api/v1/accounts/${client.accountId}/conversations/${req.params.convId}/messages`;

        log('api', `POST /conversations/${req.params.convId}/messages (multipart)`, req.params.slug);

        const formData = new FormDataLib();

        if (req.body.content) {
            formData.append('content', req.body.content);
        }
        formData.append('message_type', req.body.message_type || 'outgoing');

        if (req.files && req.files.length > 0) {
            req.files.forEach(file => {
                formData.append('attachments[]', file.buffer, {
                    filename: file.originalname,
                    contentType: file.mimetype
                });
            });
        }

        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'api_access_token': client.apiToken,
                ...formData.getHeaders()
            },
            body: formData
        });

        const data = await response.json();
        res.status(response.status).json(data);

    } catch (error) {
        log('error', 'Multipart proxy error', error.message);
        res.status(500).json({ error: error.message });
    }
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

        // Monta a URL da API do Chatwoot (com query string original preservada)
        const endpoint = req.path.replace(`/api/${req.params.slug}`, '');
        const qsIndex = req.originalUrl.indexOf('?');
        const qs = qsIndex >= 0 ? req.originalUrl.substring(qsIndex + 1) : '';
        const url = `${client.apiUrl}/api/v1/accounts/${client.accountId}${endpoint}${qs ? '?' + qs : ''}`;

        log('api', `${req.method} ${endpoint}${qs ? '?' + qs : ''}`, req.params.slug);

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

        const text = await response.text();
        let data;
        try { data = JSON.parse(text); } catch(e) { data = { raw: text }; }

        if (!response.ok) {
            log('error', `API ${response.status}: ${endpoint}`, JSON.stringify(data).substring(0, 200));
        }

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
// Evitar crash por erros não tratados
process.on('uncaughtException', (err) => {
    log('error', 'Uncaught Exception', err.message);
});
process.on('unhandledRejection', (reason) => {
    log('error', 'Unhandled Rejection', String(reason));
});

// Pool do PostgreSQL - evitar crash em erro de conexão
if (pool) {
    pool.on('error', (err) => {
        log('error', 'PostgreSQL pool error', err.message);
    });
}

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
