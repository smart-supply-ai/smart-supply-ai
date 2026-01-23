#!/usr/bin/env bash
set -e
docker compose --env-file .env -f infra/docker-compose.yml down
echo "Dev environment has been stopped."