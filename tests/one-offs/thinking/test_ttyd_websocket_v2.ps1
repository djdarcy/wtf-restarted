# Test ttyd websocket data flow - v2 with proper handshake
# ttyd requires the client to send JSON_DATA (starts with '{') with window size
# before it spawns the shell process.

param(
    [int]$Port = 19892
)

Write-Host "=== ttyd WebSocket Test v2 (with handshake) ==="
Write-Host "Testing port $Port..."

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

    # Send the JSON_DATA handshake (window size)
    # This triggers spawn_process() in protocol.c
    $handshake = '{"columns":80,"rows":24}'
    Write-Host "Sending handshake: $handshake"
    $sendBuf = [System.Text.Encoding]::UTF8.GetBytes($handshake)
    $sendSeg = [System.ArraySegment[byte]]::new($sendBuf)
    $sendTask = $ws.SendAsync($sendSeg, [System.Net.WebSockets.WebSocketMessageType]::Binary, $true, $ct)
    $sendTask.Wait(3000) | Out-Null
    Write-Host "Handshake sent"

    # Now try to read terminal output
    Write-Host "Waiting for terminal output..."
    $buf = [byte[]]::new(4096)
    $seg = [System.ArraySegment[byte]]::new($buf)

    for ($i = 0; $i -lt 3; $i++) {
        $readTask = $ws.ReceiveAsync($seg, $ct)
        if ($readTask.Wait(5000)) {
            $count = $readTask.Result.Count
            if ($count -gt 0) {
                # First byte is message type (OUTPUT = '0')
                $msgType = [char]$buf[0]
                $text = [System.Text.Encoding]::UTF8.GetString($buf, 1, $count - 1)
                Write-Host "SUCCESS: Read $count bytes (type=$msgType)"
                Write-Host "Data: $($text.Substring(0, [Math]::Min($text.Length, 200)))"
            } else {
                Write-Host "Read 0 bytes (connection closed?)"
                break
            }
        } else {
            Write-Host "TIMEOUT on read $i - no data"
            break
        }
    }

    $ws.Dispose()
} catch {
    Write-Host "ERROR: $_"
}

Write-Host "`n=== Done ==="
