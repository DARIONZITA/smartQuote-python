# 🐍 Guia: Como Rodar a API Python para Testar

## 📋 Pré-requisitos

### 1. Instalar Python 3.10+

**Windows:**
```powershell
# Opção 1: Microsoft Store
# Procurar "Python" na Microsoft Store e instalar

# Opção 2: Download direto
# Baixar de https://python.org/downloads/
# Marcar "Add Python to PATH" durante instalação

# Opção 3: Chocolatey
choco install python

# Opção 4: Winget
winget install Python.Python.3.11
```

**Linux/Ubuntu:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS:**
```bash
# Homebrew
brew install python3

# Ou baixar de python.org
```

### 2. Verificar Instalação
```bash
python --version    # ou python3 --version
pip --version       # ou pip3 --version
```

## 🚀 Passos para Rodar a API Python

### 1. Navegar para o Diretório
```bash
cd scripts/busca_local
```

### 2. Configurar Ambiente Python (Recomendado)
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Verificar se ativou (deve mostrar (venv) no prompt)
```

### 3. Instalar Dependências
```bash
# Instalar dependências da API
pip install -r requirements-api.txt

# Ou manualmente se der erro:
pip install flask flask-cors pydantic weaviate-client sentence-transformers groq supabase python-dotenv
```

### 4. Configurar Variáveis de Ambiente
```bash
# Copiar exemplo de configuração
cp .env.example .env

# Editar .env com suas configurações
# Windows: notepad .env
# Linux/Mac: nano .env
```

**Mínimo necessário no .env:**
```bash
# API Python
PYTHON_API_HOST=127.0.0.1
PYTHON_API_PORT=5001
PYTHON_API_DEBUG=true

# Supabase (obrigatório)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role

# GROQ (obrigatório)
GROQ_API_KEY=gsk_sua_chave_groq

# Weaviate (opcional - pode usar mock)
WEAVIATE_URL=http://localhost:8080
```

### 5. Testar Configuração
```bash
python test-env.py
```

### 6. Rodar a API Python
```bash
python app.py
```

**Saída esperada:**
```
🚀 Inicializando serviços...
✅ Weaviate conectado
✅ Supabase conectado - 0 produtos indexados
✅ Decomposer (GROQ) inicializado
🎉 Todos os serviços inicializados com sucesso!
🌐 Iniciando API Python em 127.0.0.1:5001
 * Running on http://127.0.0.1:5001
```

## 🧪 Testar a API

### 1. Health Check
```bash
# Em outro terminal:
curl http://127.0.0.1:5001/health

# Ou no navegador:
# http://127.0.0.1:5001/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-02T12:00:00",
  "services": {
    "weaviate": true,
    "supabase": true,
    "decomposer": true
  }
}
```

### 2. Teste de Busca Híbrida
```bash
curl -X POST http://127.0.0.1:5001/hybrid-search \
  -H "Content-Type: application/json" \
  -d '{"pesquisa": "notebook", "limite": 3}'
```

### 3. Teste de Sincronização
```bash
curl -X POST http://127.0.0.1:5001/sync-products
```

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError"
```bash
# Reinstalar dependências
pip install -r requirements-api.txt

# Ou instalar módulo específico
pip install nome_do_modulo
```

### Erro: "Port 5001 already in use"
```bash
# Mudar porta no .env
PYTHON_API_PORT=5002

# Ou matar processo na porta
# Windows:
netstat -ano | findstr :5001
taskkill /PID numero_do_pid /F

# Linux/Mac:
lsof -ti:5001 | xargs kill -9
```

### Erro: "GROQ_API_KEY not found"
```bash
# Verificar se .env está carregado
python -c "import os; print(os.getenv('GROQ_API_KEY'))"

# Se retornar None, verificar .env
cat .env | grep GROQ
```

### Erro: "Supabase connection failed"
```bash
# Testar conexão manual
curl -H "Authorization: Bearer sua_service_role_key" \
     "https://seu-projeto.supabase.co/rest/v1/produtos?limit=1"
```

### Erro: "Weaviate connection failed"
```bash
# Se usando Weaviate local, iniciar com Docker:
docker run -p 8080:8080 semitechnologies/weaviate:1.24.4

# Ou usar mock/desabilitar Weaviate temporariamente
```

## 🔄 Desenvolvimento com Auto-reload

### Usar Flask em modo debug:
```bash
# No .env:
PYTHON_API_DEBUG=true

# Rodar:
python app.py
```

### Ou usar ferramentas de desenvolvimento:
```bash
# Instalar watchdog
pip install watchdog

# Rodar com auto-reload
python -m flask --app app run --debug --host 127.0.0.1 --port 5001
```

## 📝 Logs e Debug

### Ver logs detalhados:
```bash
# No .env:
PYTHON_API_DEBUG=true
LOG_LEVEL=DEBUG

# Rodar com logs verbosos:
python app.py
```

### Arquivo de log:
```bash
# Logs são salvos em:
tail -f api-python.log
```

## 🐳 Alternativa: Usar Docker

Se tiver problemas com Python local:

```bash
# Build da imagem
docker build -t python-api .

# Rodar container
docker run -p 5001:5001 --env-file .env python-api

# Ou usar docker-compose
docker-compose up --build
```

## ✅ Checklist de Validação

- [ ] Python 3.10+ instalado
- [ ] Dependências instaladas (`pip list`)
- [ ] Arquivo .env configurado
- [ ] Health check retorna "healthy"
- [ ] Logs não mostram erros críticos
- [ ] Portas 5001 acessível

---

**Pronto!** 🎉 Sua API Python está rodando e pronta para ser consumida pela API principal!
