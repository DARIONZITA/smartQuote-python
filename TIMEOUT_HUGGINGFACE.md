# Configuração de Timeout e Resiliência para HuggingFace API

## Problema Identificado

A API do HuggingFace Space (`dnzita-smartquote.hf.space`) estava apresentando timeouts frequentes durante a geração de embeddings, com o erro:

```
urllib3.exceptions.ReadTimeoutError: HTTPSConnectionPool: Read timed out.
```

## Soluções Implementadas

### 1. Variáveis de Ambiente para Timeout

Agora é possível configurar o comportamento de timeout através de variáveis de ambiente no arquivo `.env`:

```bash
# Timeout em segundos para chamadas à API (padrão: 60s)
EMBEDDING_TIMEOUT=60

# Número máximo de tentativas em caso de falha (padrão: 5)
EMBEDDING_MAX_RETRIES=5

# Tempo base entre tentativas - backoff exponencial (padrão: 3.0s)
EMBEDDING_RETRY_BACKOFF=3.0
```

### 2. Melhorias no Código

#### a) Logging Detalhado

O método `encode()` agora registra:
- Tempo decorrido em cada tentativa
- Tipo de erro (TIMEOUT, CONEXÃO, ERRO)
- Progresso das tentativas e retries
- Mensagens claras sobre próximas ações

```
🔍 Tentando gerar embedding (tentativa 1/5, timeout=60s)...
⏱️ TIMEOUT ao gerar embedding após 30.45s (tentativa 1/5): The read operation timed out
🔄 Reconectando ao HuggingFace Space dnzita/smartquote...
⏸️ Aguardando 3.0s antes da próxima tentativa...
```

#### b) Reconexão Completa

Em caso de timeout, o sistema agora:
1. Destrói completamente a conexão (`self.client = None`)
2. Cria uma nova conexão do zero
3. Aguarda com backoff exponencial antes de tentar novamente

#### c) Detecção Inteligente de Erros

O código diferencia entre:
- **Timeouts**: Erros de leitura que expiram
- **Conexão**: Problemas de rede (handshake, reset, aborted)
- **Transitórios**: Erros temporários que podem ser resolvidos com retry
- **Permanentes**: Erros que não devem ser retentados

#### d) Sugestões Automáticas

Quando todas as tentativas falham, o sistema sugere:
```
❌ Falha após 5 tentativas - HuggingFace API não respondeu dentro de 60s. 
Considere: 
1) Aumentar EMBEDDING_TIMEOUT
2) Verificar status do Space dnzita/smartquote
3) Usar modelo alternativo.
```

### 3. Valores Padrão Atualizados

| Parâmetro | Valor Antigo | Valor Novo | Justificativa |
|-----------|--------------|------------|---------------|
| `timeout` | 30s | 60s | HuggingFace Spaces podem ser lentos em cold start |
| `max_retries` | 3 | 5 | Mais chances de recuperação |
| `backoff_seconds` | 2.0s | 3.0s | Mais tempo para API se estabilizar |

### 4. Backoff Exponencial

O tempo de espera entre tentativas cresce exponencialmente:
- Tentativa 1 → 2: aguarda 3.0s
- Tentativa 2 → 3: aguarda 6.0s
- Tentativa 3 → 4: aguarda 12.0s
- Tentativa 4 → 5: aguarda 15.0s (limitado a 15s)

Fórmula: `min(EMBEDDING_RETRY_BACKOFF * (2 ^ tentativa), 15)`

## Configuração Recomendada

### Para Desenvolvimento Local
```bash
EMBEDDING_TIMEOUT=30
EMBEDDING_MAX_RETRIES=3
EMBEDDING_RETRY_BACKOFF=2.0
```

### Para Produção (Render)
```bash
EMBEDDING_TIMEOUT=90
EMBEDDING_MAX_RETRIES=5
EMBEDDING_RETRY_BACKOFF=3.0
```

### Para Problemas Persistentes
```bash
EMBEDDING_TIMEOUT=120
EMBEDDING_MAX_RETRIES=7
EMBEDDING_RETRY_BACKOFF=5.0
```

## Como Testar

1. Configure as variáveis de ambiente no `.env`
2. Execute localmente:
```powershell
python app.py
```

3. Faça uma requisição de teste:
```powershell
$headers = @{ "Content-Type" = "application/json" }
$body = @{
    interpretation = "Macbook | Fornece mobilidade e produtividade para a equipe de TI."
    create_quotation = $false
    limit = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/process-interpretation" -Method POST -Headers $headers -Body $body
```

4. Observe os logs para verificar:
   - ✅ Embeddings gerados com sucesso
   - 🔄 Reconexões automáticas
   - ⏱️ Tempos de resposta

## Próximos Passos (se problemas persistirem)

1. **Cache de Embeddings**: Armazenar embeddings já calculados
2. **Modelo Local**: Hospedar modelo de embedding no próprio servidor
3. **Fallback Provider**: Usar API alternativa quando HuggingFace falhar
4. **Queue System**: Processar embeddings em background assíncrono

## Monitoramento

Para acompanhar a saúde da API de embeddings:

```powershell
# Ver logs em tempo real no Render
# Dashboard → Logs → Filtrar por "embedding"
```

Procure por:
- `✅ Embedding gerado com sucesso` - Operações bem-sucedidas
- `⏱️ TIMEOUT` - Problemas de timeout
- `🔌 CONEXÃO` - Problemas de rede
- `❌ Falha após N tentativas` - Falhas definitivas
