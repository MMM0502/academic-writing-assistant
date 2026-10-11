$ErrorActionPreference = "Stop"

$env:LLM_API_URL = "https://api.deepseek.com/chat/completions"
$env:LLM_MODEL = "deepseek-flash"
$env:DATA_DIR = ".data-runtime"
$secureKey = Read-Host "粘贴新 DeepSeek API Key（输入不会显示）" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:LLM_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    Remove-Variable secureKey
}

try {
    python main.py
}
finally {
    Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
}
