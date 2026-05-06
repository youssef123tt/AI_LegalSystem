$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
  Write-Host "Missing .env. Create it from .env.example first."
  exit 1
}

docker compose -f .\infra\docker-compose.yml up --build

