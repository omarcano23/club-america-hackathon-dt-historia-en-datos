"""Check StatsBomb credentials and save the competitions visible to this account."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

username = os.getenv("SB_USERNAME", "").strip()
password = os.getenv("SB_PASSWORD", "")

if not username or not password:
    sys.exit(
        "Missing credentials. Copy .env.example to .env and set SB_USERNAME and SB_PASSWORD."
    )

try:
    from statsbombpy import sb

    print("Checking StatsBomb access...")
    competitions = sb.competitions(creds={"user": username, "passwd": password})
    if competitions is None:
        sys.exit("The API returned no competitions. Confirm account permissions and API docs.")

    out = ROOT / "data" / "raw" / "competitions.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(competitions, "to_json"):
        payload = json.loads(competitions.to_json(orient="records"))
    else:
        payload = competitions
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    count = len(competitions)
    print(f"Access check succeeded. Competitions returned: {count}")
    print(f"Saved locally to: {out.relative_to(ROOT)}")
    print("Reminder: data files are licensed competition data and must not be committed.")
except Exception as exc:
    # Avoid printing credentials or request headers.
    print(f"Access check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(
        "Check the API overview, credentials, network access, package version, and licensed scope.",
        file=sys.stderr,
    )
    sys.exit(1)
