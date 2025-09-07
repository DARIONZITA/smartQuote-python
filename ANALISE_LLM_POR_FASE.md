# Análise LLM por Fase: Local vs Cache

## Resumo da Funcionalidade

A análise da LLM agora é diferenciada por fase de busca:
- **Produtos da Fase LOCAL** → Análise salva na coluna `analise_local`
- **Produtos da Fase CACHE** → Análise salva na coluna `analise_cache`

## Modificações Realizadas

### 1. CotacaoManager (cotacao_manager.py)

#### Método `insert_cotacao_item`
```python
def insert_cotacao_item(
    self,
    cotacao_id: int,
    *,
    # ... outros parâmetros
    analise_local: Optional[Dict[str, Any]] = None,
    analise_cache: Optional[Dict[str, Any]] = None,  # ✅ NOVO
    # ... demais parâmetros
) -> Optional[int]:
```

#### Método `insert_cotacao_item_from_result`
```python
def insert_cotacao_item_from_result(
    self,
    cotacao_id: int,
    resultado_produto: Dict[str, Any],
    *,
    # ... outros parâmetros
    analise_local: Optional[Dict[str, Any]] = None,
    analise_cache: Optional[Dict[str, Any]] = None,  # ✅ NOVO
    # ... demais parâmetros
) -> Optional[int]:
```

#### Método `insert_missing_item`
```python
def insert_missing_item(
    self,
    cotacao_id: int,
    *,
    # ... outros parâmetros
    analise_local: Optional[Dict[str, Any]] = None,
    analise_cache: Optional[Dict[str, Any]] = None,  # ✅ NOVO
    # ... demais parâmetros
) -> Optional[int]:
```

### 2. Busca em Duas Fases (app.py)

#### Marcação de Produtos por Fase
```python
# Fase LOCAL
for produto in lista:
    produto["fase_origem"] = "local"

# Fase CACHE  
for produto in lista_cache:
    produto["fase_origem"] = "cache"
```

#### Lógica de Análise Diferenciada
```python
fase_origem = produto.get("fase_origem", "local")

if fase_origem == "cache":
    # Produto da fase cache - usar analise_cache
    analise_cache = {
        "query_id": qid, 
        "score": produto.get("score"), 
        "alternativa": False
    }
    if produto.get('llm_relatorio'):
        analise_cache["llm_relatorio"] = produto.get('llm_relatorio')
    analise_local = None
else:
    # Produto da fase local - usar analise_local
    analise_local = {
        "query_id": qid, 
        "score": produto.get("score"), 
        "alternativa": False
    }
    if produto.get('llm_relatorio'):
        analise_local["llm_relatorio"] = produto.get('llm_relatorio')
    analise_cache = None
```

## Estrutura da Tabela `cotacoes_itens`

```sql
-- Colunas relevantes na tabela cotacoes_itens
CREATE TABLE cotacoes_itens (
    id SERIAL PRIMARY KEY,
    cotacao_id INTEGER,
    produto_id INTEGER,
    origem TEXT, -- 'local', 'externo', etc.
    
    -- Análises diferenciadas por fase
    analise_local JSONB,   -- Para produtos da Fase LOCAL
    analise_cache JSONB,   -- Para produtos da Fase CACHE
    
    -- Outros campos...
    item_nome TEXT,
    item_preco DECIMAL,
    quantidade INTEGER,
    status BOOLEAN,
    pedido TEXT
);
```

## Comportamento do Sistema

### Fluxo de Busca e Análise

1. **Fase LOCAL**: 
   - Busca produtos com `origem='local'`
   - Análise LLM salva em `analise_local`

2. **Fase CACHE** (se necessário):
   - Busca produtos com `origem='externo'` 
   - Análise LLM salva em `analise_cache`

3. **Inserção na Cotação**:
   - Produtos locais: `analise_local` preenchida, `analise_cache` NULL
   - Produtos cache: `analise_cache` preenchida, `analise_local` NULL

### Estrutura da Análise

```json
// Para produtos da Fase LOCAL (analise_local)
{
    "query_id": "Q1",
    "score": 0.95,
    "alternativa": false,
    "llm_relatorio": {
        "compatibilidade": "Alta",
        "preco_beneficio": "Excelente",
        "observacoes": "Produto ideal para as necessidades"
    }
}

// Para produtos da Fase CACHE (analise_cache)
{
    "query_id": "Q2", 
    "score": 0.78,
    "alternativa": false,
    "llm_relatorio": {
        "compatibilidade": "Média",
        "preco_beneficio": "Bom",
        "observacoes": "Alternativa viável do cache externo"
    }
}
```

## Vantagens

1. **Rastreabilidade**: Distingue análises por fonte de origem dos produtos
2. **Qualidade**: Preserva diferenças entre produtos locais e cache
3. **Auditoria**: Facilita análise de performance por fase
4. **Flexibilidade**: Permite tratamentos diferenciados por origem

## Consultas Úteis

### Produtos por Fase
```sql
-- Produtos da fase local
SELECT * FROM cotacoes_itens 
WHERE analise_local IS NOT NULL AND analise_cache IS NULL;

-- Produtos da fase cache
SELECT * FROM cotacoes_itens 
WHERE analise_cache IS NOT NULL AND analise_local IS NULL;
```

### Estatísticas por Fase
```sql
-- Contagem por fase
SELECT 
    CASE 
        WHEN analise_local IS NOT NULL THEN 'LOCAL'
        WHEN analise_cache IS NOT NULL THEN 'CACHE'
        ELSE 'INDEFINIDO'
    END as fase,
    COUNT(*) as total
FROM cotacoes_itens 
GROUP BY fase;
```

## Compatibilidade

✅ **Retrocompatibilidade mantida**: Produtos existentes continuam funcionando
✅ **Migração transparente**: Sistema detecta fase automaticamente  
✅ **Testes validados**: Sintaxe verificada e funcionamento confirmado
