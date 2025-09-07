#!/usr/bin/env python3
"""
Script de teste para verificar se a filtragem por origem está funcionando corretamente
"""
import requests
import json
from datetime import datetime

# URL base da API
BASE_URL = "http://localhost:5001"

def test_filtro_origem():
    """Testa se o filtro de origem está funcionando"""
    print("🔍 Testando filtro de origem na busca híbrida")
    
    # Teste 1: Busca apenas produtos locais
    payload_local = {
        "pesquisa": "impressora HP",
        "filtros": {"origem": "local"},
        "limite": 5,
        "usar_multilingue": True
    }
    
    print(f"\n📤 Teste 1: Busca apenas produtos LOCAIS")
    print(f"Filtros: {payload_local['filtros']}")
    
    try:
        response = requests.post(f"{BASE_URL}/hybrid-search", json=payload_local)
        if response.status_code == 200:
            data = response.json()
            resultados = data.get("resultados", [])
            print(f"✅ Encontrados {len(resultados)} produtos locais")
            
            # Verificar se todos são realmente locais
            for i, produto in enumerate(resultados[:3], 1):
                origem = produto.get("origem", "N/A")
                nome = produto.get("nome", "N/A")
                score = produto.get("score", 0)
                print(f"  {i}. {nome} | Origem: {origem} | Score: {score:.3f}")
                
                if origem != "local":
                    print(f"    ⚠️ ERRO: Produto não é local!")
        else:
            print(f"❌ Erro na busca local: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro no teste local: {e}")
    
    # Teste 2: Busca apenas produtos externos
    payload_externo = {
        "pesquisa": "impressora HP",
        "filtros": {"origem": "externo"},
        "limite": 5,
        "usar_multilingue": True
    }
    
    print(f"\n📤 Teste 2: Busca apenas produtos EXTERNOS")
    print(f"Filtros: {payload_externo['filtros']}")
    
    try:
        response = requests.post(f"{BASE_URL}/hybrid-search", json=payload_externo)
        if response.status_code == 200:
            data = response.json()
            resultados = data.get("resultados", [])
            print(f"✅ Encontrados {len(resultados)} produtos externos")
            
            # Verificar se todos são realmente externos
            for i, produto in enumerate(resultados[:3], 1):
                origem = produto.get("origem", "N/A")
                nome = produto.get("nome", "N/A")
                score = produto.get("score", 0)
                print(f"  {i}. {nome} | Origem: {origem} | Score: {score:.3f}")
                
                if origem != "externo":
                    print(f"    ⚠️ ERRO: Produto não é externo!")
        else:
            print(f"❌ Erro na busca externa: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro no teste externo: {e}")
    
    # Teste 3: Busca sem filtro (todos os produtos)
    payload_todos = {
        "pesquisa": "impressora HP",
        "limite": 5,
        "usar_multilingue": True
    }
    
    print(f"\n📤 Teste 3: Busca SEM filtro de origem (todos)")
    
    try:
        response = requests.post(f"{BASE_URL}/hybrid-search", json=payload_todos)
        if response.status_code == 200:
            data = response.json()
            resultados = data.get("resultados", [])
            print(f"✅ Encontrados {len(resultados)} produtos (todos)")
            
            # Verificar mix de origens
            origens = {}
            for produto in resultados:
                origem = produto.get("origem", "desconhecida")
                origens[origem] = origens.get(origem, 0) + 1
            
            print(f"📊 Distribuição por origem:")
            for origem, count in origens.items():
                print(f"  - {origem}: {count} produtos")
        else:
            print(f"❌ Erro na busca geral: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro no teste geral: {e}")

def test_busca_duas_fases():
    """Testa se a busca em duas fases está usando filtros corretamente"""
    print("\n🚀 Testando busca em duas fases")
    
    payload = {
        "interpretation": {
            "id": 88888,
            "solicitacao": "Preciso de uma impressora laser monocromática HP para escritório",
            "cliente": {"id": 1, "nome": "Empresa Teste Filtro"},
            "dados_bruto": {"emailId": "teste.filtro@email.com"}
        },
        "limite": 3,
        "usar_multilingue": True,
        "criar_cotacao": False
    }
    
    try:
        response = requests.post(f"{BASE_URL}/process-interpretation", json=payload)
        if response.status_code == 200:
            data = response.json()
            
            if "metricas_busca" in data:
                metricas = data["metricas_busca"]
                print(f"📊 MÉTRICAS DA BUSCA EM DUAS FASES:")
                print(f"   FASE LOCAL: {metricas['fase_local']['produtos_encontrados']} produtos")
                print(f"   FASE CACHE: {metricas['fase_cache']['produtos_encontrados']} produtos")
                
                # Verificar se as fases foram executadas corretamente
                if metricas['fase_local']['produtos_encontrados'] > 0:
                    print(f"   ✅ Fase LOCAL encontrou produtos")
                else:
                    print(f"   ⚠️ Fase LOCAL não encontrou produtos")
                
                if metricas['fase_cache']['queries_executadas'] > 0:
                    if metricas['fase_cache']['produtos_encontrados'] > 0:
                        print(f"   ✅ Fase CACHE encontrou produtos")
                    else:
                        print(f"   ⚠️ Fase CACHE executada mas não encontrou produtos")
                else:
                    print(f"   ✅ Fase CACHE não foi necessária")
            
            print(f"✅ Busca em duas fases funcionando!")
        else:
            print(f"❌ Erro na busca duas fases: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro no teste duas fases: {e}")

if __name__ == "__main__":
    print("🚀 TESTE: Filtros de Origem")
    print("=" * 50)
    
    # Testar filtros de origem na busca híbrida
    test_filtro_origem()
    
    # Testar busca em duas fases
    test_busca_duas_fases()
    
    print("\n" + "=" * 50)
    print("🎉 TESTES FINALIZADOS")
