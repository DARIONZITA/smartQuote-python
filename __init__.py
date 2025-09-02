# Exportações para tornar o busca_local um pacote Python válido
try:
    from .decomposer import SolutionDecomposer
    from .models import (
        DecompositionResult, ComponenteParaAquisicao,
        AlternativaViavel, ComponentPriority
    )
    from .weaviate_client import WeaviateManager
    from .supabase_client import SupabaseManager
    from .search_engine import buscar_hibrido_ponderado, _llm_escolher_indice
    from .query_builder import gerar_estrutura_de_queries
    from .cotacao_manager import CotacaoManager
    from .config import *
    from .app import app
except ImportError as e:
    # Em caso de erro, importar individualmente para debug
    print(f"⚠️ Aviso ao importar módulos em __init__.py: {e}")
    try:
        from .app import app
    except ImportError:
        pass

# Versão do pacote
__version__ = "1.0.0"
from .utils import validate_and_fix_result, create_fallback_decomposition, build_filters

__all__ = [
    'SolutionDecomposer',
    'DecompositionResult',
    'ComponenteParaAquisicao', 
    'AlternativaViavel',
    'ComponentPriority',
    'validate_and_fix_result',
    'create_fallback_decomposition',
    'build_filters'
]
