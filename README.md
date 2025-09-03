# API Python de Busca Local - smartQuote

**API Flask completamente independente** para processamento de interpretações e busca híbrida de produtos.

## 📋 Visão Geral

Esta API roda **independentemente** da API principal Node.js e pode ser hospedada em servidores diferentes, oferecendo:

- **Arquitetura desacoplada**: API Python independente da API Node.js
- **Deploy isolado**: Pode ser hospedada em qualquer servidor/cloud
- **Escalabilidade horizontal**: Múltiplas instâncias com load balancing
- **Zero dependências** da API principal: Apenas Weaviate, Supabase e GROQ

## 📚 Documentação Completa

### 📖 **Documentos Principais**
- **[🔧 Como Consumir a API](CONSUMO_API_BUSCA_LOCAL.md)** - Guia completo para desenvolvedores
- **[📊 Tabela Relatórios](TABELA_RELATORIOS.md)** - Estrutura e funcionamento da auditoria
- **[🔍 Exemplos de Consultas](EXEMPLOS_CONSULTAS_RELATORIOS.md)** - SQL práticos para análises
- **[🎨 Diagrama Visual](DIAGRAMA_RELATORIOS.md)** - Estruturas visuais e fluxogramas

### 🎯 **Documentos Específicos**
- **[📋 Como Rodar](COMO-RODAR.md)** - Setup e execução local
- **[🔄 Migração HuggingFace](MIGRACAO_API_HF.md)** - Histórico de migração

## 🏗️ Arquitetura Independente

```
┌─────────────────┐    HTTP    ┌─────────────────┐
│   API Node.js   │◄──────────►│   API Python    │
│  (Principal)    │            │  (Independente) │
│                 │            │                 │
│ - Controllers   │            │ - Flask App     │
│ - Routes        │            │ - Weaviate      │
│ - Auth          │            │ - Supabase      │
│ - Business      │            │ - GROQ LLM      │
└─────────────────┘            └─────────────────┘
                                       │
                                   HTTP/TCP
                                       │
                                ┌─────────────┐
                                │  Serviços   │
                                │  Externos   │
                                │             │
                                │ - Weaviate  │
                                │ - Supabase  │
                                │ - GROQ      │
                                └─────────────┘
```

## 🚀 Deploy Independente

### Opção 1: Deploy Automatizado (Recomendado)

```bash
# Clone apenas a pasta busca_local para seu servidor
cd /path/to/your/server
git clone https://github.com/alfredo003/smartquote-backend.git
cd smartquote-backend/scripts/busca_local

# Configure o ambiente
cp .env.example .env
# Edite .env com suas configurações

# Deploy automático (Linux/Mac)
chmod +x deploy.sh
./deploy.sh

# Deploy automático (Windows)
.\deploy.ps1
```

### Opção 2: Deploy Manual com Docker

```bash
# 1. Configurar ambiente
cp .env.example .env
# Editar .env com suas configurações

# 2. Para produção (apenas API Python)
docker-compose up --build -d

# 3. Para desenvolvimento (com Weaviate local)
docker-compose --profile local up --build -d

# 4. Para produção com load balancing
docker-compose --profile production up --build -d
```

### Opção 3: Deploy Nativo (sem Docker)

```bash
# 1. Instalar Python 3.10+
python --version

# 2. Instalar dependências
pip install -r requirements-api.txt

# 3. Configurar ambiente
export PYTHON_API_HOST=0.0.0.0
export PYTHON_API_PORT=5001
export SUPABASE_URL=https://seu-projeto.supabase.co
export GROQ_API_KEY=sua_chave_groq
# ... outras variáveis

# 4. Executar API
python app.py
```

## 🔧 Configuração

### ⚠️ IMPORTANTE: Variáveis de Ambiente

A API Python é **completamente independente** e busca suas configurações em:

1. **Arquivo `.env` LOCAL** (no diretório `scripts/busca_local/.env`)
2. **Variáveis de ambiente do sistema** (se .env não existir)

**NÃO** usa mais o `.env` da raiz do projeto Node.js!

### Configuração Inicial

```bash
# 1. Navegar para o diretório da API Python
cd scripts/busca_local

# 2. Criar .env local baseado no exemplo
cp .env.example .env

# 3. Editar .env com suas configurações
nano .env  # ou seu editor preferido

# 4. Testar configuração
python test-env.py
```

### Variáveis Obrigatórias (.env local)

```bash
# Supabase (sempre remoto)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role

# GROQ LLM (sempre remoto)
GROQ_API_KEY=gsk_sua_chave_groq

# Weaviate (local ou remoto)
WEAVIATE_URL=http://weaviate:8080  # Para Docker local
# WEAVIATE_URL=https://seu-cluster.weaviate.io  # Para remoto
```

### Variáveis Opcionais (.env local)

```bash
# Configurações da API Python
PYTHON_API_HOST=0.0.0.0
PYTHON_API_PORT=5001
PYTHON_API_DEBUG=false

# Configurações de processamento
PYTHON_DEFAULT_LIMIT=10
PYTHON_USE_MULTILINGUAL=true
PYTHON_CREATE_QUOTATION=false

# Weaviate (se usando cluster com autenticação)
WEAVIATE_API_KEY=sua_chave_weaviate
```

## 📡 Endpoints da API

### Health Check
```http
GET /health
```

Verifica se todos os serviços estão funcionais.

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-02T12:00:00Z",
  "services": {
    "weaviate": true,
    "supabase": true,
    "decomposer": true
  }
}
```

### Processar Interpretação
```http
POST /process-interpretation
Content-Type: application/json

{
  "interpretation": {
    "solicitacao": "Preciso de 10 computadores para escritório",
    "emailId": "123",
    "cliente": "Empresa XYZ"
  },
  "limite": 10,
  "usar_multilingue": true,
  "criar_cotacao": false
}
```

**Resposta:**
```json
{
  "status": "success",
  "processed_at": "2025-09-02T12:00:00Z",
  "resultado_resumo": {
    "Q0": [
      {
        "nome": "Computador Dell OptiPlex",
        "categoria": "Desktop",
        "preco": 2500.00,
        "score": 0.95
      }
    ]
  },
  "faltantes": [],
  "cotacoes": {
    "principal_id": "456",
    "itens_adicionados": 1
  }
}
```

### Busca Híbrida
```http
POST /hybrid-search
Content-Type: application/json

{
  "pesquisa": "notebook gamer",
  "filtros": {
    "categoria": "Notebook",
    "preco_max": 5000
  },
  "limite": 5,
  "usar_multilingue": true
}
```

**Resposta:**
```json
{
  "status": "success",
  "resultados": [
    {
      "nome": "Notebook Gamer Acer Nitro",
      "categoria": "Notebook",
      "preco": 4500.00,
      "score": 0.92
    }
  ],
  "total_encontrados": 1,
  "espacos_pesquisados": ["vetor_portugues", "vetor_multilingue"]
}
```

### Sincronizar Produtos
```http
POST /sync-products
```

Sincroniza produtos do Supabase para o Weaviate.

## 🔄 Migração do Sistema Anterior

### Antes (Processo Filho)
```typescript
// Spawna processo Python para cada requisição
const result = await pythonProcessor.processInterpretation(interpretation);
```

### Depois (API HTTP)
```typescript
// Faz requisição HTTP para API persistente
const result = await pythonApiClient.processInterpretation({
  interpretation,
  limite: 10,
  criar_cotacao: true
});
```

### Vantagens da Nova Arquitetura

1. **Performance**: Sem overhead de spawn de processo
2. **Monitoramento**: Health checks e métricas HTTP padrão
3. **Debugging**: Logs estruturados e endpoint de status
4. **Escalabilidade**: Pode rodar em containers separados
5. **Reliability**: Auto-restart e health checks do Docker

## 🐛 Debugging

### Verificar Status da API
```bash
curl http://127.0.0.1:5001/health
```

### Logs da API
Os logs são exibidos no console da API e incluem:
- `🐍 [PYTHON-API]` - Logs da API Flask
- `🔍 [WEAVIATE]` - Logs do Weaviate
- `📊 [SUPABASE]` - Logs do Supabase
- `🧠 [LLM]` - Logs do processamento de LLM

### Variáveis de Debug
```bash
# Habilitar debug da API Flask
PYTHON_API_DEBUG=true

# Logs mais verbosos
PYTHON_LOG_LEVEL=DEBUG
```

## 🚦 Monitoramento em Produção

### Health Check Automático
```bash
# Health check via curl
curl -f http://127.0.0.1:5001/health || exit 1

# Health check no Docker Compose
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5001/health', timeout=5)"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Métricas
A API expõe automaticamente:
- Tempo de resposta das requisições
- Status de saúde dos serviços dependentes
- Número de produtos sincronizados
- Contadores de sucesso/erro

## 🔧 Desenvolvimento

### Estrutura de Arquivos
```
scripts/busca_local/
├── app.py                 # API Flask principal
├── requirements-api.txt   # Dependências da API
├── Dockerfile            # Container da API
├── docker-compose.yml    # Orquestração
├── config.py             # Configurações
├── weaviate_client.py    # Cliente Weaviate
├── supabase_client.py    # Cliente Supabase
├── search_engine.py      # Engine de busca
├── decomposer.py         # Decomposição LLM
└── ...                   # Outros módulos
```

### Adicionando Novos Endpoints
```python
@app.route('/novo-endpoint', methods=['POST'])
def novo_endpoint():
    try:
        data = request.get_json()
        # Processamento
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
```

## 🚀 Deploy

### Docker Swarm
```bash
docker stack deploy -c docker-compose.yml smartquote-python
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smartquote-python-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: smartquote-python-api
  template:
    metadata:
      labels:
        app: smartquote-python-api
    spec:
      containers:
      - name: python-api
        image: smartquote-python-api:latest
        ports:
        - containerPort: 5001
        env:
        - name: PYTHON_API_HOST
          value: "0.0.0.0"
```

## 🔒 Segurança

### Recomendações
1. Use HTTPS em produção
2. Configure rate limiting
3. Valide todos os inputs
4. Use secrets para API keys
5. Configure CORS adequadamente

### Exemplo com Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/process-interpretation', methods=['POST'])
@limiter.limit("10 per minute")
def process_interpretation():
    # ...
```

## 📊 Sistema de Auditoria e Relatórios

### 🎯 **Nova Funcionalidade: Rastreabilidade Completa**

A partir da versão 2.0, o sistema conta com **auditoria completa** de todas as análises e decisões:

#### ✅ **Garantias de Rastreabilidade**
- ✅ **Todas as buscas geram relatórios** (sucesso ou falha)
- ✅ **Análises LLM preservadas** mesmo quando produtos são rejeitados
- ✅ **Histórico detalhado** de critérios e justificativas
- ✅ **Métricas de performance** para otimização contínua

#### 📋 **Tipos de Relatório Criados**
```json
// Produto aceito - Relatório completo + Item na cotação
{
    "status": "produto_adicionado",
    "llm_relatorio": { /* análise completa LLM */ }
}

// Produto rejeitado - Relatório preservado + Sem item na cotação
{
    "status": "rejeitado_por_llm", 
    "llm_relatorio": { /* análise completa PRESERVADA */ }
}

// Busca sem resultados - Relatório de análise vazia
{
    "status": "sem_produtos_encontrados",
    "observacao": "Nenhum produto encontrado na base"
}
```

#### 🔍 **Consultando Relatórios**
```sql
-- Ver relatórios de uma cotação específica
SELECT analise_local FROM relatorios WHERE cotacao_id = 123;

-- Produtos rejeitados pela LLM com justificativas
SELECT 
    analise_local -> 0 -> 'llm_relatorio' ->> 'justificativa_escolha' as motivo_rejeicao
FROM relatorios 
WHERE analise_local @> '[{"status": "rejeitado_por_llm"}]';

-- Taxa de sucesso da LLM
SELECT 
    COUNT(CASE WHEN analise_local @> '[{"status": "produto_adicionado"}]' THEN 1 END) as aceitos,
    COUNT(CASE WHEN analise_local @> '[{"status": "rejeitado_por_llm"}]' THEN 1 END) as rejeitados
FROM relatorios;
```

#### 📚 **Documentação Detalhada**
- **[📊 Estrutura Completa](TABELA_RELATORIOS.md)** - Como funciona a tabela relatórios
- **[🔍 Consultas SQL](EXEMPLOS_CONSULTAS_RELATORIOS.md)** - Exemplos práticos de análise
- **[🎨 Diagramas Visuais](DIAGRAMA_RELATORIOS.md)** - Fluxos e estruturas visuais
