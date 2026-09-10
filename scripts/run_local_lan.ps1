param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$lanAddress = Get-NetIPConfiguration |
    Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4DefaultGateway } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Select-Object -First 1

if (-not $lanAddress) {
    throw "No active LAN/Wi-Fi IPv4 address was found."
}

Write-Host "EduPilot local server"
Write-Host "PC:      http://127.0.0.1:$Port/"
Write-Host "Wi-Fi:   http://${lanAddress}:$Port/"
Write-Host "Swagger: http://${lanAddress}:$Port/api/docs/"
Write-Host "Flutter build value: http://${lanAddress}:$Port/api/v1"

python manage.py runserver "0.0.0.0:$Port"
