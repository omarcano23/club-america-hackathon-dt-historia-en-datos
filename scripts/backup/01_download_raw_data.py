"""
Script de Descarga por Capas (Corrección de Lineups) - Proyecto Club América ISAC 2026
Garantiza que events, frames_360 y lineups se guarden como JSONs nativos estructurados.
"""
import argparse
import json
import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

username = os.getenv("SB_USERNAME", "").strip()
password = os.getenv("SB_PASSWORD", "")

if not username or not password:
    sys.exit("Error: Faltan credenciales SB_USERNAME / SB_PASSWORD en el archivo .env")

try:
    from statsbombpy import sb
except ImportError:
    sys.exit("Error: La librería 'statsbombpy' no está instalada.")

CREDS = {"user": username, "passwd": password}

def serialize_for_json(obj):
    """
    Convierte cualquier objeto (DataFrame, Dict de DataFrames, Series)
    a estructuras nativas de Python (dict/list) compatibles con json.dumps.
    """
    if isinstance(obj, pd.DataFrame):
        return json.loads(obj.to_json(orient="records", force_ascii=False))
    elif isinstance(obj, dict):
        clean_dict = {}
        for k, v in obj.items():
            if isinstance(v, pd.DataFrame):
                clean_dict[k] = json.loads(v.to_json(orient="records", force_ascii=False))
            else:
                clean_dict[k] = serialize_for_json(v)
        return clean_dict
    elif hasattr(obj, "to_json"):
        return json.loads(obj.to_json(orient="records", force_ascii=False))
    return obj

def save_clean_json(path: Path, value):
    """Guarda en disco un JSON estructurado de forma limpia."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_value = serialize_for_json(value)
    path.write_text(
        json.dumps(clean_value, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

def get_matches_index():
    """Obtiene y guarda el índice de partidos de Jardine."""
    seasons = [281, 317] # 2023/2024 y 2024/2025
    all_matches = []
    
    print("=== CAPA 1: Extrayendo índice de partidos ===")
    for season_id in seasons:
        try:
            matches = sb.matches(competition_id=73, season_id=season_id, creds=CREDS)
            matches_df = pd.DataFrame(matches)
            matches_df['season_id_ref'] = season_id
            all_matches.append(matches_df)
            print(f"  -> Temporada {season_id}: {len(matches_df)} partidos.")
        except Exception as e:
            print(f"  [!] Error en season {season_id}: {e}")

    if not all_matches:
        sys.exit("Error: No se obtuvieron partidos.")

    df = pd.concat(all_matches, ignore_index=True)
    
    # Filtrar Club América
    def check_america(val):
        s = str(val).lower()
        return "américa" in s or "america" in s

    america_df = df[df["home_team"].apply(check_america) | df["away_team"].apply(check_america)].copy()
    
    # Filtrar André Jardine
    def check_jardine(row):
        m = str(row.get("home_managers", "")) + " " + str(row.get("away_managers", ""))
        return "jardine" in m.lower() or "andré" in m.lower() or "andre" in m.lower()

    jardine_df = america_df[america_df.apply(check_jardine, axis=1)].copy()
    
    # Guardar índice filtrado en data/raw
    jardine_index_path = ROOT / "data" / "raw" / "jardine_matches_index.json"
    save_clean_json(jardine_index_path, jardine_df)
    print(f"Índice guardado: {len(jardine_df)} partidos de Jardine.")
    return jardine_df

def download_all_match_data(matches_df, limit=None):
    """Descarga los recursos de todos los partidos de la muestra."""
    print("\n=== CAPA 2: Descargando eventos, alineaciones y frames 360 ===")
    match_ids = matches_df["match_id"].tolist()
    if limit:
        print(f"Modo prueba: Descargando únicamente los primeros {limit} partidos.")
        match_ids = match_ids[:limit]

    total = len(match_ids)
    for idx, m_id in enumerate(match_ids, start=1):
        match_dir = ROOT / "data" / "raw" / "matches" / str(m_id)
        print(f"[{idx}/{total}] Descargando datos para partido ID {m_id}...")
        
        resources = [
            ("events", lambda: sb.events(match_id=m_id, creds=CREDS)),
            ("lineups", lambda: sb.lineups(match_id=m_id, creds=CREDS)),
            ("frames_360", lambda: sb.frames(match_id=m_id, creds=CREDS)),
        ]
        
        for name, loader in resources:
            file_path = match_dir / f"{name}.json"
            try:
                res = loader()
                if res is not None:
                    save_clean_json(file_path, res)
            except Exception as e:
                print(f"   [!] Error cargando {name} en partido {m_id}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limitar número de partidos")
    args = parser.parse_args()
    
    df_jardine = get_matches_index()
    download_all_match_data(df_jardine, limit=args.limit)
    print("\nDescarga RAW completada.")