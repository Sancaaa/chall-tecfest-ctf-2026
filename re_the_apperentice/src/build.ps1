$ErrorActionPreference = "Stop"

$env:GOOS = "linux"
$env:GOARCH = "amd64"
$env:CGO_ENABLED = "0"

New-Item -ItemType Directory -Force -Path "..\dist" | Out-Null
go build -trimpath -o "..\dist\grimoire" .
Write-Host "Built ..\dist\grimoire"
