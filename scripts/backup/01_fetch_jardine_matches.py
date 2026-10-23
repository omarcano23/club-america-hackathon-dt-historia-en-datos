import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Configurar ruta raíz y cargar variables de entorno
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

username = os.getenv("SB_USERNAME", "").strip()
password = os.getenv("SB_PASSWORD", "")

if not username or not password:
    sys.exit("Error: Faltan credenciales en .env (SB_USERNAME / SB_PASSWORD).")

try:
    from statsbombpy import sb
except ImportError:
    sys.exit("Error: 'statsbombpy' no está instalado en el entorno virtual.")

def fetch_and_filter_jardine_matches():
    raw_dir = ROOT / "data" / "raw"
    processed_dir = ROOT / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    creds = {"user": username, "passwd": password}
    
    # Temporadas seleccionadas para Jardine: 2023/2024 (281) y 2024/2025 (317)
    target_seasons = [281, 317]
    all_matches = []
    
    print("Obteniendo partidos desde la API privada de StatsBomb...")
    for s_id in target_seasons:
        try:
            # Pasar credenciales explícitamente a la API
            matches = sb.matches(competition_id=73, season_id=s_id, creds=creds)
            
            # Si retorna DataFrame o Diccionario, convertir adecuadamente
            if isinstance(matches, dict):
                matches_df = pd.DataFrame.from_dict(matches, orient="index") if not isinstance(list(matches.values())[0], dict) else pd.DataFrame(matches.values())
            else:
                matches_df = pd.DataFrame(matches)
                
            matches_df["season_id_ref"] = s_id
            all_matches.append(matches_df)
            print(f"-> Temporada season_id {s_id}: {len(matches_df)} partidos obtenidos correctamente.")
        except Exception as e:
            print(f"Error al extraer season_id {s_id}: {type(e).__name__}: {e}")
            
    if not all_matches:
        print("\nNo se pudieron extraer partidos. Revisa permisos o conexión.")
        return None
        
    df_matches = pd.concat(all_matches, ignore_index=True)
    
    # Filtrar partidos donde participa el Club América
    america_df = df_matches[
        (df_matches['home_team'] == 'Club América') | 
        (df_matches['away_team'] == 'Club América')
    ].copy()
    
    # Identificar partidos donde André Jardine es el DT
    def is_jardine(row):
        managers = str(row.get('home_managers', '')) + " " + str(row.get('away_managers', ''))
        return 'Jardine' in managers or 'André' in managers or 'Andre' in managers
    
    jardine_df = america_df[america_df.apply(is_jardine, axis=1)].copy()
    
    print("\n================ RESUMEN DE LA MUESTRA ================")
    print(f"Total de partidos en las 2 temporadas: {len(df_matches)}")
    print(f"Total partidos del Club América: {len(america_df)}")
    print(f"Total partidos validados bajo André Jardine: {len(jardine_df)}")
    
    # Desglose por temporada
    if 'season_name' in jardine_df.columns:
        print("\nDesglose por temporada:")
        print(jardine_df['season_name'].value_counts().to_string())
        
    # Guardar localmente
    output_path = processed_dir / "jardine_matches_universe.csv"
    jardine_df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\nGuardado universo de partidos en: {output_path.relative_to(ROOT)}")
    
    return jardine_df

if __name__ == "__main__":
    fetch_and_filter_jardine_matches()