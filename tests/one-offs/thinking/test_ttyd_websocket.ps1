# Test ttyd websocket data flow
# Usage: powershell -File test_ttyd_websocket.ps1 [port]
# Connects to ttyd websocket and checks if shell data arrives.

param(
    [int]$Port = 19882
)

Write-Host "Testing ttyd websocket on port $Port..."

try {
    $ws = New-Object System.Net.WebSockets.ClientWebSocket
    $uri = [System.Uri]::new("ws://127.0.0.1:${Port}/ws")
    $ct = [System.Threading.CancellationToken]::None

    $connectTask = $ws.ConnectAsync($uri, $ct)
    if (-not $connectTask.Wait(5000)) {
        Write-Host "FAIL: Connection timeout"
        return
    }
    Write-Host "WebSocket state: $($ws.State)"

    # Try to read data (shell prompt should arrive)
    $buf = [byte[]]::new(4096)
    $seg = [System.ArraySegment[byte]]::new($buf)
    $readTask = $ws.ReceiveAsync($seg, $ct)

    if ($readTask.Wait(5000)) {
        $count = $readTask.Result.Count
        $hex = [BitConverter]::ToString($buf[0..([Math]::Min($count, 64) - 1)])
        Write-Host "SUCCESS: Got $count bytes"
        Write-Host "Hex: $hex"

        # Try to decode as UTF-8
        $text = [System.Text.Encoding]::UTF8.GetString($buf, 0, $count)
        Write-Host "Text: $text"
    } else {
        Write-Host "FAIL: No data received within 5 seconds (ConPTY broken)"
    }

    $ws.Dispose()
} catch {
    Write-Host "ERROR: $_"
}
