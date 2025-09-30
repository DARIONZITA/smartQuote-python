"""
API Flask Independente para Sistema de Busca Local - smartQuote    modelos = weaviate_manager.get_models()
    espacos = ["vetor_portugues"] + (["vetor_multilingue"] if modelos.get("supports_multilingual") and usar_multilingue else [])sta API roda de forma completamente independente da API principal Node.js
"""
import warnings
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Any, Dict, List, Tuple
import os
import sys
import json
from datetime import datetime, timedelta
import traceback
import logging
import hashlib

# Configurar o path para imports locais (sem dependência da API principal)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# IMPORTANTE: Carregar .env LOCAL antes de qualquer import que use variáveis
try:
    from config import load_env
    load_env()  # Carrega .env do diretório busca_local
    
    # Imports dos módulos locais (agora com variáveis carregadas)
    from config import LIMITE_PADRAO_RESULTADOS, LIMITE_MAXIMO_RESULTADOS, GROQ_API_KEY
    from weaviate_client import WeaviateManager
    from supabase_client import SupabaseManager
    from search_engine import buscar_hibrido_ponderado, _llm_escolher_indice
    from query_builder import gerar_estrutura_de_queries
    from cotacao_manager import CotacaoManager
    from decomposer import SolutionDecomposer
except ImportError:
    try:
        from .config import load_env
        load_env()  # Carrega .env do diretório busca_local
        
        # Imports dos módulos locais (agora com variáveis carregadas)
        from .config import LIMITE_PADRAO_RESULTADOS, LIMITE_MAXIMO_RESULTADOS, GROQ_API_KEY
        from .weaviate_client import WeaviateManager
        from .supabase_client import SupabaseManager
        from .search_engine import buscar_hibrido_ponderado, _llm_escolher_indice
        from .query_builder import gerar_estrutura_de_queries
        from .cotacao_manager import CotacaoManager
        from .decomposer import SolutionDecomposer
    except ImportError as e:
        print(f"⚠️ Erro crítico ao importar módulos: {e}")
        raise

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configurar logging independente
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api-python.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Managers globais (inicializados na startup)
weaviate_manager = None
supabase_manager = None
decomposer = None

# Logging de requisições: URL acessada, origem (Referer/Origin) e IP
def _client_ip() -> str:
    try:
        xff = request.headers.get('X-Forwarded-For')
        if xff:
            return xff.split(',')[0].strip()
        xri = request.headers.get('X-Real-IP')
        return xri or request.remote_addr or ""
    except Exception:
        return ""

@app.before_request
def _log_incoming_request():
    try:
        # Headers auxiliares para rastreio
        xff_chain = request.headers.get('X-Forwarded-For')
        x_request_id = request.headers.get('X-Request-Id') or request.headers.get('X-Request-ID')
        x_client_service = request.headers.get('X-Client-Service')
        auth_hdr = request.headers.get('Authorization')
        auth_fp = None
        if auth_hdr:
            try:
                # Hash do Authorization (sem vazar segredo)
                auth_fp = hashlib.sha256(auth_hdr.encode('utf-8')).hexdigest()[:10]
            except Exception:
                auth_fp = 'err'

        interp_id = None
        if request.method == 'POST' and request.path.endswith('/process-interpretation'):
            body = request.get_json(silent=True) or {}
            interp = body.get('interpretation') if isinstance(body, dict) else None
            if isinstance(interp, dict):
                interp_id = interp.get('id')

        # País/região via proxies comuns (Cloudflare, etc.)
        cf_country = request.headers.get('CF-IPCountry') or request.headers.get('Cf-Ipcountry')
        fly_region = request.headers.get('Fly-Region')
        x_region = request.headers.get('X-Region')

        # Identificação do cliente (label) via cabeçalho, fingerprint, ou IP conforme mapas em env
        client_label = None
        try:
            # Mapa por fingerprint de Authorization (env JSON: {"<fp>": "label"})
            authfp_map = json.loads(os.environ.get('REQUEST_AUTHFP_LABELS', '{}'))
        except Exception:
            authfp_map = {}
        try:
            # Mapa por IP (env JSON: {"1.2.3.4": "label"})
            ip_map = json.loads(os.environ.get('REQUEST_IP_LABELS', '{}'))
        except Exception:
            ip_map = {}

        ip_eff = _client_ip()
        if x_client_service:
            client_label = x_client_service
        elif auth_fp and authfp_map.get(auth_fp):
            client_label = authfp_map.get(auth_fp)
        elif ip_map.get(ip_eff):
            client_label = ip_map.get(ip_eff)
        else:
            ua_l = (request.headers.get('User-Agent') or '').lower()
            client_label = 'axios-client' if 'axios' in ua_l else 'desconhecido'

        logger.info(
            "↘️ %s %s | host=%s | ip=%s | xff=%s | referer=%s | origin=%s | ua=%s | x-request-id=%s | x-client=%s | auth#=%s | interp_id=%s | client=%s | country=%s | region=%s",
            request.method,
            request.url,
            request.host,
            ip_eff,
            xff_chain,
            request.headers.get('Referer'),
            request.headers.get('Origin'),
            request.headers.get('User-Agent'),
            x_request_id,
            x_client_service,
            auth_fp,
            interp_id,
            client_label,
            cf_country,
            fly_region or x_region,
        )
    except Exception as e:
        logger.warning(f"⚠️ Falha ao logar request: {e}")

@app.after_request
def _log_outgoing_response(response):
    try:
        logger.info("↗️ %s %s %s", response.status_code, request.method, request.path)
    except Exception:
        pass
    return response

def executar_estrutura_de_queries(
    weaviate_manager: WeaviateManager, 
    estrutura: List[Dict[str, Any]], 
    limite: int = None, 
    usar_multilingue: bool = True,
    verbose: bool = False
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
    """
    Executa todas as queries geradas pela estrutura e apresenta resultados.
    Retorna um dicionário {query_id: [resultados]} e uma lista de IDs de queries faltantes.
    """
    if limite is None:
        limite = LIMITE_PADRAO_RESULTADOS
        
    modelos = weaviate_manager.get_models()
    espacos = ["vetor_portugues"] + (["vetor_multilingue"] if modelos.get("supports_multilingual") and usar_multilingue else [])
    
    if verbose:
        logger.info(f"🔍 Espaços de busca: {espacos}")

    resultados_por_query: Dict[str, List[Dict[str, Any]]] = {}

    for q in estrutura:
        if verbose:
            logger.info(f"➡️ Executando {q['id']} [{q['tipo']}] | Query: {q['query']}")
            logger.info(f"Filtros: {q.get('filtros')}")
        
        todos: List[Dict[str, Any]] = []
        # Buscar em todos os espaços e juntar resultados
        for espaco in espacos:
            filtros_query = q.get("filtros") or {}
            
            r = buscar_hibrido_ponderado(
                weaviate_manager.client,
                modelos,
                q["query"],
                espaco,
                limite=limite,
                filtros=filtros_query,
            )
            todos.extend(r)
        
        # Agregar por produto mantendo melhor score
        agregados: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for item in todos:
            categoria = item.get("categoria", "") or item.get("modelo", "")
            chave = (item["nome"], categoria)
            atual = agregados.get(chave)
            if not atual or item["score"] > atual["score"]:
                agregados[chave] = item
                
        lista = list(agregados.values())
        lista.sort(key=lambda x: x["score"], reverse=True)

        resultado_llm = {"index": -1, "relatorio": {}}
        try:
            resultado_llm = _llm_escolher_indice(q["query"], q.get("filtros") or None, q.get("custo_beneficio") or None, q.get("rigor") or None, lista)
            logger.info(f"🧠 [LLM] Resultado para {q['id']}: índice={resultado_llm.get('index')}, relatório={len(resultado_llm.get('relatorio', {}))} campos")
        except Exception as e:
            logger.error(f"[LLM] Erro ao executar refinamento: {e}")
            resultado_llm = {"index": -1, "relatorio": {}}
        
        idx_escolhido = resultado_llm.get("index", -1)
        relatorio_llm = resultado_llm.get("relatorio", {})
        
        if isinstance(idx_escolhido, int) and 0 <= idx_escolhido < len(lista):
            escolhido = lista[idx_escolhido]
            escolhido["llm_match"] = True
            escolhido["llm_index"] = idx_escolhido
            escolhido["llm_relatorio"] = relatorio_llm
            logger.info(f"🎯 Índice escolhido pela LLM: {idx_escolhido} - {escolhido.get('nome', 'N/A')}")
            lista = [escolhido]
        else:
            if idx_escolhido == -1:
                logger.info(f"❌ LLM não encontrou match adequado para {q['id']}")
            else:
                logger.warning(f"⚠️ Índice LLM inválido: {idx_escolhido} (max: {len(lista)-1})")
            
            # PRESERVAR o relatório LLM mesmo quando nenhum produto é escolhido
            # Criar um objeto especial para representar a análise rejeitada
            if relatorio_llm and lista:  # Se houve análise LLM e havia produtos candidatos
                produto_rejeitado = {
                    "llm_match": False,
                    "llm_rejected": True,
                    "llm_relatorio": relatorio_llm,
                    "query_id": q["id"],
                    "status": "rejeitado_por_llm",
                    "observacao": "Produtos encontrados mas rejeitados pela análise LLM"
                }
                # Manter o produto rejeitado para que o relatório seja preservado
                lista = [produto_rejeitado]
            else:
                lista = []

        resultados_por_query[q["id"]] = lista

        # Log resumido por query
        if verbose:
            logger.info(f"📌 Top {min(limite, len(lista))} para {q['id']}:")
            for i, r in enumerate(lista[:limite], start=1):
                logger.info(f"  {i}. {r.get('nome', 'N/A')} - Score: {r.get('score', 0):.3f}")

    # Pós-processamento: queries sem resultado
    ids_por_tipo: Dict[str, str] = {q["id"]: q.get("tipo", "") for q in estrutura}
    item_ids: List[str] = [q["id"] for q in estrutura if q.get("tipo") == "item"]

    # Verificar se Q0 e Q1 têm resultados
    has_q0 = bool(resultados_por_query.get("Q0"))
    has_q1 = bool(resultados_por_query.get("Q1"))

    # Considerar somente itens (Q1..QN) para determinar faltantes
    missing_items: List[str] = []
    for qid in item_ids:
        resultados_query = resultados_por_query.get(qid, [])
        # Considerar faltante se: vazio OU se contém apenas produtos rejeitados pela LLM
        if not resultados_query:
            missing_items.append(qid)
        elif len(resultados_query) == 1 and resultados_query[0].get("llm_rejected"):
            # Query rejeitada pela LLM - será tratada como faltante no loop principal
            # Não adicionar à lista missing_items para evitar duplicação
            pass
        # Queries com produtos válidos não são consideradas faltantes
    faltando: List[str] = missing_items

    if verbose:
        if faltando:
            logger.info("⚠️ Queries sem resultados ou pendentes:")
            for qid in faltando:
                logger.info(f"  - {qid}")
        else:
            if (has_q0 or has_q1) and not missing_items:
                logger.info("✅ Todas as queries principais encontraram resultados!")

    return resultados_por_query, faltando

def _resumo_resultados(resultados: Dict[str, List[Dict[str, Any]]], limite: int) -> Dict[str, List[Dict[str, Any]]]:
    """Extrai um resumo compacto dos resultados (Top N por query)."""
    resumo: Dict[str, List[Dict[str, Any]]] = {}
    for qid, lista in resultados.items():
        compact = []
        for r in (lista or [])[:limite]:
            compact.append({
                "nome": r.get("nome"),
                "categoria": r.get("categoria") or r.get("modelo"),
                "preco": r.get("preco"),
                "score": r.get("score"),
                "produto_id": r.get("produto_id"),
                "fonte": r.get("fonte"),
            })
        resumo[qid] = compact
    return resumo

def executar_busca_duas_fases(
    weaviate_manager: WeaviateManager,
    estrutura: List[Dict[str, Any]],
    limite_resultados: int = LIMITE_PADRAO_RESULTADOS,
    usar_multilingue: bool = True,
    verbose: bool = False
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str], Dict[str, Any]]:
    """
    Executa busca em duas fases:
    1. Primeira fase: produtos com origem='local'
    2. Segunda fase (cache): produtos com origem='externo' para queries sem resultado na primeira fase
    
    Returns:
        Tuple[resultados_finais, faltantes_finais, metricas_fases]
    """
    metricas = {
        "fase_local": {"queries_executadas": 0, "produtos_encontrados": 0, "queries_com_resultado": 0},
        "fase_cache": {"queries_executadas": 0, "produtos_encontrados": 0, "queries_com_resultado": 0},
        "queries_ids_por_fase": {"local": [], "cache": []},
        # Novo: guardar as análises LLM por fase para cada query
        "analises_por_fase": {"local": {}, "cache": {}}
    }
    
    if verbose:
        logger.info("🚀 Iniciando busca em duas fases: LOCAL → CACHE")
    
    # FASE 1: Busca com produtos locais apenas
    if verbose:
        logger.info("📍 FASE 1: Buscando produtos com origem='local'")
    
    # Criar estrutura com filtros de origem local
    estrutura_local = []
    for q in estrutura:
        q_local = q.copy()
        filtros_local = (q_local.get("filtros") or {}).copy()
        filtros_local["origem"] = "local"
        q_local["filtros"] = filtros_local
        estrutura_local.append(q_local)
    
    resultados_local, faltantes_local = executar_estrutura_de_queries(
        weaviate_manager,
        estrutura_local,
        limite=limite_resultados,
        usar_multilingue=usar_multilingue,
        verbose=verbose
    )
    
    # Atualizar métricas da fase local e marcar origem
    metricas["fase_local"]["queries_executadas"] = len(estrutura)
    for qid, lista in resultados_local.items():
        metricas["queries_ids_por_fase"]["local"].append(qid)
        if lista and not (len(lista) == 1 and lista[0].get("llm_rejected")):
            metricas["fase_local"]["queries_com_resultado"] += 1
            metricas["fase_local"]["produtos_encontrados"] += len(lista)
            # Marcar produtos da fase local
            for produto in lista:
                produto["fase_origem"] = "local"
        # Capturar análise LLM da fase local (SEMPRE preservar relatórios)
        if lista:
            topo = lista[0]
            rel = topo.get("llm_relatorio") or {}
            match_ok = not topo.get("llm_rejected") and topo.get("produto_id") is not None
            score_local = topo.get("score") if match_ok else 0
            metricas["analises_por_fase"]["local"][qid] = {
                "relatorio": rel,
                "score": score_local,
                "match": bool(match_ok),
                "status": "rejeitado_por_llm" if topo.get("llm_rejected") else "aceito",
                "observacao": topo.get("observacao") if topo.get("llm_rejected") else None
            }
        else:
            # Mesmo sem resultados, preservar estrutura para capturar relatórios futuros
            metricas["analises_por_fase"]["local"][qid] = {
                "relatorio": {},
                "score": 0,
                "match": False,
                "status": "sem_produtos_encontrados",
                "observacao": "Nenhum produto encontrado na fase local"
            }
    
    # Identificar queries que precisam de busca cache
    queries_para_cache = []
    queries_ids_cache = []
    
    for q in estrutura:
        qid = q["id"]
        lista_q = resultados_local.get(qid, [])
        
        # Precisa de cache se: vazio OU se contém apenas produtos rejeitados pela LLM
        precisa_cache = (
            not lista_q or 
            (len(lista_q) == 1 and lista_q[0].get("llm_rejected"))
        )
        
        if precisa_cache:
            queries_para_cache.append(q)
            queries_ids_cache.append(qid)
    
    resultados_finais = resultados_local.copy()
    faltantes_finais = faltantes_local.copy()
    
    # FASE 2: Busca cache (produtos externos) apenas para queries sem resultado
    if queries_para_cache:
        if verbose:
            logger.info(f"🔄 FASE 2 (CACHE): Buscando produtos com origem='externo' para {len(queries_para_cache)} queries")
            logger.info(f"Queries para cache: {queries_ids_cache}")
        
        # Criar estrutura com filtros de origem externa
        estrutura_cache = []
        for q in queries_para_cache:
            q_cache = q.copy()
            filtros_cache = (q_cache.get("filtros") or {}).copy()
            filtros_cache["origem"] = "externo"
            q_cache["filtros"] = filtros_cache
            estrutura_cache.append(q_cache)
        
        resultados_cache, faltantes_cache = executar_estrutura_de_queries(
            weaviate_manager,
            estrutura_cache,
            limite=limite_resultados,
            usar_multilingue=usar_multilingue,
            verbose=verbose
        )
        
        # Atualizar métricas da fase cache
        metricas["fase_cache"]["queries_executadas"] = len(queries_para_cache)
        for qid, lista in resultados_cache.items():
            metricas["queries_ids_por_fase"]["cache"].append(qid)
            if lista and not (len(lista) == 1 and lista[0].get("llm_rejected")):
                metricas["fase_cache"]["queries_com_resultado"] += 1
                metricas["fase_cache"]["produtos_encontrados"] += len(lista)
            # Capturar análise LLM da fase cache (SEMPRE preservar relatórios)
            if lista:
                topo = lista[0]
                rel = topo.get("llm_relatorio") or {}
                match_ok = not topo.get("llm_rejected") and topo.get("produto_id") is not None
                score_cache = topo.get("score") if match_ok else 0
                metricas["analises_por_fase"]["cache"][qid] = {
                    "relatorio": rel,
                    "score": score_cache,
                    "match": bool(match_ok),
                    "status": "rejeitado_por_llm" if topo.get("llm_rejected") else "aceito",
                    "observacao": topo.get("observacao") if topo.get("llm_rejected") else None
                }
            else:
                # Mesmo sem resultados na cache, preservar estrutura
                metricas["analises_por_fase"]["cache"][qid] = {
                    "relatorio": {},
                    "score": 0,
                    "match": False,
                    "status": "sem_produtos_encontrados", 
                    "observacao": "Nenhum produto encontrado na fase cache"
                }
        
        # Mesclar resultados: substituir resultados vazios/rejeitados pelos da cache
        for qid in queries_ids_cache:
            if qid in resultados_cache:
                lista_cache = resultados_cache[qid]
                if lista_cache and not (len(lista_cache) == 1 and lista_cache[0].get("llm_rejected")):
                    # Cache encontrou resultado válido - marcar como originário da cache
                    for produto in lista_cache:
                        produto["fase_origem"] = "cache"  # Marcar produtos da fase cache
                    resultados_finais[qid] = lista_cache
                    # Remover da lista de faltantes se estava lá
                    if qid in faltantes_finais:
                        faltantes_finais.remove(qid)
                    if verbose:
                        logger.info(f"✅ Cache resolveu query {qid}")
        
        # Atualizar faltantes finais
        faltantes_finais = [qid for qid in faltantes_cache if qid in queries_ids_cache]
    else:
        if verbose:
            logger.info("✅ FASE 2 (CACHE): Não necessária - todas as queries foram resolvidas na fase local")
    
    if verbose:
        total_local = metricas["fase_local"]["queries_com_resultado"]
        total_cache = metricas["fase_cache"]["queries_com_resultado"] 
        total_faltantes = len(faltantes_finais)
        logger.info(f"📊 RESUMO: {total_local} local + {total_cache} cache + {total_faltantes} faltantes = {len(estrutura)} queries")
    
    return resultados_finais, faltantes_finais, metricas

def processar_interpretacao(
    interpretation: Dict[str, Any],
    limite_resultados: int = LIMITE_PADRAO_RESULTADOS,
    usar_multilingue: bool = True,
    criar_cotacao: bool = False,
) -> Dict[str, Any]:
    """
    Processa uma interpretação: usa o campo 'solicitacao' para rodar LLM->brief->queries->busca.
    Retorna um dicionário com status, resumo dos resultados e metadados.
    """
    global weaviate_manager, supabase_manager, decomposer
    
    # Campos básicos
    solicitacao = (interpretation or {}).get("solicitacao")
    if not solicitacao:
        raise ValueError("Campo 'solicitacao' ausente na interpretação fornecida")

    # Sincronizar dados antes da busca
    try:
        if supabase_manager and supabase_manager.is_available():
            # Atualizar dados completos do Supabase (incluindo produtos removidos)
            produtos_atualizados = supabase_manager.refresh()
            if produtos_atualizados:
                logger.info(f"🔄 Sincronizando {len(produtos_atualizados)} produtos do Supabase (incluindo remoções)")
                # Usar sincronização completa que remove órfãos e indexa novos
                metricas = weaviate_manager.sincronizar_com_supabase(produtos_atualizados)
                if metricas.get("novos", 0) > 0 or metricas.get("removidos", 0) > 0:
                    logger.info(f"📊 Sincronização: +{metricas.get('novos', 0)} novos, -{metricas.get('removidos', 0)} removidos")
            else:
                logger.info("📊 Nenhum produto encontrado no Supabase")
        else:
            logger.info("📊 Supabase não disponível; mantendo dados atuais do Weaviate")
    except Exception as e:
        logger.warning(f"⚠️ Falha ao sincronizar com Supabase antes da busca: {e}")

    logger.info("🤖 Decompondo solicitação...")
    brief = decomposer.gerar_brief(solicitacao)

    estrutura = gerar_estrutura_de_queries(brief)
    logger.info(f"🧩 {len(estrutura)} queries geradas a partir do brief")

    # Executar busca em duas fases: LOCAL → CACHE
    resultados, faltantes, metricas_fases = executar_busca_duas_fases(
        weaviate_manager,
        estrutura,
        limite_resultados=limite_resultados,
        usar_multilingue=usar_multilingue,
        verbose=True
    )

    # Mapear metadados das queries para facilitar detalhes dos faltantes
    meta_por_id = {q["id"]: q for q in estrutura}
    faltantes_meta: Dict[str, Any] = {}
    for qid in faltantes:
        qm = meta_por_id.get(qid)
        if not qm:
            continue
        filtros = qm.get("filtros") or {}
        fonte = qm.get("fonte") or {}
        # Nome amigável: item.nome, alternativa.nome ou solucao_principal
        nome_amigavel = fonte.get("nome") or fonte.get("solucao_principal") or None
        faltantes_meta[qid] = {
            "id": qm.get("id"),
            "tipo": qm.get("tipo"),
            "nome": nome_amigavel,
            "query": qm.get("query"),
            "custo_beneficio": filtros.get("custo_beneficio"),
            "categoria": filtros.get("categoria"),
            "palavras_chave": filtros.get("palavras_chave"),
            "quantidade": qm.get("quantidade"),
            "fonte": fonte,
        }

    # Gerar tarefas para pesquisa web com base nos faltantes (retorno informativo)
    tarefas_web: List[Dict[str, Any]] = []
    for qid, meta in faltantes_meta.items():
        nome = (meta.get("nome") or "").strip()
        categoria = (meta.get("categoria") or "").strip()
        palavras = meta.get("palavras_chave") or []
        custo_beneficio = meta.get("custo_beneficio") or {}
        if isinstance(palavras, list):
            palavras_str = " ".join([str(p).strip() for p in palavras if str(p).strip()])
        else:
            palavras_str = str(palavras).strip()
        base = " ".join([s for s in [nome, categoria, palavras_str] if s])
        # fallback para query original se base ficar vazia
        query_sugerida = base if base else (meta.get("query") or nome or categoria)
        query_sugerida = (query_sugerida or "").strip()
        tarefas_web.append({
            "id": qid,
            "tipo": meta.get("tipo"),
            "nome": nome or None,
            "categoria": categoria or None,
            "custo_beneficio": custo_beneficio,
            "palavras_chave": palavras or None,
            "quantidade": meta.get("quantidade") or 1,
            "query_sugerida": query_sugerida or None,
        })

    saida: Dict[str, Any] = {
        "status": "success",
        "processed_at": datetime.now().isoformat(),
        "email_id": interpretation.get("emailId"),
        "interpretation_id": interpretation.get("id"),
        "tipo": interpretation.get("tipo"),
        "prioridade": interpretation.get("prioridade"),
        "confianca": interpretation.get("confianca"),
        "dados_extraidos": brief,
        "cliente": interpretation.get("cliente"),
        "dados_bruto": interpretation.get("dados_bruto"),
        "faltantes": tarefas_web,
        "resultado_resumo": _resumo_resultados(resultados, limite_resultados),
        "metricas_busca": metricas_fases,
    }

    # Criação opcional de cotações
    if criar_cotacao:
        logger.info("⚙️ Criando cotações (modo automático)...")
        cotacao_manager = CotacaoManager(supabase_manager)

        prompt_id = cotacao_manager.insert_prompt(
            texto_original=solicitacao,
            dados_extraidos=brief,
            cliente=interpretation.get("cliente"),
            dados_bruto=interpretation.get("dados_bruto"),
            origem={"tipo": "api", "interpretation_id": interpretation.get("id")},
            status="analizado",
        )
        if not prompt_id:
            logger.error("❌ Não foi possível criar o prompt; pulando cotações.")
            saida["cotacoes"] = {"status": "erro", "motivo": "prompt_invalido"}
            return saida

        tem_q0 = bool(resultados.get("Q0"))

        if tem_q0:
            ids_primeira = ["Q0"] + [
                qid for qid, meta in meta_por_id.items()
                if meta.get("tipo") == "item" and qid != "Q1"
            ]
        else:
            ids_primeira = [
                qid for qid, meta in meta_por_id.items()
                if meta.get("tipo") == "item"
            ]

        cotacao1_id = cotacao_manager.insert_cotacao(
            prompt_id=prompt_id,
            observacoes="Cotação principal (automática).",
            prazo_validade=(datetime.now() + timedelta(days=15)).isoformat()
        )

        itens_adicionados = 0
        produtos_principais = set()
        
        if cotacao1_id:
            for qid in ids_primeira:
                lista_q = resultados.get(qid, [])
                
                # Se há produtos (aceitos ou rejeitados pela LLM)
                if lista_q:
                    produto = lista_q[0]  # Sempre há apenas 1 produto por query após LLM
                    
                    # Verificar se é um produto rejeitado pela LLM
                    if produto.get("llm_rejected"):
                        # Produto rejeitado - preservar análises das fases adequadas
                        fase_origem = produto.get("fase_origem", "local")
                        dados_cache = metricas_fases.get("analises_por_fase", {}).get("cache", {}).get(qid, {})
                        dados_local_ref = metricas_fases.get("analises_por_fase", {}).get("local", {}).get(qid, {})
                        
                        # Sempre incluir análise local quando produtos são rejeitados
                        analise_local = {
                            "query_id": qid,
                            "score": dados_local_ref.get("score", 0),
                            "alternativa": False,
                            "status": dados_local_ref.get("status", "rejeitado_por_llm"),
                            "observacao": dados_local_ref.get("observacao", "Produtos encontrados mas rejeitados pela análise LLM"),
                            "fase_origem": "local"
                        }
                        if dados_local_ref.get("relatorio"):
                            analise_local["llm_relatorio"] = dados_local_ref.get("relatorio")
                        
                        # Sempre incluir análise cache se a fase cache foi executada
                        analise_cache = None
                        if dados_cache:
                            # Produto rejeitado na cache - incluir análise da cache
                            analise_cache = {
                                "query_id": qid,
                                "score": dados_cache.get("score", 0),
                                "alternativa": False,
                                "status": "rejeitado_por_llm",
                                "observacao": dados_cache.get("observacao", "Produtos encontrados mas rejeitados pela análise LLM na cache"),
                                "fase_origem": "cache"
                            }
                            if dados_cache.get("relatorio"):
                                analise_cache["llm_relatorio"] = dados_cache.get("relatorio")
                        else:
                            # Verificar se a fase cache foi executada mesmo sem dados
                            fases_executadas = metricas_fases.get("fases_executadas", [])
                            if "cache" in fases_executadas:
                                analise_cache = {
                                    "query_id": qid,
                                    "score": 0,
                                    "alternativa": False,
                                    "status": "fase_executada_sem_resultado",
                                    "observacao": "Fase cache executada mas sem produtos encontrados ou dados de análise",
                                    "fase_origem": "cache"
                                }
                        
                        # Criar item faltante para produto rejeitado pela LLM
                        try:
                            query_geradora = meta_por_id.get(qid, {}).get("query")
                            nome_item = meta_por_id.get(qid, {}).get("fonte", {}).get("nome") or "Item rejeitado pela LLM"
                            quantidade = meta_por_id.get(qid, {}).get("quantidade", 1)
                            
                            item_id = cotacao_manager.insert_missing_item(
                                cotacao_id=cotacao1_id,
                                nome=nome_item,
                                descricao="Produto não encontrado",
                                tags=["rejeitado_llm", "faltante"],
                                quantidade=quantidade,
                                pedido=query_geradora,
                                origem="externo",
                                analise_local=analise_local,
                                analise_cache=analise_cache
                            )
                            if item_id:
                                logger.info(f"📝 Item faltante criado para produto rejeitado pela LLM: {nome_item}")
                        except Exception as e:
                            logger.warning(f"⚠️ Falha ao criar item faltante para produto rejeitado pela LLM: {e}")
                    
                    else:
                        # Produto aceito - processar normalmente
                        produto_id = produto.get("produto_id")
                        if produto_id and produto_id not in produtos_principais:
                            # Verificar se o produto vem da fase cache ou local
                            fase_origem = produto.get("fase_origem", "local")
                            
                            if fase_origem == "cache":
                                # Produto da fase cache - criar ambas análises com dados específicos por fase
                                dados_cache = metricas_fases.get("analises_por_fase", {}).get("cache", {}).get(qid, {})
                                dados_local_ref = metricas_fases.get("analises_por_fase", {}).get("local", {}).get(qid, {})
                                analise_local = {
                                    "query_id": qid,
                                    "score": dados_local_ref.get("score", 0),
                                    "alternativa": False,
                                    "fase_origem": "cache",
                                }
                                if dados_local_ref.get("relatorio"):
                                    analise_local["llm_relatorio"] = dados_local_ref.get("relatorio")
                                analise_cache = {
                                    "query_id": qid,
                                    "score": dados_cache.get("score", produto.get("score")),
                                    "alternativa": False,
                                }
                                if dados_cache.get("relatorio"):
                                    analise_cache["llm_relatorio"] = dados_cache.get("relatorio")
                            else:
                                # Produto da fase local - usar analise_local com dados da fase local
                                dados_local = metricas_fases.get("analises_por_fase", {}).get("local", {}).get(qid, {})
                                analise_local = {
                                    "query_id": qid,
                                    "score": dados_local.get("score", produto.get("score")),
                                    "alternativa": False,
                                    "fase_origem": "local",
                                }
                                if dados_local.get("relatorio"):
                                    analise_local["llm_relatorio"] = dados_local.get("relatorio")
                                analise_cache = None
                            
                                  # Inserir item na cotação
                            # Passar a query que gerou o item no campo 'pedido'
                            query_geradora = meta_por_id.get(qid, {}).get("query")
                            item_id = cotacao_manager.insert_cotacao_item_from_result(
                                cotacao_id=cotacao1_id,
                                resultado_produto=produto,
                                origem=produto.get("origem", "local"),
                                produto_id=produto_id,
                                analise_local=analise_local,
                                analise_cache=analise_cache,
                                quantidade=meta_por_id.get(qid, {}).get("quantidade", 1),
                                pedido=query_geradora,
                            )
                            if item_id:
                                itens_adicionados += 1
                                produtos_principais.add(produto_id)
                else:
                    # Nenhum produto encontrado em ambas as fases - preservar relatórios LLM de ambas
                    dados_local = metricas_fases.get("analises_por_fase", {}).get("local", {}).get(qid, {})
                    dados_cache = metricas_fases.get("analises_por_fase", {}).get("cache", {}).get(qid, {})
                    
                    analise_local = {
                        "query_id": qid,
                        "score": dados_local.get("score", 0),
                        "alternativa": False,
                        "status": dados_local.get("status", "sem_produtos_encontrados"),
                        "observacao": dados_local.get("observacao", "Nenhum produto encontrado na base de dados"),
                        "fase_origem": "local"
                    }
                    if dados_local.get("relatorio"):
                        analise_local["llm_relatorio"] = dados_local.get("relatorio")
                    
                    # Sempre criar analise_cache se houve tentativa de busca cache
                    analise_cache = None
                    if dados_cache:  # Se houve tentativa de busca cache
                        analise_cache = {
                            "query_id": qid,
                            "score": dados_cache.get("score", 0),
                            "alternativa": False,
                            "status": dados_cache.get("status", "sem_produtos_encontrados"),
                            "observacao": dados_cache.get("observacao", "Nenhum produto encontrado na cache externa"),
                            "fase_origem": "cache"
                        }
                        if dados_cache.get("relatorio"):
                            analise_cache["llm_relatorio"] = dados_cache.get("relatorio")
                    else:
                        # Mesmo sem dados cache, verificar se houve busca na fase cache
                        fases_executadas = metricas_fases.get("fases_executadas", [])
                        if "cache" in fases_executadas:
                            analise_cache = {
                                "query_id": qid,
                                "score": 0,
                                "alternativa": False,
                                "status": "fase_executada_sem_resultado",
                                "observacao": "Fase cache executada mas sem dados de análise",
                                "fase_origem": "cache"
                            }
                    
                    # Criar item faltante preservando TODOS os relatórios LLM
                    try:
                        query_geradora = meta_por_id.get(qid, {}).get("query")
                        nome_item = meta_por_id.get(qid, {}).get("fonte", {}).get("nome") or "Item não encontrado"
                        quantidade = meta_por_id.get(qid, {}).get("quantidade", 1)
                        
                        item_id = cotacao_manager.insert_missing_item(
                            cotacao_id=cotacao1_id,
                            nome=nome_item,
                            descricao="Produto não encontrado em nenhuma fase",
                            tags=["faltante", "ambas_fases_falharam"],
                            quantidade=quantidade,
                            pedido=query_geradora,
                            origem="externo",
                            analise_local=analise_local,
                            analise_cache=analise_cache  # Preservar análise cache também
                        )
                        if item_id:
                            logger.info(f"📝 Item faltante criado preservando relatórios de ambas as fases: {nome_item}")
                    except Exception as e:
                        logger.warning(f"⚠️ Falha ao criar item faltante com relatórios preservados: {e}")
                    
            # Atualizar status da cotação conforme itens (incompleta se houver algum status=False)
            try:
                cotacao_manager.update_status_from_items(cotacao1_id)
            except Exception as e:
                logger.warning(f"⚠️ Falha ao atualizar status da cotação {cotacao1_id}: {e}")

        saida["cotacoes"] = {
            "principal_id": cotacao1_id,
            "itens_adicionados": itens_adicionados,
            "faltantes_inseridos": locals().get("faltantes_inseridos", 0)
        }

    return saida

@app.route('/health', methods=["GET", "HEAD"])
def health_check():
    """Endpoint de health check"""
    try:
        # Verificar se os managers estão funcionais
        weaviate_status = weaviate_manager is not None and weaviate_manager.client is not None
        supabase_status = supabase_manager is not None and supabase_manager.is_available()
        decomposer_status = decomposer is not None
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "weaviate": weaviate_status,
                "supabase": supabase_status,
                "decomposer": decomposer_status
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/', methods=["GET", "HEAD"])
def root_health_check():
    """Endpoint de health check"""
    try:
        # Verificar se os managers estão funcionais
        weaviate_status = weaviate_manager is not None and weaviate_manager.client is not None
        supabase_status = supabase_manager is not None and supabase_manager.is_available()
        decomposer_status = decomposer is not None
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "weaviate": weaviate_status,
                "supabase": supabase_status,
                "decomposer": decomposer_status
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/process-interpretation', methods=['POST'])
def process_interpretation():
    """Processa uma interpretação de email e retorna resultados da busca"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON analise_local required"}), 400
        
        # Extrair parâmetros
        interpretation = data.get('interpretation')
        limite = data.get('limite', LIMITE_PADRAO_RESULTADOS)
        usar_multilingue = data.get('usar_multilingue', True)
        criar_cotacao = data.get('criar_cotacao', False)
        
        # Validar limite
        if limite < 1 or limite > LIMITE_MAXIMO_RESULTADOS:
            limite = LIMITE_PADRAO_RESULTADOS
        
        # Processar interpretação
        resultado = processar_interpretacao(
            interpretation=interpretation,
            limite_resultados=limite,
            usar_multilingue=usar_multilingue,
            criar_cotacao=criar_cotacao
        )
        
        return jsonify(resultado), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Processing error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Internal processing error",
            "details": str(e),
            "status": "error"
        }), 500

@app.route('/hybrid-search', methods=['POST'])
def hybrid_search():
    """Executa busca híbrida ponderada diretamente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON analise_local required"}), 400
        
        pesquisa = data.get('pesquisa')
        if not pesquisa:
            return jsonify({"error": "Campo 'pesquisa' é obrigatório"}), 400
        
        filtros = data.get('filtros')
        limite = data.get('limite', LIMITE_PADRAO_RESULTADOS)
        usar_multilingue = data.get('usar_multilingue', True)
        
        # Validar limite
        if limite < 1 or limite > LIMITE_MAXIMO_RESULTADOS:
            limite = LIMITE_PADRAO_RESULTADOS
        
        # Sincronizar dados antes da busca
        try:
            if supabase_manager and supabase_manager.is_available():
                produtos_atualizados = supabase_manager.refresh()
                if produtos_atualizados:
                    metricas = weaviate_manager.sincronizar_com_supabase(produtos_atualizados)
                    if metricas.get("novos", 0) > 0 or metricas.get("removidos", 0) > 0:
                        logger.info(f"📊 Sincronização híbrida: +{metricas.get('novos', 0)} novos, -{metricas.get('removidos', 0)} removidos")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao sincronizar antes da busca híbrida: {e}")
        
        modelos = weaviate_manager.get_models()
        espacos = ["vetor_portugues"] + (["vetor_multilingue"] if modelos.get("supports_multilingual") and usar_multilingue else [])
        
        todos_resultados = []
        
        # Buscar em todos os espaços
        for espaco in espacos:
            resultados = buscar_hibrido_ponderado(
                weaviate_manager.client,
                modelos,
                pesquisa,
                espaco,
                limite=limite,
                filtros=filtros
            )
            todos_resultados.extend(resultados)
        
        # Agregar por produto mantendo melhor score
        agregados = {}
        for item in todos_resultados:
            categoria = item.get("categoria", "") or item.get("modelo", "")
            chave = (item["nome"], categoria)
            atual = agregados.get(chave)
            if not atual or item["score"] > atual["score"]:
                agregados[chave] = item
        
        lista_final = list(agregados.values())
        lista_final.sort(key=lambda x: x["score"], reverse=True)
        
        # Limitar resultados
        lista_final = lista_final[:limite]
        
        return jsonify({
            "status": "success",
            "resultados": lista_final,
            "total_encontrados": len(lista_final),
            "espacos_pesquisados": espacos,
            "query": pesquisa,
            "filtros": filtros,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Hybrid search error",
            "details": str(e),
            "status": "error"
        }), 500

@app.route('/sync-products', methods=['POST'])
def sync_products():
    """Sincroniza produtos do Supabase para o Weaviate (incluindo remoções)"""
    try:
        if not supabase_manager or not supabase_manager.is_available():
            return jsonify({"error": "Supabase não disponível"}), 503
        
        # Buscar todos os produtos atuais do Supabase
        produtos_atualizados = supabase_manager.refresh()
        
        if produtos_atualizados is not None:
            # Sincronização completa (adiciona novos e remove órfãos)
            metricas = weaviate_manager.sincronizar_com_supabase(produtos_atualizados)
            logger.info(f"🔄 Sincronização completa: {len(produtos_atualizados)} produtos no Supabase")
            
            return jsonify({
                "status": "success",
                "produtos_total_supabase": len(produtos_atualizados),
                "produtos_novos_indexados": metricas.get("novos", 0),
                "produtos_removidos": metricas.get("removidos", 0),
                "falhas": metricas.get("falhas", 0),
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "success",
                "produtos_total_supabase": 0,
                "produtos_novos_indexados": 0,
                "produtos_removidos": 0,
                "message": "Nenhum produto encontrado no Supabase",
                "timestamp": datetime.now().isoformat()
            }), 200
            
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({
            "error": "Sync error",
            "details": str(e),
            "status": "error"
        }), 500

@app.route('/sync-status', methods=['GET'])
def sync_status():
    """Verifica o status da sincronização entre Supabase e Weaviate"""
    try:
        status = {
            "timestamp": datetime.now().isoformat(),
            "supabase_available": False,
            "weaviate_available": False,
            "produtos_supabase": 0,
            "produtos_weaviate": 0,
            "sincronizado": False
        }
        
        # Verificar Supabase
        if supabase_manager and supabase_manager.is_available():
            status["supabase_available"] = True
            try:
                produtos = supabase_manager.get_produtos()
                status["produtos_supabase"] = len(produtos) if produtos else 0
            except Exception as e:
                logger.warning(f"Erro ao contar produtos Supabase: {e}")
        
        # Verificar Weaviate
        if weaviate_manager and weaviate_manager.client:
            status["weaviate_available"] = True
            try:
                collection = weaviate_manager.client.collections.get("Produtos")
                res = collection.aggregate.over_all(total_count=True)
                status["produtos_weaviate"] = res.total_count if res else 0
            except Exception as e:
                logger.warning(f"Erro ao contar produtos Weaviate: {e}")
        
        # Verificar sincronização
        status["sincronizado"] = (
            status["supabase_available"] and 
            status["weaviate_available"] and 
            status["produtos_supabase"] == status["produtos_weaviate"]
        )
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Sync status error: {e}")
        return jsonify({
            "error": "Sync status error",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def initialize_services():
    """Inicializa os serviços necessários"""
    global weaviate_manager, supabase_manager, decomposer
    
    try:
        logger.info("🚀 Inicializando serviços...")
        
        # Inicializar Weaviate
        weaviate_manager = WeaviateManager()
        weaviate_manager.connect()
        weaviate_manager.definir_schema()
        logger.info("✅ Weaviate conectado")
        
        # Inicializar Supabase
        supabase_manager = SupabaseManager()
        if supabase_manager.connect():
            # Indexar produtos existentes
            produtos = supabase_manager.get_produtos()
            if produtos:
                weaviate_manager.indexar_produtos(produtos)
                logger.info(f"✅ Supabase conectado - {len(produtos)} produtos indexados")
            else:
                logger.info("✅ Supabase conectado - nenhum produto encontrado")
        else:
            logger.warning("⚠️ Supabase não disponível")
        
        # Inicializar Decomposer (GROQ)
        api_key = os.environ.get("GROQ_API_KEY", GROQ_API_KEY)
        if not api_key:
            raise ValueError("GROQ_API_KEY não encontrada")
        
        decomposer = SolutionDecomposer(api_key)
        logger.info("✅ Decomposer (GROQ) inicializado")
        
        logger.info("🎉 Todos os serviços inicializados com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar serviços: {e}")
        raise

if __name__ == '__main__':
    try:
        initialize_services()
        
        # Se estiver no Render, ele define $PORT. Caso contrário, use suas variáveis locais
        port = int(os.environ.get('PORT', os.environ.get('PYTHON_API_PORT', 5001)))
        host = '0.0.0.0' if 'PORT' in os.environ else os.environ.get('PYTHON_API_HOST', '127.0.0.1')
        debug = os.environ.get('PYTHON_API_DEBUG', 'false').lower() == 'true'
        
        logger.info(f"🌐 Iniciando API Python em {host}:{port}")
        
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )    
    except KeyboardInterrupt:
        logger.info("🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar servidor: {e}")
    finally:
        # Cleanup
        if weaviate_manager:
            weaviate_manager.close()
        logger.info("🧹 Recursos liberados")
