"""Write the API's OpenAPI schema to a file.

Run: python -m scripts.dump_openapi [output_path]

The Workbench generates its request and response types from this document, so
it is produced from the application object rather than from a running server.
That keeps type generation deterministic and available offline.
"""

import json
import sys
from pathlib import Path

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"


def main() -> int:
    from app.main import create_app

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")
    schemas = len(create_app().openapi().get("components", {}).get("schemas", {}))
    print(f"Wrote {output} ({schemas} schemas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
