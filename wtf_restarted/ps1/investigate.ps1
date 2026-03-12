# investigate.ps1 -- Full restart/crash investigation with JSON output
#
# Modularized from SYSDIAGNOSE crash_investigator.ps1
# Outputs structured JSON for consumption by the Python CLI.
#
# Usage:
#   powershell -File investigate.ps1
#   powershell -File investigate.ps1 -LookbackHours 72
#   powershell -File investigate.ps1 -SkipDump
#   powershell -File investigate.ps1 -JsonOnly
#
# What it checks:
#   1. System uptime and boot time
#   2. Kernel-Power Event 41 (dirty/unexpected shutdown)
#   3. Event 6008 (previous shutdown was unexpected)
#   4. Shutdown initiator Event 1074/1076
#   5. Kernel-Power Event 109 (power transitions)
#   6. BugCheck events (BSOD via Windows Error Reporting)
#   7. WHEA hardware errors
#   8. Windows Update installs near restart
#   9. Application crashes near reboot time
#  10. Crash dump files (MEMORY.DMP + Minidump)
#  11. Boot/shutdown sequence (6005/6006/6008/6009)
#  12. RDP session detection
#  13. Surrounding event context window
#  14. Crash dump analysis via kd.exe (optional)

param(
    [int]$LookbackHours = 48,
    [string]$DumpFile = "",
    [switch]$SkipDump,
    [switch]$JsonOnly,
    [int]$ContextMinutes = 10,
    [string]$SymbolPath = ""
)

# Use _NT_SYMBOL_PATH if set and no explicit path given
if (-not $SymbolPath) {
    $envSymPath = $env:_NT_SYMBOL_PATH
    if ($envSymPath) {
        $SymbolPath = $envSymPath
    } else {
        $SymbolPath = "srv*C:\Symbols*https://msdl.microsoft.com/download/symbols"
    }
}

# Truncate long messages safely
function Truncate-Message {
    param([string]$Msg, [int]$MaxLen = 500)
    if (-not $Msg) { return "(no message)" }
    if ($Msg.Length -le $MaxLen) { return $Msg }
    return $Msg.Substring(0, $MaxLen) + "..."
}

# Format event as hashtable for JSON
function Format-Event {
    param($Event, [int]$MaxLen = 500)
    @{
        time = $Event.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
        id = $Event.Id
        provider = $Event.ProviderName
        message = (Truncate-Message $Event.Message $MaxLen)
    }
}

$now = Get-Date
$lookback = $now.AddHours(-$LookbackHours)

# ===================================================================
# SYSTEM INFO
# ===================================================================

$bootTime = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$uptime = $now - $bootTime

$systemInfo = @{
    current_time = $now.ToString("yyyy-MM-dd HH:mm:ss")
    boot_time = $bootTime.ToString("yyyy-MM-dd HH:mm:ss")
    uptime_seconds = [int]$uptime.TotalSeconds
    uptime_display = $uptime.ToString('d\.hh\:mm\:ss')
    lookback_hours = $LookbackHours
    os_version = [System.Environment]::OSVersion.VersionString
    computer_name = $env:COMPUTERNAME
}

# ===================================================================
# RDP SESSION DETECTION
# ===================================================================

$rdpInfo = @{
    is_rdp = $false
    session_name = $env:SESSIONNAME
    disconnected_sessions = @()
    warning = $null
}

if ($env:SESSIONNAME -match '^RDP-') {
    $rdpInfo.is_rdp = $true

    # Check for disconnected sessions that may have open windows
    try {
        $qsOutput = query session 2>$null
        if ($qsOutput) {
            $discSessions = @()
            foreach ($line in $qsOutput) {
                if ($line -match '\bDisc\b' -and $line -notmatch '^\s*services') {
                    $discSessions += $line.Trim()
                }
            }
            $rdpInfo.disconnected_sessions = $discSessions
            if ($discSessions.Count -gt 0) {
                $rdpInfo.warning = "You are connected via RDP. There are disconnected sessions with potentially open windows. The machine may not have actually restarted -- your windows may still be alive on another session."
            } else {
                $rdpInfo.warning = "You are connected via RDP (not the physical console). If windows appear missing, it may be because this is a new session, not necessarily a restart."
            }
        }
    } catch {
        # query session may not be available
    }
}

# ===================================================================
# EVIDENCE COLLECTION
# ===================================================================

$evidence = @{
    dirty_shutdown = $false
    bugcheck = $false
    initiated_by = $null
    whea_error = $false
    windows_update = $false
    crash_dump_exists = $false
    previous_uptime = $null
}

$events = @{}

# --- 1. Kernel-Power Event 41 (unexpected shutdown) ---
$kp41 = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=41; StartTime=$lookback} -ErrorAction SilentlyContinue
$events.kernel_power_41 = @()
if ($kp41) {
    $evidence.dirty_shutdown = $true
    foreach ($e in $kp41) {
        $events.kernel_power_41 += Format-Event $e
    }
}

# --- 2. Event 6008 (previous shutdown was unexpected) ---
$ev6008 = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6008; StartTime=$lookback} -ErrorAction SilentlyContinue
$events.event_6008 = @()
if ($ev6008) {
    $evidence.dirty_shutdown = $true
    foreach ($e in $ev6008) {
        $events.event_6008 += Format-Event $e
    }
}

# --- 3. Shutdown initiator Event 1074/1076 ---
$shutdown = Get-WinEvent -FilterHashtable @{LogName='System'; Id=@(1074,1076); StartTime=$lookback} -ErrorAction SilentlyContinue
$events.shutdown_initiator = @()
if ($shutdown) {
    foreach ($e in $shutdown | Select-Object -First 5) {
        $evidence.initiated_by = (Truncate-Message $e.Message 1000)
        $events.shutdown_initiator += Format-Event $e 1000
    }
}

# --- 4. Kernel-Power Event 109 (power transitions) ---
$kp109 = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=109; StartTime=$lookback} -ErrorAction SilentlyContinue
$events.power_transitions = @()
if ($kp109) {
    foreach ($e in $kp109 | Select-Object -First 5) {
        $events.power_transitions += Format-Event $e 300
    }
}

# --- 5. BugCheck events (Windows Error Reporting) ---
$events.bugcheck = @()
$bugchecks = Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001; StartTime=$lookback} -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match "BugCheck|bugcheck|BlueScreen" }
if ($bugchecks) {
    $evidence.bugcheck = $true
    foreach ($e in $bugchecks | Select-Object -First 5) {
        $events.bugcheck += Format-Event $e
    }
}
$bugchecksApp = Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Windows Error Reporting'; StartTime=$lookback} -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match "BugCheck|BlueScreen|LiveKernelEvent" }
if ($bugchecksApp) {
    $evidence.bugcheck = $true
    foreach ($e in $bugchecksApp | Select-Object -First 5) {
        $events.bugcheck += Format-Event $e
    }
}

# --- 6. WHEA hardware errors ---
$whea = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WHEA-Logger'; StartTime=$lookback} -ErrorAction SilentlyContinue
$events.whea = @()
if ($whea) {
    $evidence.whea_error = $true
    foreach ($e in $whea | Select-Object -First 5) {
        $events.whea += Format-Event $e 300
    }
}

# --- 7. Windows Update installs ---
$events.windows_update = @()
$wuEvents = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WindowsUpdateClient'; StartTime=$lookback} -ErrorAction SilentlyContinue
if ($wuEvents) {
    $rebootUpdates = $wuEvents | Where-Object { $_.Id -eq 19 -or $_.Id -eq 20 }
    if ($rebootUpdates) {
        foreach ($e in $rebootUpdates | Select-Object -First 10) {
            $minutesBefore = ($bootTime - $e.TimeCreated).TotalMinutes
            $isNearCrash = $minutesBefore -gt 0 -and $minutesBefore -lt 30
            $formatted = Format-Event $e 250
            $formatted.near_crash = $isNearCrash
            $events.windows_update += $formatted
            if ($isNearCrash) {
                $evidence.windows_update = $true
            }
        }
    }
}

# --- 8. Application crashes near reboot ---
$events.app_crashes = @()
$preCrashStart = $bootTime.AddHours(-1)
$appErrors = Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'; StartTime=$preCrashStart} -ErrorAction SilentlyContinue
if ($appErrors) {
    foreach ($e in $appErrors | Select-Object -First 10) {
        $events.app_crashes += Format-Event $e 300
    }
}

# --- 9. Crash dump files ---
$dumpInfo = @{
    memory_dmp = $null
    minidumps = @()
    recent_dumps = @()
}
$foundDumps = @()

if (Test-Path "C:\Windows\MEMORY.DMP") {
    $f = Get-Item "C:\Windows\MEMORY.DMP"
    $isRecent = ($now - $f.LastWriteTime).TotalHours -lt $LookbackHours
    $dumpInfo.memory_dmp = @{
        path = $f.FullName
        size_mb = [Math]::Round($f.Length / 1MB, 1)
        modified = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        recent = $isRecent
    }
    if ($isRecent) {
        $foundDumps += $f.FullName
        $evidence.crash_dump_exists = $true
    }
}

if (Test-Path "C:\Windows\Minidump") {
    $files = Get-ChildItem "C:\Windows\Minidump" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10
    foreach ($f in $files) {
        $isRecent = ($now - $f.LastWriteTime).TotalHours -lt $LookbackHours
        $entry = @{
            path = $f.FullName
            size_mb = [Math]::Round($f.Length / 1MB, 1)
            modified = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            recent = $isRecent
        }
        $dumpInfo.minidumps += $entry
        if ($isRecent) {
            $foundDumps += $f.FullName
        }
    }
}

# --- 10. Boot/shutdown sequence ---
$events.boot_sequence = @()
$bootShutdown = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=@(6005,6006,6008,6009); StartTime=$lookback} -ErrorAction SilentlyContinue
if ($bootShutdown) {
    foreach ($e in $bootShutdown | Select-Object -First 15) {
        $label = switch ($e.Id) {
            6005 { "START" }
            6006 { "CLEAN_STOP" }
            6008 { "DIRTY_SHUTDOWN" }
            6009 { "OS_VERSION" }
            default { "UNKNOWN" }
        }
        $formatted = Format-Event $e 500
        $formatted.label = $label
        $events.boot_sequence += $formatted
    }
}

# --- 11. Previous boot duration ---
$previousBoot = @{}
$allStarts = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6005; StartTime=$now.AddDays(-7)} -ErrorAction SilentlyContinue
if ($allStarts -and $allStarts.Count -ge 2) {
    $currentBoot = $allStarts[0].TimeCreated
    $prevBoot = $allStarts[1].TimeCreated
    $prevUptime = $currentBoot - $prevBoot
    $evidence.previous_uptime = $prevUptime.ToString('d\.hh\:mm\:ss')
    $previousBoot = @{
        previous_boot = $prevBoot.ToString("yyyy-MM-dd HH:mm:ss")
        current_boot = $currentBoot.ToString("yyyy-MM-dd HH:mm:ss")
        previous_uptime = $prevUptime.ToString('d\.hh\:mm\:ss')
        previous_uptime_seconds = [int]$prevUptime.TotalSeconds
    }
}

# --- 12. Surrounding events context window ---
$events.context_window = @()
$contextStart = $bootTime.AddMinutes(-$ContextMinutes)
$contextEnd = $bootTime.AddMinutes(5)
$contextEvents = Get-WinEvent -FilterHashtable @{LogName='System'; Level=@(1,2,3); StartTime=$contextStart; EndTime=$contextEnd} -ErrorAction SilentlyContinue
if ($contextEvents) {
    foreach ($e in $contextEvents | Select-Object -First 30) {
        $events.context_window += Format-Event $e 300
    }
}
# Also check Application log
$contextEventsApp = Get-WinEvent -FilterHashtable @{LogName='Application'; Level=@(1,2,3); StartTime=$contextStart; EndTime=$contextEnd} -ErrorAction SilentlyContinue
if ($contextEventsApp) {
    foreach ($e in $contextEventsApp | Select-Object -First 20) {
        $events.context_window += Format-Event $e 300
    }
}

# --- 13. GPU driver events (TDR / display driver recovery) ---
$events.gpu_events = @()
$gpuEvents = Get-WinEvent -FilterHashtable @{LogName='System'; Id=@(4101,4097); StartTime=$lookback} -ErrorAction SilentlyContinue
if ($gpuEvents) {
    foreach ($e in $gpuEvents | Select-Object -First 5) {
        $events.gpu_events += Format-Event $e 300
    }
}
# nvlddmkm specific events
$nvEvents = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='nvlddmkm'; StartTime=$lookback} -ErrorAction SilentlyContinue
if ($nvEvents) {
    foreach ($e in $nvEvents | Select-Object -First 5) {
        $events.gpu_events += Format-Event $e 300
    }
}

# ===================================================================
# VERDICT
# ===================================================================

$verdict = @{
    type = "UNKNOWN"
    summary = ""
    details = @()
}

if ($evidence.crash_dump_exists -and $evidence.dirty_shutdown) {
    $verdict.type = "BSOD"
    $verdict.summary = "Blue Screen of Death (BSOD) - crash dump found with dirty shutdown."
    $verdict.details += "Crash dump found + dirty shutdown confirmed."
    $verdict.details += "Run with dump analysis for bugcheck details."
} elseif ($evidence.bugcheck -and $evidence.dirty_shutdown) {
    $verdict.type = "BSOD"
    $verdict.summary = "Blue Screen of Death (BSOD) - bugcheck event with dirty shutdown."
    $verdict.details += "BugCheck event detected in Windows Error Reporting."
} elseif ($evidence.dirty_shutdown -and -not $evidence.initiated_by) {
    $verdict.type = "UNEXPECTED_SHUTDOWN"
    $verdict.summary = "Unexpected shutdown - power loss, hardware reset, or BSOD without dump."
    $verdict.details += "Dirty shutdown with no initiating process."
    if ($evidence.whea_error) {
        $verdict.details += "WHEA hardware error detected -- possible hardware fault."
    }
} elseif ($evidence.initiated_by -and -not $evidence.dirty_shutdown) {
    $verdict.type = "INITIATED_RESTART"

    # Parse Event 1074 message for structured fields
    $msg1074 = $evidence.initiated_by
    $initiatorProcess = ""
    $initiatorUser = ""
    $initiatorReason = ""
    $reasonCode = ""
    $shutdownType = ""

    if ($msg1074 -match 'The process (.+?) \(.+?\) has initiated the') {
        $initiatorProcess = $Matches[1].Trim()
    }
    if ($msg1074 -match 'on behalf of user (.+?) for the following reason:') {
        $initiatorUser = $Matches[1].Trim()
    }
    if ($msg1074 -match 'for the following reason:\s*(.+?)(?:\s*Reason Code:|$)') {
        $initiatorReason = $Matches[1].Trim()
    }
    if ($msg1074 -match 'Reason Code:\s*(0x[0-9A-Fa-f]+)') {
        $reasonCode = $Matches[1]
    }
    if ($msg1074 -match 'Shutdown Type:\s*(\S+)') {
        $shutdownType = $Matches[1].Trim()
    }

    # Build readable summary
    $processName = if ($initiatorProcess) {
        Split-Path $initiatorProcess -Leaf
    } else { "" }

    if ($evidence.windows_update -or $initiatorProcess -match 'TrustedInstaller') {
        if ($processName) {
            $verdict.summary = "Windows Update ($processName) restarted your PC."
        } else {
            $verdict.summary = "Windows Update triggered the restart."
        }
        $verdict.details += "Windows Update activity detected near restart time."
    } elseif ($processName) {
        $verdict.summary = "$processName requested the restart."
    } else {
        $verdict.summary = "A process or user requested the restart."
    }

    if ($initiatorReason) {
        $verdict.details += "Reason: $initiatorReason"
    }
    $verdict.details += "Shutdown initiator found in Event 1074."

    # Structured fields for downstream consumers (AI, JSON)
    $verdict.initiator_process = $initiatorProcess
    $verdict.initiator_user = $initiatorUser
    $verdict.initiator_reason = $initiatorReason
    $verdict.reason_code = $reasonCode
    $verdict.shutdown_type = $shutdownType
} elseif ($evidence.dirty_shutdown -and $evidence.initiated_by) {
    $verdict.type = "MIXED_SIGNALS"
    $verdict.summary = "Both dirty shutdown and restart initiator found."
    $verdict.details += "Check timestamps to determine if crash interrupted a planned restart."
} else {
    $verdict.type = "CLEAN_RESTART"
    $verdict.summary = "No evidence of unexpected shutdown. Most recent restart was clean."
}

# ===================================================================
# CRASH DUMP ANALYSIS (Phase 2, optional)
# ===================================================================

$dumpAnalysis = @{
    performed = $false
    dump_file = $null
    kd_available = $false
    bugcheck_code = $null
    module = $null
    image = $null
    symbol = $null
    process = $null
    bucket = $null
    raw_output = $null
}

if (-not $SkipDump) {
    $targetDump = $DumpFile
    if (-not $targetDump -and $foundDumps.Count -gt 0) {
        $targetDump = $foundDumps[0]
    }
    if (-not $targetDump -and (Test-Path "C:\Windows\MEMORY.DMP")) {
        $targetDump = "C:\Windows\MEMORY.DMP"
    }

    if ($targetDump -and (Test-Path $targetDump)) {
        $dumpAnalysis.dump_file = $targetDump

        # Find kd.exe -- registry-first, then known paths, then PATH
        $kdPath = $null
        $arch = "x64"

        # 1. Registry: WindowsDebuggersRoot10 (most reliable)
        $regHives = @(
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows Kits\Installed Roots",
            "HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots"
        )
        foreach ($hive in $regHives) {
            $props = Get-ItemProperty $hive -ErrorAction SilentlyContinue
            if ($props.WindowsDebuggersRoot10) {
                $candidate = Join-Path $props.WindowsDebuggersRoot10 "$arch\kd.exe"
                if (Test-Path $candidate) { $kdPath = $candidate; break }
            }
            if (-not $kdPath -and $props.KitsRoot10) {
                $candidate = Join-Path $props.KitsRoot10 "Debuggers\$arch\kd.exe"
                if (Test-Path $candidate) { $kdPath = $candidate; break }
            }
        }

        # 2. Well-known filesystem paths
        if (-not $kdPath) {
            $kdFallbacks = @(
                "C:\Program Files (x86)\Windows Kits\10\Debuggers\$arch\kd.exe",
                "C:\Program Files\Windows Kits\10\Debuggers\$arch\kd.exe",
                "C:\Program Files\Debugging Tools for Windows (x64)\kd.exe"
            )
            foreach ($p in $kdFallbacks) {
                if (Test-Path $p) { $kdPath = $p; break }
            }
        }

        # 3. WinDbg Store app
        if (-not $kdPath) {
            $pkg = Get-AppxPackage -Name "Microsoft.WinDbg" -ErrorAction SilentlyContinue
            if ($pkg) {
                $candidate = Join-Path $pkg.InstallLocation "kd.exe"
                if (Test-Path $candidate) { $kdPath = $candidate }
            }
        }

        # 4. PATH (last resort)
        if (-not $kdPath) {
            $kdCmd = Get-Command kd.exe -ErrorAction SilentlyContinue
            if ($kdCmd) { $kdPath = $kdCmd.Source }
        }

        if ($kdPath) {
            $dumpAnalysis.kd_available = $true
            $dumpAnalysis.performed = $true

            $kdOutput = & $kdPath -z $targetDump -c ".bugcheck; !analyze -v; k; q" -y $SymbolPath 2>&1
            $kdText = $kdOutput | Out-String

            $dumpAnalysis.raw_output = $kdText

            # Extract key fields
            $bugcheckMatch = [regex]::Match($kdText, "Bugcheck code ([0-9A-Fa-f]+)")
            $bucketMatch = [regex]::Match($kdText, "FAILURE_BUCKET_ID:\s+(.+)")
            $moduleMatch = [regex]::Match($kdText, "MODULE_NAME:\s+(.+)")
            $imageMatch = [regex]::Match($kdText, "IMAGE_NAME:\s+(.+)")
            $processMatch = [regex]::Match($kdText, "PROCESS_NAME:\s+(.+)")
            $symbolMatch = [regex]::Match($kdText, "SYMBOL_NAME:\s+(.+)")

            if ($bugcheckMatch.Success) { $dumpAnalysis.bugcheck_code = "0x$($bugcheckMatch.Groups[1].Value)" }
            if ($moduleMatch.Success)   { $dumpAnalysis.module = $moduleMatch.Groups[1].Value.Trim() }
            if ($imageMatch.Success)    { $dumpAnalysis.image = $imageMatch.Groups[1].Value.Trim() }
            if ($symbolMatch.Success)   { $dumpAnalysis.symbol = $symbolMatch.Groups[1].Value.Trim() }
            if ($processMatch.Success)  { $dumpAnalysis.process = $processMatch.Groups[1].Value.Trim() }
            if ($bucketMatch.Success)   { $dumpAnalysis.bucket = $bucketMatch.Groups[1].Value.Trim() }
        }
    }
}

# ===================================================================
# OUTPUT
# ===================================================================

$result = @{
    system = $systemInfo
    rdp = $rdpInfo
    evidence = $evidence
    verdict = $verdict
    events = $events
    dumps = $dumpInfo
    dump_analysis = $dumpAnalysis
    previous_boot = $previousBoot
}

$json = $result | ConvertTo-Json -Depth 5 -Compress:$JsonOnly

if ($JsonOnly) {
    Write-Output $json
} else {
    # Human-readable output + JSON at end
    Write-Host "============================================"
    Write-Host "  WTF-RESTARTED -- Crash Investigator"
    Write-Host "============================================"
    Write-Host "Time:       $($systemInfo.current_time)"
    Write-Host "Lookback:   $LookbackHours hours"
    Write-Host "Boot time:  $($systemInfo.boot_time)"
    Write-Host "Uptime:     $($systemInfo.uptime_display)"
    Write-Host ""

    if ($rdpInfo.is_rdp -and $rdpInfo.warning) {
        Write-Host "*** RDP WARNING ***" -ForegroundColor Yellow
        Write-Host $rdpInfo.warning -ForegroundColor Yellow
        Write-Host ""
    }

    Write-Host "============================================"
    Write-Host "  VERDICT: $($verdict.type)"
    Write-Host "============================================"
    Write-Host "  $($verdict.summary)"
    foreach ($d in $verdict.details) {
        Write-Host "  - $d"
    }
    Write-Host ""

    if ($events.kernel_power_41.Count -gt 0) {
        Write-Host "--- Kernel-Power Event 41 (Unexpected Shutdown) ---"
        foreach ($e in $events.kernel_power_41) { Write-Host "  [$($e.time)] $($e.message)" }
        Write-Host ""
    }
    if ($events.event_6008.Count -gt 0) {
        Write-Host "--- Event 6008 (Previous Shutdown Was Unexpected) ---"
        foreach ($e in $events.event_6008) { Write-Host "  [$($e.time)] $($e.message)" }
        Write-Host ""
    }
    if ($events.shutdown_initiator.Count -gt 0) {
        Write-Host "--- Shutdown Initiator ---"
        foreach ($e in $events.shutdown_initiator) { Write-Host "  [$($e.time)] ID=$($e.id) $($e.message)" }
        Write-Host ""
    }
    if ($events.bugcheck.Count -gt 0) {
        Write-Host "--- BugCheck / BSOD Events ---"
        foreach ($e in $events.bugcheck) { Write-Host "  [$($e.time)] $($e.message)" }
        Write-Host ""
    }
    if ($events.gpu_events.Count -gt 0) {
        Write-Host "--- GPU Driver Events (TDR/Display Recovery) ---"
        foreach ($e in $events.gpu_events) { Write-Host "  [$($e.time)] $($e.message)" }
        Write-Host ""
    }
    if ($events.context_window.Count -gt 0) {
        Write-Host ('--- Surrounding Events (' + $ContextMinutes + ' min before reboot) ---')
        foreach ($e in $events.context_window | Select-Object -First 15) { Write-Host "  [$($e.time)] [$($e.provider)] $($e.message)" }
        Write-Host ""
    }

    if ($dumpAnalysis.performed) {
        Write-Host "--- Crash Dump Analysis ---"
        if ($dumpAnalysis.bugcheck_code) { Write-Host "  Bugcheck: $($dumpAnalysis.bugcheck_code)" }
        if ($dumpAnalysis.module)        { Write-Host "  Module:   $($dumpAnalysis.module)" }
        if ($dumpAnalysis.image)         { Write-Host "  Image:    $($dumpAnalysis.image)" }
        if ($dumpAnalysis.symbol)        { Write-Host "  Symbol:   $($dumpAnalysis.symbol)" }
        if ($dumpAnalysis.process)       { Write-Host "  Process:  $($dumpAnalysis.process)" }
        if ($dumpAnalysis.bucket)        { Write-Host "  Bucket:   $($dumpAnalysis.bucket)" }
    }

    Write-Host ""
    Write-Host "--- JSON OUTPUT ---"
    Write-Output $json
}
