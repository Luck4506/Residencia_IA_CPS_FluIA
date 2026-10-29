"""Inicia o programa a partir da pasta do projeto."""
import sys
from pathlib import Path

# Permite importar os arquivos da pasta scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
from buscar_relevancia_embeddings import main

if __name__ == '__main__':
    # Mantém os comandos que já eram usados no terminal.
    if len(sys.argv) > 1:
        comando = sys.argv[1]

        if comando in {'indexar', 'perguntar', 'recuperar'}:
            sys.argv.pop(1)

            if comando == 'indexar':
                sys.argv.append('--indexar')
            elif comando == 'recuperar':
                sys.argv.append('--sem-ollama')

    raise SystemExit(main())
