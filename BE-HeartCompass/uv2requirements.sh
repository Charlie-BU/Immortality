if [ -f requirements.txt ]; then
    rm requirements.txt
fi

uv export --no-hashes --no-annotate --format=requirements.txt > requirements.txt