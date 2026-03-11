# history.ps1 -- Enumerate restart events over a configurable time range
#
# Returns JSON array of restart events sorted newest-first.
# Each entry has: time, type, event_id, message.
#
# Types: START, CLEAN_STOP, DIRTY_SHUTDOWN, INITIATED_RESTART, BSOD
#
# Usage:
#   powershell -File history.ps1
#   powershell -File history.ps1 -Days 90

param(
    [int]$Days = 30
)

$lookback = (Get-Date).AddDays(-$Days)
$results = @()

# Boot events (6005 = start, 6006 = clean stop, 6008 = dirty shutdown)
$bootEvents = Get-WinEvent -FilterHashtable @{
    LogName='System'; ProviderName='EventLog'; Id=@(6005,6006,6008); StartTime=$lookback
} -ErrorAction SilentlyContinue

foreach ($e in $bootEvents) {
    $label = switch ($e.Id) {
        6005 { "START" }
        6006 { "CLEAN_STOP" }
        6008 { "DIRTY_SHUTDOWN" }
    }
    $msg = $e.Message
    if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
    $results += @{
        time = $e.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
        type = $label
        event_id = $e.Id
        message = $msg
    }
}

# Shutdown initiators (1074)
$shutdowns = Get-WinEvent -FilterHashtable @{
    LogName='System'; Id=1074; StartTime=$lookback
} -ErrorAction SilentlyContinue

foreach ($e in $shutdowns) {
    $msg = $e.Message
    if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
    $results += @{
        time = $e.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
        type = "INITIATED_RESTART"
        event_id = $e.Id
        message = $msg
    }
}

# BugCheck events (BSOD via Windows Error Reporting)
$bugchecks = Get-WinEvent -FilterHashtable @{
    LogName='System'; Id=1001; StartTime=$lookback
} -ErrorAction SilentlyContinue | Where-Object { $_.Message -match "BugCheck" }

foreach ($e in $bugchecks) {
    $msg = $e.Message
    if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
    $results += @{
        time = $e.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
        type = "BSOD"
        event_id = $e.Id
        message = $msg
    }
}

$sorted = $results | Sort-Object { [datetime]$_.time } -Descending
$sorted | ConvertTo-Json -Compress
