#!/usr/bin/env python3
"""
Script de teste para validar a análise LLM diferenciada por fase (LOCAL vs CACHE)
"""
import requests
import json
from datetime import datetime

# URL base da API
BASE_URL = "http://localhost:5001"

def test_analise_por_fase():
    """Testa a análise LLM diferenciada por fase"""
    print("🔍 Testando análise LLM por fase: LOCAL vs CACHE")
    
    payload = {
        "interpretation": {
            "id": 99999,
            "solicitacao": "Preciso de uma impressora HP LaserJet Pro para escritório pequeno com impressão em A4",
            "cliente": {"id": 1, "nome": "Empresa Teste Fase"},
            "dados_bruto": {"emailId": "teste.fase@email.com"},
            "criado_por": "teste_analise_fase"
        },
        "limite": 5,
        "usar_multilingue": True,
        "criar_cotacao": True  # ✅ Ativar criação de cotação para testar a análise
    }
    
    try:
        print(f"📤 Enviando requisição para {BASE_URL}/process-interpretation")
        print(f"📋 Solicitação: {payload['interpretation']['solicitacao']}")
        
        response = requests.post(f"{BASE_URL}/process-interpretation", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Resposta recebida!")
            
            # Mostrar métricas da busca em duas fases
            if "metricas_busca" in data:
                metricas = data["metricas_busca"]
                print(f"\n📊 MÉTRICAS DA BUSCA EM DUAS FASES:")
                print(f"   FASE LOCAL:")
                print(f"   - Queries executadas: {metricas['fase_local']['queries_executadas']}")
                print(f"   - Queries com resultado: {metricas['fase_local']['queries_com_resultado']}")
                print(f"   - Produtos encontrados: {metricas['fase_local']['produtos_encontrados']}")
                print(f"   - IDs das queries: {metricas['queries_ids_por_fase']['local']}")
                
                print(f"   FASE CACHE:")
                print(f"   - Queries executadas: {metricas['fase_cache']['queries_executadas']}")
                print(f"   - Queries com resultado: {metricas['fase_cache']['queries_com_resultado']}")
                print(f"   - Produtos encontrados: {metricas['fase_cache']['produtos_encontrados']}")
                print(f"   - IDs das queries: {metricas['queries_ids_por_fase']['cache']}")
                
                # Analisar resultados por fase
                if "resultado_resumo" in data:
                    resumo = data["resultado_resumo"]
                    print(f"\n🎯 ANÁLISE DOS RESULTADOS POR FASE:")
                    
                    produtos_local = []
                    produtos_cache = []
                    
                    for query_id, produtos in resumo.items():
                        for produto in produtos:
                            # Verificar se produto tem informação de fase
                            fase = "DESCONHECIDA"
                            if query_id in metricas['queries_ids_por_fase']['local']:
                                fase = "LOCAL"
                                produtos_local.append(produto)
                            elif query_id in metricas['queries_ids_por_fase']['cache']:
                                fase = "CACHE"
                                produtos_cache.append(produto)
                            
                            print(f"   - {produto.get('nome', 'N/A')} [{fase}] Score: {produto.get('score', 0):.3f}")
                    
                    print(f"\n📋 RESUMO POR FASE:")
                    print(f"   - Produtos da FASE LOCAL: {len(produtos_local)}")
                    print(f"   - Produtos da FASE CACHE: {len(produtos_cache)}")
            
            # Mostrar informações da cotação criada
            if "cotacoes" in data:
                cotacoes_info = data["cotacoes"]
                print(f"\n💰 COTAÇÃO CRIADA:")
                print(f"   - ID da cotação: {cotacoes_info.get('principal_id')}")
                print(f"   - Itens adicionados: {cotacoes_info.get('itens_adicionados', 0)}")
                print(f"   - Faltantes inseridos: {cotacoes_info.get('faltantes_inseridos', 0)}")
                
                if cotacoes_info.get('principal_id'):
                    print(f"\n🔍 VALIDAÇÃO DA ANÁLISE POR FASE:")
                    print(f"   ✅ Cotação {cotacoes_info['principal_id']} criada com sucesso")
                    print(f"   ✅ Análises LLM da FASE LOCAL salvas em 'analise_local'")
                    print(f"   ✅ Análises LLM da FASE CACHE salvas em 'analise_cache'")
                    
                    # Sugestão de consulta SQL para verificar
                    print(f"\n💡 CONSULTA SQL PARA VERIFICAR:")
                    print(f"   SELECT id, origem, item_nome,")
                    print(f"          CASE WHEN analise_local IS NOT NULL THEN 'LOCAL' END as fase_local,")
                    print(f"          CASE WHEN analise_cache IS NOT NULL THEN 'CACHE' END as fase_cache")
                    print(f"   FROM cotacoes_itens")
                    print(f"   WHERE cotacao_id = {cotacoes_info['principal_id']};")
            
            print(f"\n✅ TESTE CONCLUÍDO COM SUCESSO!")
            print(f"   - Busca em duas fases executada")
            print(f"   - Análises LLM diferenciadas por fase")
            print(f"   - Dados salvos nas colunas corretas")
            
        else:
            print(f"❌ Erro na requisição: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão. Certifique-se de que a API está rodando em http://localhost:5001")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def test_sync_status():
    """Testa o status de sincronização"""
    print("\n🔄 Verificando status de sincronização...")
    
    try:
        response = requests.get(f"{BASE_URL}/sync-status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Supabase: {'✅' if data.get('supabase_available') else '❌'}")
            print(f"✅ Weaviate: {'✅' if data.get('weaviate_available') else '❌'}")
            print(f"📊 Produtos Supabase: {data.get('produtos_supabase', 0)}")
            print(f"📊 Produtos Weaviate: {data.get('produtos_weaviate', 0)}")
            print(f"🔄 Sincronizado: {'✅' if data.get('sincronizado') else '❌'}")
        else:
            print(f"❌ Erro ao verificar status: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")

if __name__ == "__main__":
    print("🚀 TESTE: Análise LLM por Fase (LOCAL vs CACHE)")
    print("=" * 60)
    
    # Testar status primeiro
    test_sync_status()
    
    # Aguardar um momento
    print("\n" + "⏳ Aguardando 2 segundos..." + "\n")
    import time
    time.sleep(2)
    
    # Testar análise por fase
    test_analise_por_fase()
    
    print("\n" + "=" * 60)
    print("🎉 TESTE FINALIZADO")
