#!/usr/bin/env python3
"""
Script de teste para demonstrar a busca em duas fases (LOCAL → CACHE)
"""
import requests
import json
from datetime import datetime

# URL base da API (ajustar conforme necessário)
BASE_URL = "http://localhost:5001"

def test_process_interpretation_two_phases():
    """Testa o endpoint /process-interpretation com busca em duas fases"""
    print("🔍 Testando busca em duas fases: LOCAL → CACHE")
    
    payload = {
        "interpretation": {
            "id": 12345,
            "solicitacao": "HP Laserjet Pro MFP4104dw/fdn/fdw Monochrome Laser Multifunction Printer A4 Office Equipment Document Printer",
            "cliente": {"id": 1, "nome": "Empresa Teste"},
            "dados_bruto": {"emailId": "test@email.com"}
        },
        "limite": 3,
        "usar_multilingue": True,
        "criar_cotacao": False
    }
    
    try:
        print(f"📤 Enviando requisição para {BASE_URL}/process-interpretation")
        print(f"📋 Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        response = requests.post(f"{BASE_URL}/process-interpretation", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Resposta recebida:")
            
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
            
            # Mostrar resumo dos resultados
            if "resultado_resumo" in data:
                print(f"\n🎯 RESULTADOS FINAIS:")
                for query_id, produtos in data["resultado_resumo"].items():
                    print(f"   {query_id}: {len(produtos)} produto(s)")
                    for i, produto in enumerate(produtos, 1):
                        print(f"     {i}. {produto.get('nome', 'N/A')} - Score: {produto.get('score', 0):.3f}")
            
            # Mostrar itens faltantes
            if "faltantes" in data and data["faltantes"]:
                print(f"\n❌ ITENS FALTANTES: {len(data['faltantes'])}")
                for item in data["faltantes"]:
                    print(f"   - {item.get('nome', 'N/A')} (Query: {item.get('query_sugerida', 'N/A')})")
            else:
                print(f"\n✅ TODOS OS ITENS FORAM ENCONTRADOS!")
            
            return data
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def test_health():
    """Testa health check"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API saudável: {data['status']}")
            return True
        else:
            print(f"❌ API não saudável: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testando API de Busca Local - BUSCA EM DUAS FASES")
    print("=" * 60)
    
    # Testar health primeiro
    if not test_health():
        print("❌ API não está disponível. Verifique se o servidor está rodando.")
        exit(1)
    
    print("\n" + "=" * 60)
    
    # Testar busca em duas fases
    result = test_process_interpretation_two_phases()
    
    print("\n" + "=" * 60)
    print("🎉 Teste concluído!")
    
    if result and "metricas_busca" in result:
        metricas = result["metricas_busca"]
        total_local = metricas["fase_local"]["queries_com_resultado"]
        total_cache = metricas["fase_cache"]["queries_com_resultado"]
        total_faltantes = len(result.get("faltantes", []))
        
        print(f"📈 RESUMO FINAL:")
        print(f"   - Resolvidas na FASE LOCAL: {total_local}")
        print(f"   - Resolvidas na FASE CACHE: {total_cache}")
        print(f"   - Ainda faltantes: {total_faltantes}")
        print(f"   - Total de queries: {total_local + total_cache + total_faltantes}")
    else:
        print("⚠️ Não foi possível obter métricas da busca")
