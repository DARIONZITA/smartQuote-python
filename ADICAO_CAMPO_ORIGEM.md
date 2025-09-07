# Adição do Campo 'origem' ao Schema Weaviate

## Problema Identificado

O erro indicava que a propriedade `origem` não existia no schema da classe `Produtos` no Weaviate:

```
Query call with protocol GRPC search failed with message no such prop with name 'origem' found in class 'Produtos' in the schema.
```

## Causa Raiz

O sistema de busca em duas fases tentava filtrar produtos por `origem`, mas:

1. **Schema não tinha o campo**: A classe `Produtos` não incluía a propriedade `origem`
2. **Produtos não tinham o campo**: Os dados indexados não continham informação de origem
3. **Filtros falhavam**: Queries com `Filter.by_property("origem")` resultavam em erro

## Soluções Implementadas

### 1. Adição do Campo 'origem' ao Schema

**Arquivo**: `weaviate_client.py` - Função `definir_schema()`

**Antes:**
```python
properties=[
    Property(name="produto_id", data_type=DataType.INT),
    Property(name="nome", data_type=DataType.TEXT),
    Property(name="descricao", data_type=DataType.TEXT),
    Property(name="preco", data_type=DataType.NUMBER),
    Property(name="categoria", data_type=DataType.TEXT),
    Property(name="tags", data_type=DataType.TEXT_ARRAY),
    Property(name="estoque", data_type=DataType.INT),
],
```

**Depois (✅ Corrigido):**
```python
properties=[
    Property(name="produto_id", data_type=DataType.INT),
    Property(name="nome", data_type=DataType.TEXT),
    Property(name="descricao", data_type=DataType.TEXT),
    Property(name="preco", data_type=DataType.NUMBER),
    Property(name="categoria", data_type=DataType.TEXT),
    Property(name="tags", data_type=DataType.TEXT_ARRAY),
    Property(name="estoque", data_type=DataType.INT),
    Property(name="origem", data_type=DataType.TEXT),  # ✅ ADICIONADO
],
```

### 2. Inclusão do Campo 'origem' na Indexação

**Arquivo**: `weaviate_client.py` - Função `indexar_produto()`

**Inserção de Novos Produtos:**
```python
dados_weaviate = {
    "produto_id": produto_id,
    "nome": nome,
    "descricao": descricao,
    "preco": preco,
    "categoria": categoria,
    "tags": tags_array,
    "estoque": estoque,
    "origem": dados_produto.get("origem", "local")  # ✅ ADICIONADO
}
```

**Atualização de Produtos Existentes:**
```python
dados_weaviate = {
    "produto_id": produto_id,
    "nome": nome,
    "descricao": descricao,
    "preco": preco,
    "categoria": categoria,
    "tags": tags_array,
    "estoque": estoque,
    "origem": dados_produto.get("origem", "local")  # ✅ ADICIONADO
}
```

### 3. Script de Migração

**Arquivo**: `recriar_schema_origem.py`

O script realiza:

1. **Remoção da coleção existente** (sem campo `origem`)
2. **Recriação do schema** (com campo `origem`)
3. **Reindexação de todos os produtos** (incluindo campo `origem`)
4. **Validação** do resultado

```python
# Deletar coleção existente
if weaviate_manager.client.collections.exists("Produtos"):
    weaviate_manager.client.collections.delete("Produtos")

# Recriar schema
weaviate_manager.definir_schema()

# Reindexar produtos com campo 'origem'
for produto in produtos:
    if 'origem' not in produto:
        produto['origem'] = 'local'  # Padrão para produtos do Supabase

weaviate_manager.indexar_produtos(produtos)
```

## Lógica de Origem

### Valores Padrão
- **Produtos do Supabase**: `origem = 'local'`
- **Produtos de cache externo**: `origem = 'externo'`
- **Produtos sem especificação**: `origem = 'local'` (padrão)

### Comportamento das Fases

**Fase LOCAL:**
```python
filtros_local["origem"] = "local"
# Resultado: Apenas produtos com origem='local'
```

**Fase CACHE:**
```python
filtros_cache["origem"] = "externo"
# Resultado: Apenas produtos com origem='externo'
```

## Estrutura do Schema Atualizada

```python
Classe: Produtos
├── produto_id (INT)
├── nome (TEXT)
├── descricao (TEXT)
├── preco (NUMBER)
├── categoria (TEXT)
├── tags (TEXT_ARRAY)
├── estoque (INT)
└── origem (TEXT) ✅ NOVO CAMPO

Vetores:
├── vetor_portugues
└── vetor_multilingue
```

## Exemplo de Produto Indexado

```json
{
  "produto_id": 123,
  "nome": "HP LaserJet Pro M404dw",
  "descricao": "Impressora laser monocromática",
  "preco": 350000.0,
  "categoria": "Impressoras",
  "tags": ["HP", "Laser", "Monocromática"],
  "estoque": 5,
  "origem": "local"  // ✅ NOVO CAMPO
}
```

## Consultas Suportadas

### Filtro por Origem
```python
# Buscar apenas produtos locais
filter_local = wvc.query.Filter.by_property("origem").equal("local")

# Buscar apenas produtos externos
filter_externo = wvc.query.Filter.by_property("origem").equal("externo")
```

### Busca Híbrida com Filtro
```python
# Busca semântica apenas em produtos locais
collection.query.near_vector(
    near_vector=embedding,
    filters=wvc.query.Filter.by_property("origem").equal("local"),
    limit=10
)

# Busca BM25 apenas em produtos externos
collection.query.bm25(
    query="impressora HP",
    filters=wvc.query.Filter.by_property("origem").equal("externo"),
    limit=10
)
```

## Processo de Migração

### Para Aplicar as Mudanças:

1. **Executar o script de migração**:
   ```bash
   python recriar_schema_origem.py
   ```

2. **Verificar resultado**:
   - Schema recriado com campo `origem`
   - Produtos reindexados com origem='local'
   - Filtros funcionando corretamente

3. **Testar busca em duas fases**:
   ```bash
   python test_filtro_origem.py
   ```

### Impacto da Migração:

- ✅ **Sem perda de dados**: Produtos são reindexados automaticamente
- ✅ **Compatibilidade**: Sistema continua funcionando normalmente
- ✅ **Filtros funcionais**: Busca em duas fases agora funciona corretamente
- ✅ **Performance**: Filtros Weaviate são otimizados

## Validação

### Comandos de Teste:
```bash
# Testar schema e sintaxe
python -c "import weaviate_client; print('OK')"

# Executar migração
python recriar_schema_origem.py

# Testar filtros de origem
python test_filtro_origem.py

# Testar busca em duas fases
python test_duas_fases.py
```

### Resultados Esperados:
- ✅ Schema criado com campo `origem`
- ✅ Produtos indexados com origem='local'
- ✅ Filtros de origem funcionando
- ✅ Busca em duas fases operacional

## Status

✅ **Schema atualizado**
✅ **Campo 'origem' adicionado**
✅ **Indexação corrigida**
✅ **Script de migração criado**
⏳ **Migração pendente** (executar `recriar_schema_origem.py`)

## Próximos Passos

1. **Executar migração**: `python recriar_schema_origem.py`
2. **Testar funcionalidade**: `python test_filtro_origem.py`
3. **Validar busca em duas fases**: Verificar se não há mais erros de schema
