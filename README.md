# Club América ISAC 2026 — La historia de un entrenador a través de los datos

Proyecto de analítica táctica con datos autorizados de Hudl StatsBomb. El objetivo es explicar patrones ofensivos, defensivos y contextuales del Club América a través de varios partidos.

## Reglas importantes

- Los datos de la competencia son exclusivamente para el hackathon.
- No subas credenciales, tokens, datos crudos ni datos derivados restringidos al repositorio remoto.
- No incluyas resultados ficticios en el informe final.
- Revisa las condiciones de uso y las instrucciones entregadas por ISAC/StatsBomb.

## 1. Requisitos

- Python 3.11 recomendado
- Git
- Acceso autorizado a la API de StatsBomb

Comprueba tu versión:

```bash
python --version
git --version
```

## 2. Crear entorno e instalar dependencias

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` localmente y añade las credenciales entregadas por StatsBomb. No pegues esas credenciales en el chat ni las guardes en Git.

```dotenv
SB_USERNAME=tu_usuario
SB_PASSWORD=tu_contrasena
```

## 3. Verificar el acceso

```bash
python scripts/check_access.py
```

El script intenta listar las competiciones disponibles para la cuenta y guarda la respuesta localmente en `data/raw/competitions.json`. Si falla, lee el mensaje de error sin imprimir la contraseña.

## 4. Descargar datos de un partido autorizado

Primero identifica el `match_id` de un partido incluido en el alcance del reto. Después:

```bash
python scripts/fetch_match.py --match-id ID_DEL_PARTIDO
```

El script intenta guardar eventos, alineaciones y frames 360 por separado. Un recurso puede no estar disponible aunque los demás sí lo estén. Revisa la salida y el estado de disponibilidad antes de interpretar un archivo ausente como error del código.

## 5. Estructura

```text
config/analysis.yaml       Parámetros iniciales del análisis
data/raw/                  Respuestas originales (ignoradas por Git)
data/processed/            Tablas transformadas (ignoradas por Git)
data/synthetic/            Datos sintéticos solo para pruebas (ignorados por Git)
notebooks/                 Exploración y análisis
report/                    Entregable HTML
scripts/                   Comprobación y descarga
src/club_america_isac/     Código reutilizable
tests/                     Pruebas unitarias
```

## 6. Flujo de trabajo recomendado

1. Confirmar el alcance autorizado: entrenador, lista de partidos y cobertura 360.
2. Ejecutar la comprobación de acceso.
3. Crear un inventario de partidos y campos disponibles.
4. Definir formalmente posesiones, secuencias, transiciones y presión.
5. Validar datos y definiciones antes de producir métricas.
6. Analizar patrones recurrentes y compararlos por contexto.
7. Construir el informe HTML y preparar el video de máximo 5 minutos.

## 7. Git

```bash
git init
git add .
git status
git commit -m "chore: bootstrap Club América ISAC project"
```

Antes de publicar un remoto, revisa `git status` y confirma que `.env` y los datos estén ignorados. El repositorio remoto debe contener código y documentación, no los datos licenciados.

## Referencias

- StatsBomb API overview: https://data.statsbomb.com/api-overview
- StatsBomb Python library: https://github.com/hudl/statsbombpy
- pandas: https://pandas.pydata.org/docs/
- mplsoccer: https://mplsoccer.readthedocs.io/
