#!/usr/bin/env python3
"""
Script de teste para demonstrar a sincronização automática
"""
import requests
import json
from datetime import datetime

# URL base da API (ajustar conforme necessário)
BASE_URL = "http://localhost:5001"

def test_sync_status():
    """Testa o endpoint de status de sincronização"""
    print("🔍 Verificando status de sincronização...")
    try:
        response = requests.get(f"{BASE_URL}/sync-status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def test_manual_sync():
    """Testa sincronização manual"""
    print("\n🔄 Executando sincronização manual...")
    try:
        response = requests.post(f"{BASE_URL}/sync-products")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sincronização: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def test_hybrid_search():
    """Testa busca híbrida com sincronização automática"""
    print("\n🔍 Testando busca híbrida (com sincronização automática)...")
    try:
        payload = {
            "pesquisa": "switch",
            "limite": 3,
            "usar_multilingue": True
        }
        response = requests.post(f"{BASE_URL}/hybrid-search", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Busca híbrida:")
            print(f"   - Total encontrados: {data.get('total_encontrados', 0)}")
            print(f"   - Espaços pesquisados: {data.get('espacos_pesquisados', [])}")
            print(f"   - Produtos:")
            for i, produto in enumerate(data.get('resultados', [])[:3], 1):
                print(f"     {i}. {produto.get('nome', 'N/A')} (Score: {produto.get('score', 0):.3f})")
            return data
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def test_health():
    """Testa health check"""
    print("\n❤️ Verificando saúde da API...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

if __name__ == "__main__":
    print("🧪 Testando API de Busca Local com Sincronização Automática")
    print("=" * 60)
    
    # Testar health primeiro
    health = test_health()
    if not health or health.get("status") != "healthy":
        print("❌ API não está saudável. Verifique se o servidor está rodando.")
        exit(1)
    
    # Testar status de sincronização
    status_inicial = test_sync_status()
    
    # Testar sincronização manual
    sync_result = test_manual_sync()
    
    # Testar status após sincronização
    if sync_result:
        print("\n🔍 Verificando status após sincronização...")
        status_final = test_sync_status()
    
    # Testar busca híbrida (que inclui sincronização automática)
    search_result = test_hybrid_search()
    
    print("\n" + "=" * 60)
    print("🎉 Testes concluídos!")
    
    if status_inicial and status_inicial.get("sincronizado"):
        print("✅ Sistema está sincronizado")
    else:
        print("⚠️ Sistema pode estar dessincronizado - verifique logs")
        
    if search_result and search_result.get("total_encontrados", 0) > 0:
        print("✅ Busca híbrida funcionando")
    else:
        print("⚠️ Busca híbrida não retornou resultados")
