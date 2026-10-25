# 启动脚本：用环境变量配置 DeepSeek，Key 只在本次进程内存在，不落盘。
$ErrorActionPreference = "Stop"

if (-not $env:LLM_API_KEY) {
    $secure = Read-Host "粘贴 DeepSeek API Key（输入不会显示，直接回车则跳过）" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $env:LLM_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        Remove-Variable secure
    }
}

if (-not $env:LLM_API_URL) { $env:LLM_API_URL = "https://api.deepseek.com/chat/completions" }
if (-not $env:LLM_MODEL) { $env:LLM_MODEL = "deepseek-flash" }
if (-not $env:PORT) { $env:PORT = "8766" }

Write-Host "启动中：http://127.0.0.1:$($env:PORT)  模型=$($env:LLM_MODEL)  Key=$(if ($env:LLM_API_KEY) { '已设置' } else { '未设置' })"
try {
    python main.py
}
finally {
    Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
}
