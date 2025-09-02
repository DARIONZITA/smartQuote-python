# Migração dos Modelos Locais para API do Hugging Face

## 📋 Resumo das Mudanças

Este documento descreve a migração do sistema SmartQuote de modelos locais de embedding (SentenceTransformers) para uma API do Hugging Face hospedada em `dnzita/smartquote`.

## ✅ Mudanças Implementadas

### 1. **Arquivos Modificados**

#### `weaviate_client.py`
- **Adicionada**: Nova classe `HuggingFaceEmbeddingClient` para gerenciar conexões com a API
- **Modificada**: Classe `WeaviateManager` para usar o cliente da API ao invés de modelos locais
- **Removidas**: Dependências de `SentenceTransformers` locais
- **Atualizadas**: Funções de geração de embeddings nos métodos `indexar_produto`

#### `search_engine.py` 
- **Modificada**: Função `buscar_hibrido_ponderado` para usar embeddings da API
- **Mapeamento de modelos**: 
  - `vetor_portugues` → modelo `bertimbau`
  - `vetor_multilingue` → modelo `mpnet`

#### `app.py` e `main.py`
- **Atualizadas**: Verificações de disponibilidade de modelos para usar `supports_multilingual`
- **Mantida**: Compatibilidade com o sistema de espaços vetoriais existente

#### `requirements.txt`
- **Removida**: `sentence-transformers>=2.2.0`
- **Adicionada**: `gradio-client>=0.8.0`

### 2. **Nova API de Embeddings**

#### Endpoint: `dnzita/smartquote`
```python
from gradio_client import Client

client = Client("dnzita/smartquote")
result = client.predict(
    texts="Texto para embedding",
    model_choice="mpnet",  # ou "bertimbau"
    api_name="/predict"
)
```

#### Modelos Disponíveis:
- **`bertimbau`**: Modelo português (equivalente ao anterior `neuralmind/bert-base-portuguese-cased`)
- **`mpnet`**: Modelo multilíngue (equivalente ao anterior `paraphrase-multilingual-mpnet-base-v2`)

### 3. **Arquivos de Teste**

#### `test_hf_api.py`
- **Criado**: Script de teste para validar a integração com a API
- **Funcionalidade**: Testa ambos os modelos e verifica dimensões dos embeddings

## 🔧 Como Usar

### 1. **Instalação das Dependências**
```bash
cd scripts/busca_local
pip install -r requirements.txt
```

### 2. **Teste da Integração**
```bash
python test_hf_api.py
```

### 3. **Uso Normal do Sistema**
O sistema continua funcionando normalmente. As mudanças são transparentes para o usuário final.

## 📊 Benefícios da Migração

### ✅ **Vantagens**
- **Redução de recursos locais**: Não precisa mais carregar modelos grandes na memória local
- **Menor tempo de inicialização**: Conexão rápida com a API vs. carregamento de modelos
- **Menor uso de disco**: Sem necessidade de armazenar modelos localmente
- **Escalabilidade**: API pode ser otimizada e escalada independentemente
- **Manutenção**: Modelos podem ser atualizados na API sem mudanças de código

### ⚠️ **Considerações**
- **Dependência de rede**: Requer conexão com internet para funcionar
- **Latência**: Pode haver pequena latência adicional por chamada à API
- **Disponibilidade**: Depende da disponibilidade do serviço Hugging Face

## 🧪 Testes Realizados

- ✅ **Conexão com API**: Testada com sucesso
- ✅ **Geração de embeddings**: Modelos `bertimbau` e `mpnet` funcionando
- ✅ **Compatibilidade**: Sistema mantém funcionalidade existente
- ✅ **Dimensões**: Embeddings com 768 dimensões (conforme esperado)

## 🔄 Rollback (se necessário)

Para reverter as mudanças, seria necessário:

1. Restaurar `requirements.txt` com `sentence-transformers>=2.2.0`
2. Reverter mudanças em `weaviate_client.py` para usar modelos locais
3. Reverter mudanças em `search_engine.py`, `app.py` e `main.py`
4. Reinstalar dependências: `pip install sentence-transformers`

## 📝 Notas Técnicas

- **Formato de resposta da API**: A API retorna diretamente uma lista de floats representando o embedding
- **Tratamento de erros**: Implementado tratamento robusto de erros de conexão e API
- **Cache de IDs**: Mantido o sistema de cache existente para melhor performance
- **Compatibilidade**: Mantida total compatibilidade com o schema Weaviate existente

---

## 🚀 Status: Migração Completa ✅

A migração foi concluída com sucesso e está pronta para uso em produção.
