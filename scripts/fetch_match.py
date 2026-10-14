"""Download authorized match resources using statsbombpy."""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(value, "to_json"):
        # Preserve a DataFrame in a readable JSON form.
        value.to_json(path, orient="records", indent=2, force_ascii=False)
    else:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    print(f"Saved {path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True, type=int)
    args = parser.parse_args()

    username = os.getenv("SB_USERNAME", "").strip()
    password = os.getenv("SB_PASSWORD", "")
    if not username or not password:
        sys.exit("Missing credentials. Set SB_USERNAME and SB_PASSWORD in local .env.")

    from statsbombpy import sb

    creds = {"user": username, "passwd": password}
    match_dir = ROOT / "data" / "raw" / "matches" / str(args.match_id)
    resources = [
        ("events", lambda: sb.events(match_id=args.match_id, creds=creds)),
        ("lineups", lambda: sb.lineups(match_id=args.match_id, creds=creds)),
        ("frames_360", lambda: sb.frames(match_id=args.match_id, creds=creds)),
    ]

    errors = []
    for name, loader in resources:
        try:
            result = loader()
            if result is None:
                print(f"{name}: no data returned (may be unavailable for this match).")
                continue
            # Save DataFrames as JSON records; events can be large.
            save_json(match_dir / f"{name}.json", result)
        except Exception as exc:
            errors.append((name, type(exc).__name__, str(exc)))
            print(f"{name}: unavailable or failed ({type(exc).__name__}: {exc})")

    if errors:
        print("\nSome resources failed. Check match access and 360 availability.")
        print("This does not necessarily mean the other resources are invalid.")
    else:
        print("Download attempt completed. Verify files and coverage before analysis.")


if __name__ == "__main__":
    main()
