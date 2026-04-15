import subprocess
import sys
from pathlib import Path

def main():
    """Punto de entrada para el CLI."""
    # Encuentra la carpeta donde está instalado este script
    app_dir = Path(__file__).parent
    app_path = app_dir / "app.py"
    
    comando = [sys.executable, "-m", "streamlit", "run", str(app_path)] + sys.argv[1:]
    
    try:
        # cwd=app_dir obliga a Streamlit a ejecutarse desde la carpeta interna
        subprocess.run(comando, cwd=app_dir, check=True)
    except KeyboardInterrupt:
        print("\nSaliendo de la aplicación...")