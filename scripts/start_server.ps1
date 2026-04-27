# Plector v2.0 升级 - 服务器启动脚本
# 用法: .\start_server.ps1
$ErrorActionPreference = "Stop"
Set-Location "E:\产品\Plector-v2-upgrade"

Write-Host "Starting Plector WebSocket server on port 8082..."
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "E:\产品\Plector-v2-upgrade"

$proc = Start-Process `
    -FilePath "python" `
    -ArgumentList "channels/websocket.py", "--port", "8082" `
    -WorkingDirectory "E:\产品\Plector-v2-upgrade" `
    -PassThru `
    -NoNewWindow

Write-Host "Plector PID = $($proc.Id)"
Write-Host "Waiting 3 seconds..."
Start-Sleep 3

if ($proc.HasExited) {
    Write-Host "[FAIL] Process exited with code $($proc.ExitCode)"
    exit 1
}

# Health check
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8082/api/health" -TimeoutSec 5
    Write-Host "[OK] Server health: $($resp.StatusCode)"
} catch {
    Write-Host "[WARN] Health check failed: $_"
}

Write-Host ""
Write-Host "Server is running. Now run:"
Write-Host "  python scripts/upgrade_loop.py"
Write-Host ""
Write-Host "To stop: Stop-Process -Id $($proc.Id) -Force"
