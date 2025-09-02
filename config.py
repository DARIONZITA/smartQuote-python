import os
from pathlib import Path

# Carregar variáveis de ambiente do arquivo .env LOCAL
def load_env():
    """Carrega variáveis de ambiente do arquivo .env LOCAL da API Python"""
    # Busca APENAS o .env local no diretório da API Python
    local_env = Path(__file__).parent / '.env'
    
    if local_env.exists():
        try:
            print(f"🔎 [CONFIG] Carregando .env local: {local_env}")
            with open(local_env, 'r', encoding='utf-8') as f:
                loaded_vars = 0
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove aspas se existirem
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        os.environ.setdefault(key, value)
                        loaded_vars += 1
                
                print(f"✅ [CONFIG] {loaded_vars} variáveis carregadas do .env local")
        except Exception as e:
            print(f"⚠️ [CONFIG] Erro ao carregar .env local: {e}")
    else:
        print(f"⚠️ [CONFIG] Arquivo .env não encontrado em: {local_env}")
        print(f"💡 [CONFIG] Crie o arquivo .env com base no .env.example")
        print(f"📝 [CONFIG] Usando variáveis de ambiente do sistema")

# Carregar .env antes de definir configurações
load_env()

# --- CONFIGURAÇÃO SUPABASE ---
# Preferir SERVICE_ROLE; cair para SUPABASE_KEY ou SUPABASE_ANON_KEY
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY")
)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:2000")
SUPABASE_TABLE = "produtos"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Variáveis do Supabase ausentes. Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY (ou ANON).")

# --- CONFIGURAÇÃO WEAVIATE ---
WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST")
WEAVIATE_PORT = 8080
WEAVIATE_GRPC_PORT = 50051
API_KEY_WEAVIATE = os.environ.get("API_KEY_WEAVIATE")

# --- CONFIGURAÇÃO DE BUSCA ---
LIMITE_PADRAO_RESULTADOS = 4
LIMITE_MAXIMO_RESULTADOS = 50

# --- MODELOS DE EMBEDDING ---
MODELO_PT = 'neuralmind/bert-base-portuguese-cased'
MODELO_MULTI = 'paraphrase-multilingual-mpnet-base-v2'

# --- CONFIGURAÇÃO GROQ ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- SINÔNIMOS E EQUIVALÊNCIAS ---
SYNONYMS = {
    "impressora": ["printer", "mfp", "multifuncional"],
    "multifuncional": ["mfp"],
    "sem fio": ["wireless", "wifi", "wi-fi"],
    "cartucho": ["toner", "tinta"],
    "duplex": ["frente e verso"],
}

CATEGORY_EQUIV = {
    "hardware de posto de trabalho": [
        "perifericos",
        "informática",
        "computadores",
        "hardware",
    ],
    "software de produtividade e colaboração": [
        "software",
        "produtividade",
    ],
    "servico": ["servico", "cloud", "suporte"],
}

STOPWORDS_PT = {'a', 'o', 'as', 'os', 'um', 'uma', 'de', 'do', 'da', 'e', 'ou', 'para', 'com', 'em', 'no', 'na'}