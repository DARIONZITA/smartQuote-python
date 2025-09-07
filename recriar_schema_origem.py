#!/usr/bin/env python3
"""
Script para recriar o schema do Weaviate com o campo 'origem' e reindexar produtos
"""
import os
import sys

# Configurar path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from config import load_env
load_env()

from weaviate_client import WeaviateManager
from supabase_client import SupabaseManager

def recriar_schema_com_origem():
    """Recria o schema do Weaviate incluindo o campo 'origem'"""
    print("🔄 Recriando schema do Weaviate com campo 'origem'")
    
    try:
        # Inicializar managers
        weaviate_manager = WeaviateManager()
        weaviate_manager.connect()
        
        supabase_manager = SupabaseManager()
        supabase_manager.connect()
        
        # Deletar coleção existente se existir
        print("🗑️ Removendo coleção 'Produtos' existente...")
        try:
            if weaviate_manager.client.collections.exists("Produtos"):
                weaviate_manager.client.collections.delete("Produtos")
                print("✅ Coleção 'Produtos' removida")
            else:
                print("ℹ️ Coleção 'Produtos' não existia")
        except Exception as e:
            print(f"⚠️ Erro ao remover coleção: {e}")
        
        # Recriar schema com campo 'origem'
        print("🏗️ Criando novo schema com campo 'origem'...")
        weaviate_manager.definir_schema()
        print("✅ Novo schema criado")
        
        # Reindexar produtos do Supabase
        print("📊 Buscando produtos do Supabase...")
        produtos = supabase_manager.get_produtos()
        
        if produtos:
            print(f"📝 Reindexando {len(produtos)} produtos...")
            
            # Adicionar campo 'origem' aos produtos se não existir
            for produto in produtos:
                if 'origem' not in produto:
                    produto['origem'] = 'local'  # Produtos do Supabase são 'local' por padrão
            
            # Indexar produtos
            weaviate_manager.indexar_produtos(produtos)
            print(f"✅ {len(produtos)} produtos reindexados com sucesso")
        else:
            print("⚠️ Nenhum produto encontrado no Supabase")
        
        # Verificar resultado
        print("🔍 Verificando resultado...")
        collection = weaviate_manager.client.collections.get("Produtos")
        res = collection.aggregate.over_all(total_count=True)
        total_produtos = res.total_count if res else 0
        print(f"📊 Total de produtos no Weaviate: {total_produtos}")
        
        # Testar busca com filtro de origem
        print("🧪 Testando filtro de origem...")
        import weaviate.classes as wvc
        
        # Buscar produtos locais
        res_local = collection.query.fetch_objects(
            limit=5,
            filters=wvc.query.Filter.by_property("origem").equal("local"),
            return_properties=["nome", "origem"]
        )
        
        locais_encontrados = len(res_local.objects) if res_local and res_local.objects else 0
        print(f"✅ Produtos com origem='local': {locais_encontrados}")
        
        if locais_encontrados > 0:
            print("📋 Primeiros produtos locais:")
            for i, obj in enumerate(res_local.objects[:3], 1):
                nome = obj.properties.get('nome', 'N/A')
                origem = obj.properties.get('origem', 'N/A')
                print(f"  {i}. {nome} | Origem: {origem}")
        
        print("🎉 Schema recriado e produtos reindexados com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao recriar schema: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            if 'weaviate_manager' in locals():
                weaviate_manager.close()
        except:
            pass

if __name__ == "__main__":
    print("🚀 RECRIAÇÃO DO SCHEMA WEAVIATE")
    print("=" * 50)
    recriar_schema_com_origem()
    print("=" * 50)
    print("✅ PROCESSO CONCLUÍDO")
