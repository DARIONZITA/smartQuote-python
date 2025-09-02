"""
Ponto de entrada principal para deploy no Render.
Este arquivo importa a aplicação Flask do módulo busca_local.
"""

# Importar a aplicação Flask
try:
    from busca_local.app import app
    
    # Tornar o app disponível para WSGI servers (como Gunicorn)
    application = app
    
except ImportError as e:
    print(f"Erro ao importar busca_local.app: {e}")
    print("Verificando se o módulo busca_local está disponível...")
    
    # Fallback: tentar importar diretamente
    import sys
    import os
    
    # Adicionar o diretório atual ao path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    busca_local_dir = os.path.join(current_dir, 'busca_local')
    
    if os.path.exists(busca_local_dir):
        sys.path.insert(0, busca_local_dir)
        try:
            import app as busca_local_app
            application = busca_local_app.app
        except ImportError as e2:
            print(f"Erro no fallback: {e2}")
            raise e
    else:
        print(f"Diretório busca_local não encontrado em: {current_dir}")
        raise e
