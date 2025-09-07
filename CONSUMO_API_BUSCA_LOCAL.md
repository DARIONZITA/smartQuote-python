# Consumo - O status da cotação (`cotacoes.status`) passa a ser "incompleta" sempre que existir pelo menos um item em `cotacoes_itens` com `status = false`. Caso não haja itens pendentes, a cotação é "completa".
- **Sincronização automática**: Antes de cada busca, o sistema agora sincroniza automaticamente com o Supabase, incluindo a remoção de produtos que foram apagados da base de dados. Isso garante que os resultados sempre reflitam o estado atual da base de dados.

## Endpoints principais

### 1) Health check
- Método/rota: `GET /health`
- Resposta: status de serviços (weaviate, supabase, decomposer).

### 2) Status de sincronização
- Método/rota: `GET /sync-status`
- Resposta: 
```json
{
  "timestamp": "2025-09-06T12:34:56.000Z",
  "supabase_available": true,
  "weaviate_available": true,
  "produtos_supabase": 150,
  "produtos_weaviate": 150,
  "sincronizado": true
}
```

### 3) Sincronização manual
- Método/rota: `POST /sync-products`
- Resposta:
```json
{
  "status": "success",
  "produtos_total_supabase": 150,
  "produtos_novos_indexados": 2,
  "produtos_removidos": 3,
  "falhas": 0,
  "timestamp": "2025-09-06T12:34:56.000Z"
}
```

### 4) Processar interpretação (principal)
- Método/rota: `POST /process-interpretation`
- **Nota**: Este endpoint agora executa sincronização automática antes da busca.hon de Busca Local (smartQuote)

Este documento orienta a app consumidora sobre como usar a API Python de busca local, o que esperar das respostas e como ler os dados no banco após a refatoração de "faltantes".

## Visão geral das mudanças

- A coluna `cotacoes.faltantes` não é mais utilizada para registrar itens não encontrados.
- Quando um item não é encontrado na busca local, é criado um registro diretamente em `cotacoes_itens` com:
  - `status = false` (boolean) indicando que o item ainda não foi encontrado/atendido;
  - `pedido` (text) preenchido com a consulta que antes ficava em `faltantes.query_sugerida`.
- O status da cotação (`cotacoes.status`) passa a ser “incompleta” sempre que existir pelo menos um item em `cotacoes_itens` com `status = false`. Caso não haja itens pendentes, a cotação é “completa”.

## Endpoints principais

### 1) Health check
- Método/rota: `GET /health`
- Resposta: status de serviços (weaviate, supabase, decomposer).

### 2) Processar interpretação (principal)
- Método/rota: `POST /process-interpretation`
- Body (exemplo mínimo):
```json
{
  "interpretation": {
    "id": 123,
    "solicitacao": "Preciso de 10 switches gerenciáveis, 24 portas, PoE",
    "cliente": { "id": 45, "nome": "ACME" },
    "dados_bruto": { "emailId": "abc" }
  },
  "limite": 5,
  "usar_multilingue": true,
  "criar_cotacao": true
}
```
- Resposta (campos relevantes):
```json
{
  "status": "success",
  "processed_at": "2025-09-06T12:34:56.000Z",
  "interpretation_id": 123,
  "dados_extraidos": { /* brief estruturado pelo LLM */ },
  "resultado_resumo": { "Q1": [ { "nome": "...", "produto_id": 1, "score": 0.87 } ] },
  "metricas_busca": {
    "fase_local": {
      "queries_executadas": 3,
      "produtos_encontrados": 2,
      "queries_com_resultado": 2
    },
    "fase_cache": {
      "queries_executadas": 1,
      "produtos_encontrados": 1,
      "queries_com_resultado": 1
    },
    "queries_ids_por_fase": {
      "local": ["Q1", "Q2"],
      "cache": ["Q3"]
    }
  },
  "faltantes": [
    {
      "id": "Q4",
      "tipo": "item",
      "nome": "Switch PoE",
      "categoria": "rede",
      "quantidade": 10,
      "query_sugerida": "Switch gerenciável PoE 24 portas",
      "item_id": 5555
    }
  ],
  "cotacoes": {
    "principal_id": 987,
    "itens_adicionados": 3,
    "faltantes_inseridos": 1
  }
}
```
- Notas:
  - **BUSCA EM DUAS FASES**: O sistema agora executa busca sequencial:
    1. **FASE LOCAL**: Busca produtos com `origem = "local"` primeiro
    2. **FASE CACHE**: Para queries sem resultado, busca produtos com `origem = "externo"`
  - O campo `metricas_busca` mostra estatísticas detalhadas de cada fase
  - O campo `faltantes` permanece na resposta apenas para referência/UX (tarefas de pesquisa externa). Ele NÃO é mais gravado dentro de `cotacoes`.
  - Cada item em `faltantes` agora inclui `item_id`: o ID do registro criado em `cotacoes_itens` para facilitar operações posteriores.
  - Quando `criar_cotacao` for `true`, a API cria:
    - um `prompt`;
    - uma `cotacao` (status inicialmente “completa” a menos que haja itens faltantes);
    - itens encontrados em `cotacoes_itens`;
    - para cada “faltante”, um item em `cotacoes_itens` com `status = false` e `pedido = query_sugerida`.
    - após inserir itens, o status da cotação é recalculado: “incompleta” se houver item com `status=false`.

### 5) Busca híbrida direta
- Método/rota: `POST /hybrid-search`
- **Nota**: Este endpoint também executa sincronização automática antes da busca.
- Body: `{ "pesquisa": "texto", "filtros": { ... }, "limite": 10 }`
- Resposta: lista agregada de resultados (sem criação de cotação).

## Banco de dados (tabelas e campos relevantes)

### Tabela: cotacoes
- Campos relevantes:
  - `id` (int)
  - `prompt_id` (int)
  - `status` (text):
    - “incompleta” quando existir pelo menos um item em `cotacoes_itens.status = false`.
    - “completa” quando não houver itens pendentes.
  - `orcamento_geral` (numeric): atualizado automaticamente somando `item_preco * quantidade` dos itens.

### Tabela: cotacoes_itens
- Novos campos:
  - `status` (boolean):
    - `true` para itens encontrados/atendidos (padrão para itens locais);
    - `false` para itens “não encontrados” criados pela API Python.
  - `pedido` (text): a consulta sugerida para pesquisa externa (era `faltantes.query_sugerida`).
- Outros campos de interesse:
  - `produto_id` (int, opcional): presente para itens locais com produto no catálogo;
  - `origem` (text): "local", "api", "web" ou "externo";
  - `item_nome`, `item_descricao`, `item_preco`, `item_moeda`, `quantidade`;
  - `analise_local` (jsonb): metadados úteis (ex.: `{ "query_id": "Q2" }`).

### Tabela: relatorios
- Usada para armazenar análises locais (ex.: analise_local com `llm_relatorio`).
- Atualizada/append quando novos itens são adicionados na cotação.

## Como a app consumidora deve se adaptar

1) Exibição de itens pendentes
- Antes: ler `cotacoes.faltantes`.
- Agora: consultar `cotacoes_itens` com `status = false` para a `cotacao_id` desejada.
- Mostrar `item_nome`/`pedido` e permitir ações (ex.: pesquisar na web, associar um produto, etc.).

2) Status da cotação
- Considerar `cotacoes.status` como fonte da verdade:
  - “incompleta” se existir item pendente (`status=false`).
  - “completa” caso contrário.

3) Orçamento
- `orcamento_geral` ignora itens pendentes (que normalmente têm `item_preco` nulo).

## Exemplos úteis

### Exemplo de item “não encontrado” em `cotacoes_itens`
```json
{
  "id": 5555,
  "cotacao_id": 987,
  "origem": "web",
  "produto_id": null,
  "item_nome": "Item não encontrado",
  "item_descricao": "Item não encontrado na busca local",
  "item_tags": ["faltante", "item"],
  "item_preco": null,
  "item_moeda": "AOA",
  "quantidade": 10,
  "status": false,
  "pedido": "Switch gerenciável PoE 24 portas",
  "analise_local": { "query_id": "Q2" }
}
```

### Consulta SQL para contar itens pendentes por cotação
```sql
SELECT c.id, c.status, COUNT(ci.id) AS pendentes
FROM cotacoes c
LEFT JOIN cotacoes_itens ci ON ci.cotacao_id = c.id AND ci.status = false
GROUP BY c.id, c.status
ORDER BY c.id DESC;
```

## Migração de banco (se ainda não aplicada)
```sql
ALTER TABLE cotacoes_itens
  ADD COLUMN IF NOT EXISTS status boolean DEFAULT true,
  ADD COLUMN IF NOT EXISTS pedido text;

-- opcional: remover a coluna antiga, se existir e não houver dependências
-- ALTER TABLE cotacoes DROP COLUMN IF EXISTS faltantes;
```

## Boas práticas de integração
- Tratar `faltantes` no analise_local apenas como informação auxiliar; a fonte para pendências é `cotacoes_itens.status=false`.
- Após resolver um item pendente (ex.: associar a um produto), atualizar o registro em `cotacoes_itens` para `status=true` e, opcionalmente, preencher `produto_id`, `item_preco`, etc.; depois, recalcular o status da `cotacao` (a API Python já fornece um endpoint que recalcula internamente quando ela cria/atualiza, mas sua app pode fazer esse ajuste no backend principal também).

## Suporte
Em caso de dúvidas, ver `app.py` (endpoint `/process-interpretation`) e `cotacao_manager.py` (criação/atualização de cotações e itens) neste repositório.
