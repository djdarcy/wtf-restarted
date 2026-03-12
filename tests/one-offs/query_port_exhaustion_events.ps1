# Query event logs for port exhaustion evidence
# Event IDs: 4227 (Tcpip endpoint reuse failure), 4231 (TCP limit), 4266 (ephemeral port exhaustion)
# Also checks Resource-Exhaustion provider and Tcpip provider events

Write-Host "=== Port Exhaustion Events (4227, 4231, 4266) ===" -ForegroundColor Cyan
try {
    $portEvents = Get-WinEvent -LogName System -MaxEvents 20000 | Where-Object {
        $_.Id -in @(4227, 4231, 4266) -or $_.ProviderName -like '*Resource-Exhaustion*'
    }
    if ($portEvents) {
        Write-Host "Found $($portEvents.Count) port exhaustion events:" -ForegroundColor Yellow
        $portEvents | Select-Object TimeCreated, Id, ProviderName, @{
            N='Msg'; E={ $_.Message.Substring(0, [Math]::Min(250, $_.Message.Length)) }
        } | Format-Table -AutoSize -Wrap
    } else {
        Write-Host "No port exhaustion events (4227/4231/4266) found in recent System log." -ForegroundColor Green
    }
} catch {
    Write-Host "Error querying: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== All Tcpip Provider Events (last 30 days) ===" -ForegroundColor Cyan
try {
    $cutoff = (Get-Date).AddDays(-30)
    $tcpip = Get-WinEvent -LogName System -MaxEvents 20000 | Where-Object {
        $_.ProviderName -eq 'Tcpip' -and $_.TimeCreated -ge $cutoff
    }
    if ($tcpip) {
        Write-Host "Found $($tcpip.Count) Tcpip events:" -ForegroundColor Yellow
        $tcpip | Group-Object Id | Select-Object @{N='EventID';E={$_.Name}}, Count | Sort-Object Count -Descending | Format-Table -AutoSize
        Write-Host "Details:"
        $tcpip | Select-Object TimeCreated, Id, LevelDisplayName, @{
            N='Msg'; E={ $_.Message.Substring(0, [Math]::Min(250, $_.Message.Length)) }
        } | Format-Table -AutoSize -Wrap
    } else {
        Write-Host "No Tcpip provider events in last 30 days." -ForegroundColor Green
    }
} catch {
    Write-Host "Error querying: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Current TCP State Snapshot ===" -ForegroundColor Cyan
$tcp = Get-NetTCPConnection -ErrorAction SilentlyContinue
$tcp | Group-Object State | Select-Object Name, Count | Sort-Object Count -Descending | Format-Table -AutoSize
Write-Host "Total TCP connections: $($tcp.Count)"
Write-Host "Total UDP endpoints:  $((Get-NetUDPEndpoint -ErrorAction SilentlyContinue).Count)"
Write-Host ""
Write-Host "Dynamic port range:"
netsh int ipv4 show dynamicport tcp
netsh int ipv4 show dynamicport udp

Write-Host ""
Write-Host "=== Top 10 Processes by TCP Connections ===" -ForegroundColor Cyan
$tcp | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 10 | ForEach-Object {
    $pname = (Get-Process -Id $_.Name -ErrorAction SilentlyContinue).Name
    Write-Host ("  PID {0,7} ({1,-30}) : {2} connections" -f $_.Name, $pname, $_.Count)
}

Write-Host ""
Write-Host "=== Top 10 Processes by UDP Endpoints ===" -ForegroundColor Cyan
$udp = Get-NetUDPEndpoint -ErrorAction SilentlyContinue
$udp | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 10 | ForEach-Object {
    $pname = (Get-Process -Id $_.Name -ErrorAction SilentlyContinue).Name
    Write-Host ("  PID {0,7} ({1,-30}) : {2} endpoints" -f $_.Name, $pname, $_.Count)
}

Write-Host ""
Write-Host "=== TIME_WAIT Connections (potential exhaustion indicator) ===" -ForegroundColor Cyan
$timeWait = $tcp | Where-Object State -eq 'TimeWait'
if ($timeWait) {
    Write-Host "TIME_WAIT count: $($timeWait.Count)" -ForegroundColor Yellow
    $timeWait | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 10 | ForEach-Object {
        $pname = (Get-Process -Id $_.Name -ErrorAction SilentlyContinue).Name
        Write-Host ("  PID {0,7} ({1,-30}) : {2} TIME_WAIT" -f $_.Name, $pname, $_.Count)
    }
} else {
    Write-Host "No TIME_WAIT connections." -ForegroundColor Green
}
