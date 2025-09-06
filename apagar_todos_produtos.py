import weaviate
import weaviate.classes as wvc
from config import API_KEY_WEAVIATE

def apagar_todos_produtos():
    # Conecte ao cluster (ajuste cluster_url se necessário)
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url="ylwtqkqjsfstdhecszyr5a.c0.us-west3.gcp.weaviate.cloud",
        auth_credentials=wvc.init.Auth.api_key(API_KEY_WEAVIATE),
        additional_config=wvc.init.AdditionalConfig(
            timeout=wvc.init.Timeout(init=60, query=60, insert=180)
        )
    )
    collection = client.collections.get("Produtos")
    print("Buscando todos os objetos para apagar...")
    after = None
    total = 0
    while True:
        res = collection.query.fetch_objects(
            limit=100,
            after=after,
            return_properties=["produto_id"],
        )
        objetos = getattr(res, "objects", None) or []
        if not objetos:
            break
        for obj in objetos:
            uuid_obj = getattr(obj, "uuid", None) or getattr(obj, "id", None)
            if uuid_obj:
                try:
                    collection.data.delete_by_id(uuid=uuid_obj)
                    print(f"Removido: {uuid_obj}")
                    total += 1
                except Exception as e:
                    print(f"Erro ao remover {uuid_obj}: {e}")
        after = getattr(res, "next_page_cursor", None)
        if not after:
            break
    print(f"Total removido: {total}")

if __name__ == "__main__":
    apagar_todos_produtos()