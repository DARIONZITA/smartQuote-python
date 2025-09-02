"""
WSGI entry point para deploy em serviços como Render, Heroku, etc.
"""

import os
import sys

# Adicionar o diretório atual ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importar a aplicação
try:
    # Tentar importar como módulo
    from busca_local.app import app as application
except ImportError:
    try:
        # Fallback: importar diretamente
        from app import app as application
    except ImportError:
        # Último recurso: tentar carregar do diretório busca_local
        busca_local_path = os.path.join(current_dir, 'busca_local')
        if os.path.exists(busca_local_path):
            sys.path.insert(0, busca_local_path)
            from app import app as application
        else:
            raise ImportError("Não foi possível encontrar a aplicação Flask")

# Para compatibilidade com diferentes servidores WSGI
app = application

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port)
