import weaviate
import weaviate.classes as wvc
from gradio_client import Client
from typing import Dict, Any, List
import warnings
import sys
import os
import numpy as np
import time

# Importar configurações usando try/except para robustez
try:
    from config import WEAVIATE_HOST, WEAVIATE_PORT, API_KEY_WEAVIATE
except ImportError:
    # Fallback para import relativo
    try:
        from .config import WEAVIATE_HOST, WEAVIATE_PORT, API_KEY_WEAVIATE
    except ImportError:
        # Último recurso: definir valores padrão
        print("⚠️ Aviso: Não foi possível importar configurações do Weaviate. Usando valores padrão.")
        WEAVIATE_HOST = "localhost"
        WEAVIATE_PORT = 8080
        API_KEY_WEAVIATE = None

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
warnings.filterwarnings("ignore", category=DeprecationWarning)

class HuggingFaceEmbeddingClient:
    """Cliente para obter embeddings via API do Hugging Face com retries"""

    def __init__(self, space_name: str | None = None, max_retries: int | None = None, backoff_seconds: float | None = None):
        self.client = None
        # Permite configurar o Space via variável de ambiente HUGGINGFACE_SPACE
        self.space_name = space_name or os.environ.get("HUGGINGFACE_SPACE", "dnzita/smartquote")
        # Configura tentativas e backoff via env se disponível
        self.max_retries = int(os.environ.get("EMBEDDING_MAX_RETRIES", max_retries or 5))
        self.backoff_seconds = float(os.environ.get("EMBEDDING_RETRY_BACKOFF", backoff_seconds or 3.0))
        # Timeout configurável para operações de embedding
        self.embedding_timeout = int(os.environ.get("EMBEDDING_TIMEOUT", 120))
        
    def connect(self, timeout: int = 30):
        """Conecta ao cliente da API do Hugging Face com timeout configurável"""
        try:
            print(f"Conectando à API do Hugging Face... (space: {self.space_name})")
            hf_token = os.environ.get("HUGGINGFACE_TOKEN")
            
            # Criar cliente sem parâmetros httpx customizados inicialmente
            # O gradio_client gerencia seus próprios timeouts internamente
            if hf_token:
                self.client = Client(self.space_name, hf_token=hf_token)
            else:
                self.client = Client(self.space_name)
            
            print("✅ Conectado à API do Hugging Face")
        except Exception as e:
            print(f"❌ Erro ao conectar à API do Hugging Face: {e}")
            raise
            
    def encode(self, text: str, model_choice: str = "mpnet") -> List[float]:
        """
        Gera embedding para um texto usando a API do Hugging Face
        
        Args:
            text: Texto para gerar embedding
            model_choice: Modelo a usar ('mpnet' ou 'bertimbau')
            
        Returns:
            Lista de floats representando o embedding
        """
        if not self.client:
            print("🔄 Conectando ao cliente de embeddings (inicialização lazy)...")
            self.connect()
            
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()  # Definir antes do try para estar disponível no except
            try:
                print(f"🔍 Tentando gerar embedding (tentativa {attempt}/{self.max_retries}, timeout={self.embedding_timeout}s)...")
                
                result = self.client.predict(
                    texts=text,
                    model_choice=model_choice,
                    api_name="/predict"
                )
                
                elapsed = time.time() - start_time
                print(f"✅ Embedding gerado com sucesso em {elapsed:.2f}s")

                # Gradio retorna [[...]] para um texto, precisa "achatar"
                if isinstance(result, list) and len(result) > 0:
                    # Se veio [[...]], pega só o primeiro (para um texto)
                    if isinstance(result[0], list):
                        return result[0]  # Retorna apenas o embedding do primeiro texto
                    else:
                        return result  # Já está no formato correto
                else:
                    raise Exception(f"Formato de resposta inesperado: {type(result)}")

            except Exception as e:
                last_exc = e
                elapsed = time.time() - start_time
                msg = str(e).lower()
                
                # Detecta tipo de erro
                is_timeout = "timeout" in msg or "timed out" in msg
                is_connection = any(t in msg for t in ["connection", "handshake", "reset", "aborted"])
                transient = is_timeout or is_connection or any(t in msg for t in [
                    "temporarily unavailable",
                    "temporary failure",
                    "max retries",
                ])
                
                error_type = "⏱️ TIMEOUT" if is_timeout else "🔌 CONEXÃO" if is_connection else "❌ ERRO"
                print(f"{error_type} ao gerar embedding após {elapsed:.2f}s (tentativa {attempt}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries and transient:
                    # Recria o cliente e espera com backoff exponencial
                    print(f"🔄 Reconectando ao HuggingFace Space {self.space_name}...")
                    try:
                        self.client = None  # Força reconexão completa
                        self.connect()
                    except Exception as conn_err:
                        print(f"⚠️ Falha ao reconectar: {conn_err}")
                    
                    sleep_s = self.backoff_seconds * (2 ** (attempt - 1))
                    actual_sleep = min(sleep_s, 15)
                    print(f"⏸️ Aguardando {actual_sleep:.1f}s antes da próxima tentativa...")
                    time.sleep(actual_sleep)
                    continue
                # Sem retries restantes ou erro não transitório
                break

        error_summary = f"Falha após {self.max_retries} tentativas"
        if last_exc:
            if "timeout" in str(last_exc).lower():
                error_summary += f" - HuggingFace API não respondeu dentro de {self.embedding_timeout}s. Considere: 1) Aumentar EMBEDDING_TIMEOUT, 2) Verificar status do Space {self.space_name}, 3) Usar modelo alternativo."
        
        print(f"❌ {error_summary}")
        raise last_exc if last_exc else Exception("Falha desconhecida ao gerar embedding")

class WeaviateManager:
    def __init__(self):
        self.client = None
        self.embedding_client = None
        self.MULTI_OK = True  # Ambos os modelos estão disponíveis via API
        # cache leve opcional de ids já indexados, para reduzir consultas repetidas
        self._known_ids: set[int] = set()
        
    def connect(self):
        """Conecta ao Weaviate e inicializa cliente de embeddings"""
        print("A conectar ao Weaviate...")
        try:
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=WEAVIATE_HOST,  # URL do cluster no WCS a partir da variável de ambiente
                auth_credentials=wvc.init.Auth.api_key(API_KEY_WEAVIATE),
                additional_config=wvc.init.AdditionalConfig(
                    timeout=wvc.init.Timeout(init=60, query=60, insert=180)
                )
            )
            print("Conectado ao Weaviate v4 (REST+gRPC)")
        except Exception as e:
            print(f"Erro na conexão: {e}")
            raise
            
        print("Inicializando cliente de embeddings da API Hugging Face...")
        try:
            self.embedding_client = HuggingFaceEmbeddingClient()
            # Lazy init: não conectar agora, apenas quando necessário
            print("⏳ Cliente de embeddings será inicializado sob demanda")
        except Exception as e:
            print(f"❌ Falha ao criar cliente de embeddings: {e}")
            raise
    
    def _ensure_embedding_client(self):
        """Garante que o cliente de embeddings está conectado (lazy initialization)"""
        if self.embedding_client and not self.embedding_client.client:
            try:
                print("🔗 Conectando cliente de embeddings (primeira vez)...")
                self.embedding_client.connect(timeout=60)  # Timeout maior
                print("✅ Cliente de embeddings pronto")
            except Exception as e:
                print(f"⚠️ Falha ao conectar embedding client: {e}")
                raise Exception(f"Não foi possível inicializar cliente de embeddings: {e}")
        
    def definir_schema(self):
        """Cria a classe 'Produtos' com vetores baseada nos dados do Supabase."""
        from weaviate.classes.config import Configure, Property, DataType
        try:
            if self.client.collections.exists("Produtos"):
                # Já existe: reutiliza a coleção existente para evitar 422
                print("Schema 'Produtos' já existe. Reutilizando coleção existente.")
                return
            else:
                print("Criando novo schema...")
        except Exception as e:
            print(f"Aviso ao limpar schema: {e}")
        
        # Schema baseado nos campos do Supabase
        self.client.collections.create(
            name="Produtos",
            properties=[
                Property(name="produto_id", data_type=DataType.INT),
                Property(name="nome", data_type=DataType.TEXT),
                Property(name="descricao", data_type=DataType.TEXT),
                Property(name="preco", data_type=DataType.NUMBER),
                Property(name="categoria", data_type=DataType.TEXT),
                Property(name="tags", data_type=DataType.TEXT_ARRAY),
                Property(name="estoque", data_type=DataType.INT),
                Property(name="origem", data_type=DataType.TEXT),  # Adicionado para busca em duas fases
            ],
            vectorizer_config=[
                Configure.NamedVectors.none(name="vetor_portugues"),
                Configure.NamedVectors.none(name="vetor_multilingue")
            ]
        )
        print("Schema 'Produtos' criado com dois vetores nomeados.")
        
    def indexar_produto(self, dados_produto: dict):
        """
        Indexa ou atualiza produto no Weaviate conforme o fluxo inteligente:
        - Se não existe, insere com embeddings.
        - Se existe, compara campos importantes.
          - Se texto mudou, atualiza tudo e recalcula embeddings.
          - Se só mudou preço/estoque, atualiza apenas esses campos.
        """
        import uuid
        produto_id = int(dados_produto.get('id') or dados_produto.get('produto_id') or 0)
        if not produto_id:
            print("Produto sem id, ignorado.")
            return
        uuid_produto = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"produto-{produto_id}"))
        collection = self.client.collections.get("Produtos")
        filtro = wvc.query.Filter.by_property("produto_id").equal(produto_id)
        res = collection.query.fetch_objects(
            limit=1,
            filters=filtro,
            return_properties=["produto_id", "nome", "descricao", "categoria", "tags", "preco", "estoque"],
        )
        objeto_existente = res.objects[0] if res and getattr(res, "objects", None) else None
        nome = dados_produto.get('nome', '')
        descricao = dados_produto.get('descricao', '')
        categoria = dados_produto.get('categoria', '') or dados_produto.get('modelo', '')
        tags_raw = dados_produto.get('tags', '')
        if isinstance(tags_raw, str):
            tags_array = [tag.strip() for tag in tags_raw.split(',') if tag.strip()] if tags_raw else []
        elif isinstance(tags_raw, list):
            tags_array = tags_raw
        else:
            tags_array = []
        preco = float(dados_produto.get('preco', 0)) if dados_produto.get('preco') else 0.0
        estoque = int(dados_produto.get('estoque', 0)) if dados_produto.get('estoque') else 0
        if not objeto_existente:
            # Garantir que o cliente de embeddings está pronto (lazy init)
            self._ensure_embedding_client()
            
            texto_para_embedding = f"Nome: {nome}. Categoria: {categoria}. Tags: {', '.join(tags_array)}. Descrição: {descricao}"
            
            # Gerar embeddings usando a API do Hugging Face
            emb_pt = self.embedding_client.encode(texto_para_embedding, model_choice="bertimbau")
            emb_multi = self.embedding_client.encode(texto_para_embedding, model_choice="mpnet") if self.MULTI_OK else None
            
            vectors = {"vetor_portugues": emb_pt}
            if emb_multi is not None:
                vectors["vetor_multilingue"] = emb_multi
            dados_weaviate = {
                "produto_id": produto_id,
                "nome": nome,
                "descricao": descricao,
                "preco": preco,
                "categoria": categoria,
                "tags": tags_array,
                "estoque": estoque,
                "origem": dados_produto.get("origem", "local")  # Adicionado para busca em duas fases
            }
            # Usa o dicionário 'vectors' preparado acima para evitar enviar None
            collection.data.insert(
                uuid=uuid_produto,
                properties=dados_weaviate,
                vector=vectors
            )
            print(f"✔ Produto novo indexado: {nome} (id={produto_id})")
            self._known_ids.add(produto_id)
            return
        atual = objeto_existente.properties
        mudou_texto = (
            atual.get("nome", "") != nome or
            atual.get("descricao", "") != descricao or
            atual.get("categoria", "") != categoria or
            atual.get("tags", []) != tags_array
        )
        mudou_numerico = (
            atual.get("preco", 0.0) != preco or
            atual.get("estoque", 0) != estoque
        )
        if mudou_texto:
            # Garantir que o cliente de embeddings está pronto (lazy init)
            self._ensure_embedding_client()
            
            texto_para_embedding = f"Nome: {nome}. Categoria: {categoria}. Tags: {', '.join(tags_array)}. Descrição: {descricao}"
            
            # Gerar embeddings usando a API do Hugging Face
            emb_pt = self.embedding_client.encode(texto_para_embedding, model_choice="bertimbau")
            emb_multi = self.embedding_client.encode(texto_para_embedding, model_choice="mpnet") if self.MULTI_OK else None
            
            vectors = {"vetor_portugues": emb_pt}
            if emb_multi is not None:
                vectors["vetor_multilingue"] = emb_multi
            dados_weaviate = {
                "produto_id": produto_id,
                "nome": nome,
                "descricao": descricao,
                "preco": preco,
                "categoria": categoria,
                "tags": tags_array,
                "estoque": estoque,
                "origem": dados_produto.get("origem", "local")  # Adicionado para busca em duas fases
            }
            collection.data.update(uuid=uuid_produto, properties=dados_weaviate, vector=vectors)
            print(f"✏️ Produto atualizado (texto mudou): {nome} (id={produto_id})")
        elif mudou_numerico:
            dados_update = {
                "preco": preco,
                "estoque": estoque
            }
            collection.data.update(uuid=uuid_produto, properties=dados_update)
            print(f"✏️ Produto atualizado (só preço/estoque): {nome} (id={produto_id})")

    def indexar_produtos(self, produtos: list[dict]):
        """
        Indexa uma lista de produtos no Weaviate.
        Processa cada produto individualmente usando o método indexar_produto.
        """
        if not produtos:
            print("📭 Nenhum produto para indexar")
            return
        
        print(f"🔄 Indexando {len(produtos)} produtos...")
        sucessos = 0
        falhas = 0
        
        for produto in produtos:
            try:
                self.indexar_produto(produto)
                sucessos += 1
            except Exception as e:
                falhas += 1
                produto_id = produto.get('id', 'desconhecido')
                print(f"❌ Erro ao indexar produto {produto_id}: {e}")
        
        print(f"✅ Indexação concluída: {sucessos} sucessos, {falhas} falhas")

    def remover_orfaos(self, valid_produto_ids: set[int]) -> dict:
        """Remove objetos em Weaviate cujo produto_id não existe na base relacional.
        Retorna métricas: { 'removidos': int, 'falhas': int, 'total_encontrados': int }
        """
        import sys
        removidos, falhas, total = 0, 0, 0
        try:
            collection = self.client.collections.get("Produtos")
        except Exception as e:
            print(f"⚠️ Falha ao obter coleção 'Produtos' para limpeza: {e}")
            return {"removidos": 0, "falhas": 1, "total_encontrados": 0}

        # Paginação usando cursor 'after'
        after: str | None = None
        while True:
            try:
                res = collection.query.fetch_objects(
                    limit=100,
                    after=after,
                    return_properties=["produto_id"],
                )
            except Exception as e:
                print(f"⚠️ Erro ao paginar objetos na limpeza: {e}", file=sys.stderr)
                break

            objetos = getattr(res, "objects", None) or []
            if not objetos:
                break

            for obj in objetos:
                total += 1
                try:
                    pid = obj.properties.get("produto_id") if hasattr(obj, "properties") else None
                    uuid_obj = getattr(obj, "uuid", None) or getattr(obj, "id", None)
                    if pid is None or int(pid) not in valid_produto_ids:
                        if uuid_obj is None:
                            # Fallback para reconstruir UUID determinístico se possível
                            import uuid as _uuid
                            try:
                                if pid is not None:
                                    uuid_obj = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"produto-{int(pid)}"))
                            except Exception:
                                uuid_obj = None
                        try:
                            if uuid_obj is not None:
                                collection.data.delete_by_id(uuid=uuid_obj)
                                removidos += 1
                            else:
                                falhas += 1
                        except Exception as e:
                            falhas += 1
                            print(f"❌ Falha ao remover objeto órfão (produto_id={pid}): {e}", file=sys.stderr)
                except Exception as e:
                    falhas += 1
                    print(f"⚠️ Erro ao avaliar objeto na limpeza: {e}", file=sys.stderr)

            # Próxima página
            after = getattr(res, "next_page_cursor", None)
            if not after:
                break

        if removidos:
            print(f"🧹 Limpeza Weaviate: removidos {removidos} objeto(s) órfão(s).", file=sys.stderr)
        return {"removidos": removidos, "falhas": falhas, "total_encontrados": total}

    def produto_existe(self, produto_id: int) -> bool:
        """Verifica se já existe um objeto com o produto_id dado no Weaviate."""
        try:
            if produto_id in self._known_ids:
                return True
            collection = self.client.collections.get("Produtos")
            filtro = wvc.query.Filter.by_property("produto_id").equal(produto_id)
            res = collection.query.fetch_objects(
                limit=1,
                filters=filtro,
                return_properties=["produto_id"],
            )
            existe = bool(res and getattr(res, "objects", None))
            if existe:
                self._known_ids.add(int(produto_id))
            return existe
        except Exception as e:
            print(f"⚠️ Falha ao verificar existência do produto {produto_id} no Weaviate: {e}")
            # Em caso de erro na checagem, considerar que não existe para tentar indexar
            return False

    def sincronizar_com_supabase(self, produtos_supabase: list[dict]) -> dict:
        """Sincroniza: garante que Weaviate reflita o Supabase em tempo de execução.
        Ações:
        - Remove objetos cujo produto_id não existe na lista fornecida
        - Indexa produtos que ainda não existem
        Retorna métricas: { 'novos': int, 'removidos': int, 'falhas': int }
        """
        if not produtos_supabase:
            # Segurança: não remover tudo quando a lista vier vazia
            return {"novos": 0, "removidos": 0, "falhas": 0}
        novos, falhas, removidos = 0, 0, 0

        # Purga de órfãos baseada nos IDs atuais do Supabase
        try:
            valid_ids = {int(p.get("id") or p.get("produto_id") or 0) for p in produtos_supabase if (p.get("id") or p.get("produto_id"))}
        except Exception:
            valid_ids = set()
        try:
            if valid_ids:
                res_cleanup = self.remover_orfaos(valid_ids)
                removidos = int(res_cleanup.get("removidos", 0))
        except Exception as e:
            print(f"⚠️ Falha ao remover órfãos durante sincronização: {e}")

        # Indexar o que faltar
        for p in produtos_supabase:
            try:
                pid = int(p.get("id") or p.get("produto_id") or 0)
            except Exception:
                pid = 0
            if not pid:
                # sem id, não indexar
                continue
            if self.produto_existe(pid):
                continue
            try:
                self.indexar_produto(p)
                novos += 1
            except Exception as e:
                falhas += 1
                nome = p.get('nome', 'sem nome')
                print(f"❌ Erro ao indexar novo produto '{nome}' (id={pid}): {e}")
        if novos or removidos:
            print(f"🔄 Sincronização: {novos} novo(s) indexado(s), {removidos} removido(s).")
        return {"novos": novos, "removidos": removidos, "falhas": falhas}
        
    def get_models(self) -> Dict[str, Any]:
        """Retorna dicionário com cliente de embeddings"""
        return {
            "embedding_client": self.embedding_client,
            "supports_portuguese": True,
            "supports_multilingual": self.MULTI_OK,
        }
        
    def close(self):
        """Fecha conexão com Weaviate"""
        if self.client:
            self.client.close()
