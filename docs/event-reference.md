# Windows Event ID Reference

This document catalogs every event ID that wtf-restarted monitors, what each one means, where to find it manually, and links to Microsoft's documentation. It's intended both as a reference for users who want to understand the tool's output and as a guide for contributors who want to add new event checks.

## Quick Reference

| Event ID | Provider | Log | Category | What It Means |
|----------|----------|-----|----------|---------------|
| 41 | Microsoft-Windows-Kernel-Power | System | Dirty shutdown | Unexpected power loss or hard reset |
| 109 | Microsoft-Windows-Kernel-Power | System | Power transition | Sleep/wake/hibernate state change |
| 1001 | Windows Error Reporting | System or Application | BugCheck / BSOD | Blue screen crash report |
| 1074 | User32 | System | Shutdown initiator | A process requested shutdown/restart |
| 1076 | User32 | System | Shutdown initiator | Reason code for unexpected shutdown |
| 4097 | Display | System | GPU | Display driver recovered from timeout |
| 4101 | Display | System | GPU | Display driver TDR (Timeout Detection and Recovery) |
| 6005 | EventLog | System | Boot sequence | Event Log service started (system boot) |
| 6006 | EventLog | System | Boot sequence | Event Log service stopped (clean shutdown) |
| 6008 | EventLog | System | Boot sequence | Previous shutdown was unexpected |
| 6009 | EventLog | System | Boot sequence | OS version info logged at boot |
| 19 | Microsoft-Windows-WindowsUpdateClient | System | Windows Update | Update installed successfully |
| 20 | Microsoft-Windows-WindowsUpdateClient | System | Windows Update | Update install failed |
| -- | Microsoft-Windows-WHEA-Logger | System | Hardware | Hardware error (CPU, memory, PCIe, etc.) |
| -- | Application Error | Application | App crash | Application crash near reboot time |
| -- | nvlddmkm | System | GPU | NVIDIA display driver kernel event |

---

## Detailed Event Descriptions

### Kernel-Power Events

#### Event 41 -- Unexpected Shutdown (Kernel-Power)

- **Log**: System
- **Provider**: `Microsoft-Windows-Kernel-Power`
- **Level**: Critical
- **What it means**: The system rebooted without cleanly shutting down first. This is the primary "dirty shutdown" indicator. Common causes: power loss, hardware reset button, BSOD, system hang.
- **How wtf-restarted uses it**: Sets `evidence.dirty_shutdown = true`. If combined with crash dump evidence, the verdict is `BSOD`. Without a crash dump or initiator, the verdict is `UNEXPECTED_SHUTDOWN`.
- **BugCheck reason codes** (in event data):
  - `0` = Unknown / couldn't be determined
  - `1` = Blue screen (BugCheck)
  - `2` = Power button pressed
  - `4` = Hibernate failure
  - `5` = Kernel panic / fatal error

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Source: Microsoft-Windows-Kernel-Power, Event ID: 41
```

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=41} -MaxEvents 5
```

**Microsoft docs**: [Kernel-Power Event 41](https://learn.microsoft.com/en-us/windows/client-management/troubleshoot-event-id-41-restart)

---

#### Event 109 -- Power State Transition (Kernel-Power)

- **Log**: System
- **Provider**: `Microsoft-Windows-Kernel-Power`
- **Level**: Informational
- **What it means**: Records power state transitions -- sleep, wake, hibernate, resume. Useful for understanding whether a "restart" was actually a failed resume from sleep/hibernate.
- **How wtf-restarted uses it**: Collected for context but doesn't directly affect the verdict. Shown in verbose mode.

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Source: Microsoft-Windows-Kernel-Power, Event ID: 109
```

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=109} -MaxEvents 5
```

---

### Shutdown / Boot Sequence Events (EventLog)

These events come from the Event Log service itself and mark the lifecycle of the system.

#### Event 6005 -- Event Log Service Started (Boot)

- **Log**: System
- **Provider**: `EventLog`
- **Level**: Informational
- **What it means**: The Event Log service started, which means the system just booted. Every boot produces a 6005 entry. By counting 6005 entries over time, you can build a restart timeline.
- **How wtf-restarted uses it**: Used in `history` command to enumerate boots, and in the `boot_sequence` evidence to show the boot/shutdown pattern. Also used to calculate previous uptime (gap between consecutive 6005 events).
- **Label in output**: `START`

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6005} -MaxEvents 10
```

---

#### Event 6006 -- Event Log Service Stopped (Clean Shutdown)

- **Log**: System
- **Provider**: `EventLog`
- **Level**: Informational
- **What it means**: The Event Log service stopped cleanly, meaning the system performed a proper shutdown. A 6006 followed by a 6005 = clean restart cycle. A 6005 *without* a preceding 6006 = something went wrong (dirty shutdown).
- **How wtf-restarted uses it**: Used in `boot_sequence` to confirm clean shutdown patterns.
- **Label in output**: `CLEAN_STOP`

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6006} -MaxEvents 10
```

---

#### Event 6008 -- Previous Shutdown Was Unexpected

- **Log**: System
- **Provider**: `EventLog`
- **Level**: Error
- **What it means**: Logged at boot when the previous shutdown was not clean. The event message typically includes the date and time of the unexpected shutdown. Often appears alongside Event 41.
- **How wtf-restarted uses it**: Sets `evidence.dirty_shutdown = true` (same as Event 41). Redundant confirmation -- if either 41 or 6008 appears, the tool knows the shutdown was dirty.
- **Label in output**: `DIRTY_SHUTDOWN`

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6008} -MaxEvents 5
```

---

#### Event 6009 -- OS Version at Boot

- **Log**: System
- **Provider**: `EventLog`
- **Level**: Informational
- **What it means**: Logged at boot with the OS version, build number, and processor info. Useful for correlating with updates ("did the build number change after this restart?").
- **How wtf-restarted uses it**: Included in `boot_sequence` for context.
- **Label in output**: `OS_VERSION`

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6009} -MaxEvents 5
```

---

### Shutdown Initiator Events (User32)

#### Event 1074 -- Process Initiated Restart/Shutdown

- **Log**: System
- **Provider**: `User32`
- **Level**: Informational
- **What it means**: A process called `InitiateSystemShutdownEx()` or `ExitWindowsEx()` to request a restart or shutdown. The event message includes the process name, the user account, and the reason string.
- **Common initiators**:
  - `C:\Windows\system32\svchost.exe` -- usually Windows Update (TrustedInstaller service)
  - `C:\Windows\System32\usoclient.exe` -- Update Session Orchestrator
  - `C:\Windows\explorer.exe` -- user clicked Start > Restart
  - `C:\Windows\System32\shutdown.exe` -- `shutdown /r` command
- **How wtf-restarted uses it**: Sets `evidence.initiated_by` to the event message. If present without a dirty shutdown, the verdict is `INITIATED_RESTART`. If Windows Update events are also nearby, the summary says "Windows Update triggered the restart."

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Event ID: 1074
```

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; Id=1074} -MaxEvents 5 | Format-List TimeCreated, Message
```

---

#### Event 1076 -- Unexpected Shutdown Reason

- **Log**: System
- **Provider**: `User32`
- **Level**: Informational
- **What it means**: Logged when a user provides a reason for an unexpected shutdown (via the "Shutdown Event Tracker" dialog that appears on servers or when Group Policy enables it). Less common on desktop Windows.
- **How wtf-restarted uses it**: Treated the same as Event 1074 for evidence collection.

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; Id=1076} -MaxEvents 5
```

---

### BugCheck / BSOD Events

#### Event 1001 -- Windows Error Reporting (BugCheck)

- **Log**: System and Application
- **Provider**: `Windows Error Reporting` (Application log) or generic (System log)
- **Level**: Informational
- **What it means**: Windows Error Reporting logs a summary of a BugCheck (BSOD). The message contains the bugcheck code, parameter values, and sometimes the faulting module. wtf-restarted filters for events where the message matches `BugCheck`, `BlueScreen`, or `LiveKernelEvent`.
- **How wtf-restarted uses it**: Sets `evidence.bugcheck = true`. Combined with dirty shutdown evidence, produces a `BSOD` verdict.
- **Note**: Event ID 1001 is shared by many WER reports (not just BSODs). The tool filters by message content to avoid false positives.

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Event ID: 1001
(then look for entries mentioning BugCheck in the message)
```

**PowerShell**:
```powershell
# System log
Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001} -MaxEvents 20 |
    Where-Object { $_.Message -match "BugCheck|BlueScreen" }

# Application log (Windows Error Reporting provider)
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Windows Error Reporting'} -MaxEvents 20 |
    Where-Object { $_.Message -match "BugCheck|BlueScreen|LiveKernelEvent" }
```

---

### WHEA Hardware Errors

#### WHEA-Logger Events (various IDs)

- **Log**: System
- **Provider**: `Microsoft-Windows-WHEA-Logger`
- **Level**: Error or Warning
- **What it means**: WHEA (Windows Hardware Error Architecture) logs hardware faults detected by the CPU, memory controller, PCIe bus, or other hardware. Common causes: overheating, unstable overclock, failing RAM, degraded SSD.
- **Common event IDs**:
  - **17** -- Fatal hardware error (machine check exception)
  - **18** -- Corrected hardware error
  - **19** -- Corrected machine check
  - **47** -- Corrected PCIe error
- **How wtf-restarted uses it**: Sets `evidence.whea_error = true`. If combined with an unexpected shutdown, adds "WHEA hardware error detected -- possible hardware fault" to the verdict details.

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Source: Microsoft-Windows-WHEA-Logger
```

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WHEA-Logger'} -MaxEvents 10
```

**Microsoft docs**: [WHEA Hardware Error Events](https://learn.microsoft.com/en-us/windows-hardware/drivers/whea/)

---

### Windows Update Events

#### Event 19 -- Update Installed Successfully

- **Log**: System
- **Provider**: `Microsoft-Windows-WindowsUpdateClient`
- **Level**: Informational
- **What it means**: A Windows Update was successfully installed. The message includes the KB number and update title.
- **How wtf-restarted uses it**: If a successful install occurred within 30 minutes before the last boot, sets `evidence.windows_update = true` and flags the event with `near_crash = true`.

#### Event 20 -- Update Installation Failed

- **Log**: System
- **Provider**: `Microsoft-Windows-WindowsUpdateClient`
- **Level**: Error
- **What it means**: A Windows Update failed to install. Relevant because failed updates sometimes trigger reboots (the update partially applies, fails, and Windows rolls back on restart).
- **How wtf-restarted uses it**: Same proximity check as Event 19.

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Source: Microsoft-Windows-WindowsUpdateClient
```

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WindowsUpdateClient'} -MaxEvents 20
```

**Microsoft docs**: [Windows Update log files](https://learn.microsoft.com/en-us/windows/deployment/update/windows-update-logs)

---

### GPU Driver Events

#### Event 4101 -- Display Driver TDR (Timeout Detection and Recovery)

- **Log**: System
- **Provider**: `Display`
- **Level**: Warning
- **What it means**: The display driver stopped responding and was recovered. TDR is Windows' mechanism for resetting a hung GPU driver without crashing the system. If recovery fails, the system may BSOD (typically with bugcheck `VIDEO_TDR_FAILURE` / `0x116`).
- **How wtf-restarted uses it**: Collected as GPU evidence. Multiple TDR events near a restart suggest GPU instability as the root cause.

#### Event 4097 -- Display Driver Recovered

- **Log**: System
- **Provider**: `Display`
- **Level**: Warning
- **What it means**: Similar to 4101 -- the display driver was reset and recovered. Often logged alongside 4101.

#### nvlddmkm Events

- **Log**: System
- **Provider**: `nvlddmkm`
- **What it means**: Events from NVIDIA's kernel-mode display driver. These indicate NVIDIA-specific driver issues -- crashes, recoveries, or internal errors. The provider name `nvlddmkm` stands for "NVIDIA Local Display Driver (Kernel Mode)."

**Manual lookup**:
```
Event Viewer > Windows Logs > System > Filter by Event ID: 4101, 4097
(or filter by Source: nvlddmkm for NVIDIA-specific events)
```

**PowerShell**:
```powershell
# General GPU TDR events
Get-WinEvent -FilterHashtable @{LogName='System'; Id=@(4101,4097)} -MaxEvents 10

# NVIDIA-specific events
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='nvlddmkm'} -MaxEvents 10
```

**Microsoft docs**: [TDR (Timeout Detection and Recovery)](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery)

---

### Application Crashes

#### Application Error Events

- **Log**: Application
- **Provider**: `Application Error`
- **Level**: Error
- **What it means**: An application crashed (unhandled exception, access violation, etc.). The message includes the faulting process name, module, and exception code.
- **How wtf-restarted uses it**: Collects application crashes from the hour before the last boot. These don't affect the verdict directly but provide context -- if the same process crashed repeatedly before a restart, it might be related.

**Manual lookup**:
```
Event Viewer > Windows Logs > Application > Filter by Source: Application Error
```

**PowerShell**:
```powershell
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'} -MaxEvents 10
```

---

## Other Data Sources (Not Event Log)

### Crash Dump Files

wtf-restarted also checks for crash dump files on disk:

| Path | Type | What It Contains |
|------|------|-----------------|
| `C:\Windows\MEMORY.DMP` | Full/kernel memory dump | Complete system state at time of BSOD |
| `C:\Windows\Minidump\*.dmp` | Minidump | Condensed crash data (bugcheck code, stack trace, loaded modules) |

These aren't event log entries -- they're binary files written by the kernel during a BSOD. The tool checks whether they exist and whether they're recent (within the lookback window).

If `kd.exe` is available, the tool can analyze these dumps to extract the bugcheck code, faulting module, and failure bucket. See [parameters.md](parameters.md#-dumpfile----targeting-a-specific-crash-dump) for details.

**Manual access**:
```
Windows Settings > System > About > Advanced system settings >
  Startup and Recovery > Settings
  (shows dump file location and type)
```

Or check directly:
```powershell
# Full dump
Get-Item "C:\Windows\MEMORY.DMP" -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime

# Minidumps
Get-ChildItem "C:\Windows\Minidump" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
```

### RDP Session Detection

- **Source**: `$env:SESSIONNAME` environment variable, `query session` command
- **What it detects**: Whether the user is connected via Remote Desktop (session name starts with `RDP-`) and whether there are disconnected sessions with potentially open windows.
- **Why it matters**: Users connected via RDP sometimes think their machine restarted when in reality they just got a new session. Disconnected sessions may still have windows open on a different session ID.

**Manual check**:
```powershell
# Current session type
echo $env:SESSIONNAME    # "Console" = local, "RDP-Tcp#N" = remote

# All sessions
query session
```

### CIM / WMI System Info

- **Source**: `Get-CimInstance Win32_OperatingSystem`
- **What it provides**: `LastBootUpTime` (when the system last booted), OS version string
- **Used for**: Calculating uptime, establishing the boot time that all event lookups are relative to

**Manual check**:
```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object LastBootUpTime, Caption, Version, BuildNumber
```

---

## Viewing Events in Event Viewer (GUI)

For users who prefer the graphical interface:

1. Press **Win + R**, type `eventvwr.msc`, press Enter
2. In the left pane, expand **Windows Logs**
3. Click **System** (for most events) or **Application** (for WER and app crashes)
4. In the right pane, click **Filter Current Log...**
5. Enter event IDs (comma-separated) in the "Event IDs" field, e.g.: `41, 1074, 6005, 6006, 6008`
6. Optionally filter by Source (provider name)

You can also use **Custom Views** to save frequently used filters:
```
Event Viewer > Custom Views > right-click > Create Custom View
```

### Reliability Monitor

A friendlier view of system stability:

1. Press **Win + R**, type `perfmon /rel`, press Enter
2. Shows a timeline of application failures, Windows failures, and informational events
3. Click any day to see details

This is essentially the same data wtf-restarted reads, but presented as a visual timeline rather than raw events.

---

## Adding New Event Checks

If you want to add monitoring for additional events, here's the pattern used in `investigate.ps1`:

```powershell
# 1. Query the event log with a filter
$newEvents = Get-WinEvent -FilterHashtable @{
    LogName = 'System'           # or 'Application', 'Security', etc.
    ProviderName = 'ProviderName' # optional: filter by source
    Id = @(1234, 5678)           # event ID(s) to match
    StartTime = $lookback        # only events within lookback window
} -ErrorAction SilentlyContinue

# 2. Store results
$events.new_category = @()
if ($newEvents) {
    # 3. Optionally set evidence flags
    $evidence.new_flag = $true

    # 4. Format each event for JSON output
    foreach ($e in $newEvents | Select-Object -First 10) {
        $events.new_category += Format-Event $e 300
    }
}
```

### Finding event IDs to monitor

To discover what events are being generated on your system:

```powershell
# Recent errors/warnings in System log (last 24 hours)
Get-WinEvent -FilterHashtable @{LogName='System'; Level=@(1,2,3); StartTime=(Get-Date).AddHours(-24)} |
    Group-Object Id, ProviderName | Sort-Object Count -Descending | Select-Object Count, Name -First 20

# Same for Application log
Get-WinEvent -FilterHashtable @{LogName='Application'; Level=@(1,2,3); StartTime=(Get-Date).AddHours(-24)} |
    Group-Object Id, ProviderName | Sort-Object Count -Descending | Select-Object Count, Name -First 20

# List all providers (sources) that have logged events
Get-WinEvent -ListProvider * | Select-Object Name | Sort-Object Name
```

### Candidate events for future versions

Events that wtf-restarted doesn't currently monitor but could be useful:

| Event ID | Provider | Log | What It Tracks |
|----------|----------|-----|---------------|
| 7031 | Service Control Manager | System | A service terminated unexpectedly |
| 7034 | Service Control Manager | System | A service terminated unexpectedly (count) |
| 7045 | Service Control Manager | System | A new service was installed |
| 10016 | DCOM | System | DCOM permission errors (often noisy) |
| 1 | Microsoft-Windows-Sysmon | Microsoft-Windows-Sysmon/Operational | Process creation (if Sysmon installed) |
| 4624/4625 | Security | Security | Logon success/failure (needs admin) |
| 55 | Ntfs | System | File system corruption detected |
| 7 | Disk | System | Bad block detected on disk |
| 11 | Disk | System | Disk controller error |
| 153 | Disk | System | Disk I/O retry (possible failing disk) |
| 129 | storahci | System | Storage adapter reset |
