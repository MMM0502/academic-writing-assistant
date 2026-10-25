# 启动脚本：首次输入 DeepSeek Key 后会保存到同目录 .env，之后每次启动自动带上。
$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot ".env"

function Read-EnvValue([string]$name) {
    if (-not (Test-Path $envFile)) { return "" }
    $line = Get-Content -Path $envFile -Encoding UTF8 |
        Where-Object { $_ -match "^\s*$name\s*=" } |
        Select-Object -First 1
    if (-not $line) { return "" }
    return (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}

function Write-EnvValue([string]$name, [string]$value) {
    $lines = @()
    if (Test-Path $envFile) { $lines = @(Get-Content -Path $envFile -Encoding UTF8) }
    $replaced = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$name\s*=") {
            $lines[$i] = "$name=$value"
            $replaced = $true
            break
        }
    }
    if (-not $replaced) { $lines += "$name=$value" }
    [IO.File]::WriteAllLines($envFile, $lines, (New-Object Text.UTF8Encoding($false)))
}

$key = $env:LLM_API_KEY
if (-not $key) { $key = Read-EnvValue "LLM_API_KEY" }
if (-not $key) {
    $secure = Read-Host "首次配置：粘贴 DeepSeek API Key（输入不会显示，直接回车可跳过）" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        Remove-Variable secure
    }
    if ($key) {
        Write-EnvValue "LLM_API_KEY" $key
        Write-Host "已保存到 .env：以后直接运行 .\start.ps1 就会自动带上这个 Key。"
    }
}

if ($key) { $env:LLM_API_KEY = $key }
if (-not $env:LLM_API_URL) {
    $env:LLM_API_URL = Read-EnvValue "LLM_API_URL"
    if (-not $env:LLM_API_URL) { $env:LLM_API_URL = "https://api.deepseek.com/chat/completions" }
}
if (-not $env:LLM_MODEL) {
    $env:LLM_MODEL = Read-EnvValue "LLM_MODEL"
    if (-not $env:LLM_MODEL) { $env:LLM_MODEL = "deepseek-flash" }
}
if (-not $env:PORT) { $env:PORT = "8766" }

$state = if ($env:LLM_API_KEY) { "已配置" } else { "未配置（综述将用本地规则引擎）" }
Write-Host "启动：http://127.0.0.1:$($env:PORT)  模型=$($env:LLM_MODEL)  大模型=$state"

try {
    python main.py
}
finally {
    Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
}
