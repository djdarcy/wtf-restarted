# Check if ttyd actually spawns cmd.exe and if ConPTY pipes exist
# Run this WHILE ttyd is serving on a port

Write-Host "=== ttyd Process Tree Analysis ==="

# Find ttyd processes
$ttydProcs = Get-Process ttyd -ErrorAction SilentlyContinue
if (-not $ttydProcs) {
    Write-Host "No ttyd process found. Start ttyd first."
    return
}

foreach ($proc in $ttydProcs) {
    Write-Host "`nttyd PID: $($proc.Id)"
    Write-Host "  Memory: $([math]::Round($proc.WorkingSet64 / 1MB, 1)) MB"
    Write-Host "  Handles: $($proc.HandleCount)"

    # Check for child processes using WMI
    Write-Host "`n  Child processes:"
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
    if ($children) {
        foreach ($child in $children) {
            Write-Host "    PID $($child.ProcessId): $($child.Name) - $($child.CommandLine)"
        }
    } else {
        Write-Host "    NONE - cmd.exe was NOT spawned!"
    }
}

# Check for named pipes matching ttyd pattern
Write-Host "`n=== Named Pipes (ttyd-term-*) ==="
$pipes = [System.IO.Directory]::GetFiles("\\.\pipe\") | Where-Object { $_ -match "ttyd" }
if ($pipes) {
    foreach ($pipe in $pipes) {
        Write-Host "  $pipe"
    }
} else {
    Write-Host "  No ttyd pipes found"
}

# Also check conhost instances (ConPTY creates conhost)
Write-Host "`n=== conhost.exe instances ==="
$conhosts = Get-CimInstance Win32_Process -Filter "Name = 'conhost.exe'" -ErrorAction SilentlyContinue
$ttydConhosts = $conhosts | Where-Object { $_.ParentProcessId -in $ttydProcs.Id }
if ($ttydConhosts) {
    foreach ($ch in $ttydConhosts) {
        Write-Host "  PID $($ch.ProcessId) (parent: $($ch.ParentProcessId)) - $($ch.CommandLine)"
    }
} else {
    Write-Host "  No conhost spawned by ttyd"
}

Write-Host "`n=== Done ==="
