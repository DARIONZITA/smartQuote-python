# Busca em Duas Fases - Implementação Completa

## Visão Geral
Implementada funcionalidade de busca em duas fases sequenciais na rota `/process-interpretation`:

1. **FASE LOCAL**: Busca produtos com `origem = "local"`
2. **FASE CACHE**: Para queries sem resultado na fase local, busca produtos com `origem = "externo"`

## Modificações Implementadas

### 1. Função `executar_estrutura_de_queries` (Melhorada)
- **Novo parâmetro**: `filtro_origem: str = None`
- **Funcionalidade**: Aplica filtro de origem nos produtos durante a busca
- **Logs**: Mostra qual filtro de origem está sendo aplicado

### 2. Nova Função `executar_busca_duas_fases`
```python
def executar_busca_duas_fases(
    weaviate_manager: WeaviateManager,
    estrutura: List[Dict[str, Any]],
    limite_resultados: int = LIMITE_PADRAO_RESULTADOS,
    usar_multilingue: bool = True,
    verbose: bool = False
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str], Dict[str, Any]]:
```

**Fluxo de Execução**:
1. Executa busca com `origem = "local"`
2. Identifica queries sem resultado ou com produtos rejeitados pela LLM
3. Para essas queries, executa busca com `origem = "externo"`
4. Mescla resultados priorizando produtos locais
5. Retorna resultados finais + métricas detalhadas

### 3. Função `processar_interpretacao` (Atualizada)
- **Substituída chamada**: `executar_estrutura_de_queries` → `executar_busca_duas_fases`
- **Nova resposta**: Inclui campo `metricas_busca` com estatísticas detalhadas

## Estrutura das Métricas

```json
{
  "metricas_busca": {
    "fase_local": {
      "queries_executadas": 5,
      "produtos_encontrados": 8,
      "queries_com_resultado": 3
    },
    "fase_cache": {
      "queries_executadas": 2,
      "produtos_encontrados": 2,
      "queries_com_resultado": 2
    },
    "queries_ids_por_fase": {
      "local": ["Q1", "Q2", "Q3", "Q4", "Q5"],
      "cache": ["Q3", "Q5"]
    }
  }
}
```

## Lógica de Priorização

### Critérios para Fase Cache
Uma query vai para a fase cache se:
- **Vazio**: Nenhum produto encontrado na fase local
- **Rejeitado**: Produtos encontrados mas rejeitados pela LLM

### Mesclagem de Resultados
- **Prioridade**: Produtos locais sempre têm prioridade
- **Substituição**: Cache só substitui se fase local falhou
- **Preservação**: Relatórios LLM são preservados em ambas as fases

## Benefícios da Implementação

### ✅ **Performance Otimizada**
- Busca local primeiro (geralmente mais rápida)
- Cache só executa quando necessário
- Reduz chamadas desnecessárias

### ✅ **Transparência Total**
- Métricas detalhadas de cada fase
- Logs informativos durante execução
- Rastreabilidade completa do processo

### ✅ **Compatibilidade Mantida**
- API response mantém estrutura existente
- Novos campos são aditivos
- Não quebra integrações existentes

### ✅ **Inteligência de Busca**
- Prioriza produtos locais
- Fallback automático para cache
- LLM avalia qualidade em ambas as fases

## Cenários de Uso

### Cenário 1: Sucesso na Fase Local
```
INPUT: "Preciso de switches Cisco"
FASE LOCAL: Encontra 3 switches Cisco locais
FASE CACHE: Não executada
RESULTADO: 3 produtos locais
```

### Cenário 2: Fallback para Cache
```
INPUT: "Preciso de switches D-Link"
FASE LOCAL: Nenhum produto D-Link local
FASE CACHE: Encontra 2 switches D-Link externos
RESULTADO: 2 produtos externos
```

### Cenário 3: Busca Mista
```
INPUT: ["switches Cisco", "roteadores TP-Link"]
FASE LOCAL: Encontra switches Cisco (local)
FASE CACHE: Encontra roteadores TP-Link (externo)
RESULTADO: 1 produto local + 1 produto externo
```

## Logs de Exemplo

```
🚀 Iniciando busca em duas fases: LOCAL → CACHE
📍 FASE 1: Buscando produtos com origem='local'
🔍 Espaços de busca: ['vetor_portugues', 'vetor_multilingue']
🎯 Filtro de origem: local
➡️ Executando Q1 [item] | Query: switches gerenciáveis 24 portas
🎯 Índice escolhido pela LLM: 0 - Switch Cisco SG350-24P
🔄 FASE 2 (CACHE): Buscando produtos com origem='externo' para 1 queries
Queries para cache: ['Q2']
✅ Cache resolveu query Q2
📊 RESUMO: 1 local + 1 cache + 0 faltantes = 2 queries
```

## Testes

### Script de Teste
Execute `test_duas_fases.py` para validar:
```bash
python test_duas_fases.py
```

### Validação Manual
```bash
curl -X POST http://localhost:5001/process-interpretation \
  -H "Content-Type: application/json" \
  -d '{
    "interpretation": {
      "id": 123,
      "solicitacao": "Preciso de switches e roteadores",
      "cliente": {"id": 1, "nome": "Teste"}
    },
    "limite": 3,
    "usar_multilingue": true
  }'
```

## Próximos Passos
1. ✅ Implementação completa
2. ✅ Testes de sintaxe aprovados
3. ✅ Documentação atualizada
4. 🔄 Teste em ambiente real
5. 📊 Monitoramento de performance das duas fases
