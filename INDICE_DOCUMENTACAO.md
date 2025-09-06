# 📚 Índice de Documentação - API Busca Local

## 🎯 Navegação Rápida

### 📖 **Para Desenvolvedores**
- **[🏠 README Principal](README.md)** - Visão geral e setup da API
- **[🔧 Como Consumir](CONSUMO_API_BUSCA_LOCAL.md)** - Guia completo para integração
- **[📋 Como Rodar](COMO-RODAR.md)** - Setup e execução em ambiente local

### 📊 **Sistema de Relatórios (Novo)**
- **[📊 Estrutura da Tabela](TABELA_RELATORIOS.md)** - Funcionamento completo da auditoria
- **[🔍 Exemplos de Consultas](EXEMPLOS_CONSULTAS_RELATORIOS.md)** - SQL práticos para análises
- **[🎨 Diagramas Visuais](DIAGRAMA_RELATORIOS.md)** - Fluxos e estruturas visuais

### 🔄 **Histórico e Migrações**
- **[🔄 Migração HuggingFace](MIGRACAO_API_HF.md)** - Mudança de provedor LLM

---

## 🚀 Começando Rapidamente

### 👨‍💻 **Para Desenvolvedores Iniciantes**
1. **[📋 COMO-RODAR.md](COMO-RODAR.md)** - Configure seu ambiente local
2. **[🔧 CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md)** - Faça sua primeira requisição
3. **[📊 TABELA_RELATORIOS.md](TABELA_RELATORIOS.md)** - Entenda o sistema de auditoria

### 🏢 **Para Integração em Produção**
1. **[🏠 README.md](README.md)** - Deploy e configuração da API
2. **[🔧 CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md)** - Endpoints e analise_locals
3. **[🔍 EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md)** - Analytics e monitoramento

### 📊 **Para Análise de Dados**
1. **[🎨 DIAGRAMA_RELATORIOS.md](DIAGRAMA_RELATORIOS.md)** - Entenda a estrutura visual
2. **[🔍 EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md)** - Consultas SQL prontas
3. **[📊 TABELA_RELATORIOS.md](TABELA_RELATORIOS.md)** - Campos e relacionamentos

---

## 📋 Resumo dos Documentos

| 📄 Documento | 🎯 Objetivo | 👥 Público | ⏱️ Tempo Leitura |
|-------------|------------|------------|------------------|
| [README.md](README.md) | Visão geral e setup | Todos | 10 min |
| [CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md) | Guia de integração | Desenvolvedores | 15 min |
| [TABELA_RELATORIOS.md](TABELA_RELATORIOS.md) | Sistema de auditoria | Desenvolvedores/Analistas | 12 min |
| [EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md) | Consultas SQL práticas | Analistas/DBAs | 8 min |
| [DIAGRAMA_RELATORIOS.md](DIAGRAMA_RELATORIOS.md) | Estruturas visuais | Todos | 6 min |
| [COMO-RODAR.md](COMO-RODAR.md) | Setup local | Desenvolvedores | 5 min |
| [MIGRACAO_API_HF.md](MIGRACAO_API_HF.md) | Histórico de mudanças | Equipe técnica | 3 min |

---

## 🔍 Busca por Tópicos

### 🛠️ **Setup e Configuração**
- **Instalação local**: [COMO-RODAR.md](COMO-RODAR.md)
- **Deploy produção**: [README.md](README.md#-deploy-independente)
- **Configuração .env**: [README.md](README.md#variáveis-de-ambiente-env)

### 🔌 **Integração API**
- **Endpoints disponíveis**: [CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md#-endpoints-da-api)
- **Exemplos de analise_local**: [CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md#-exemplos-de-uso)
- **Códigos de erro**: [CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md#-códigos-de-resposta)

### 📊 **Sistema de Relatórios**
- **Como funciona**: [TABELA_RELATORIOS.md](TABELA_RELATORIOS.md#-visão-geral)
- **Estrutura JSON**: [TABELA_RELATORIOS.md](TABELA_RELATORIOS.md#-estrutura-do-json-analise_local)
- **Consultas prontas**: [EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md#-consultas-básicas)
- **Fluxo visual**: [DIAGRAMA_RELATORIOS.md](DIAGRAMA_RELATORIOS.md#-fluxograma-de-processamento)

### 🗄️ **Base de Dados**
- **Schema cotações**: [CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md#-esquema-da-base-de-dados)
- **Migração faltantes**: [CONSUMO_API_BUSCA_LOCAL.md](CONSUMO_API_BUSCA_LOCAL.md#-migração-sistema-faltantes)
- **Índices recomendados**: [EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md#índices-recomendados)

### 🧠 **LLM e Análise**
- **Preservação relatórios**: [TABELA_RELATORIOS.md](TABELA_RELATORIOS.md#-produtos-encontrados-mas-rejeitados-pela-llm)
- **Critérios aplicados**: [EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md#6-critérios-mais-aplicados-pela-llm)
- **Performance LLM**: [EXEMPLOS_CONSULTAS_RELATORIOS.md](EXEMPLOS_CONSULTAS_RELATORIOS.md#7-taxa-de-sucesso-da-llm-por-período)

---

## 🆕 Novidades da Versão 2.0

### ✨ **Principais Melhorias**
- **[Rastreabilidade Completa](TABELA_RELATORIOS.md#-benefícios-da-nova-estrutura)** - Todos os processamentos geram relatórios
- **[Preservação LLM](TABELA_RELATORIOS.md#-produtos-encontrados-mas-rejeitados-pela-llm)** - Análises mantidas mesmo em rejeições
- **[Migração Faltantes](CONSUMO_API_BUSCA_LOCAL.md#-migração-sistema-faltantes)** - De coluna para tabela estruturada
- **[Analytics Avançados](EXEMPLOS_CONSULTAS_RELATORIOS.md#-performance-e-métricas)** - Métricas e KPIs detalhados

### 🔧 **Melhorias Técnicas**
- **[Status Detalhados](DIAGRAMA_RELATORIOS.md#-status-possíveis-e-cores)** - 6 tipos de status para análise
- **[Consultas Otimizadas](EXEMPLOS_CONSULTAS_RELATORIOS.md#-dicas-de-performance)** - Índices e queries eficientes
- **[Estrutura JSONB](TABELA_RELATORIOS.md#-estrutura-do-json-analise_local)** - Flexível e escalável

---

## 🤝 Contribuindo

### 📝 **Melhorando a Documentação**
1. Identifique gaps ou informações desatualizadas
2. Crie/edite o documento relevante
3. Atualize este índice se necessário
4. Mantenha consistência de formato

### 🔗 **Convenções de Links**
- Use links relativos: `[texto](ARQUIVO.md)`
- Inclua âncoras para seções: `[texto](ARQUIVO.md#seção)`
- Teste todos os links antes de commitar

---

*Índice atualizado em: 3 de setembro de 2025*  
*Versão: 2.0 - Sistema completo de auditoria implementado*
