
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../src/database" || exit 1
export PYTHONPATH="$(pwd)/../..:$(pwd)/..${PYTHONPATH:+:$PYTHONPATH}"

echo "Database Migration Start..."
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "db migrate"
uv run alembic upgrade head
echo "Database Migration Ended"
