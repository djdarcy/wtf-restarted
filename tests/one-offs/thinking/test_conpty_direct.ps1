# Direct ConPTY test - does Windows Pseudo Console work at all?
# If this works, ConPTY is fine and the bug is in ttyd's usage.
# If this fails, ConPTY itself is broken on this Windows build.

Write-Host "=== ConPTY Direct Test ==="
Write-Host "Windows Version: $([System.Environment]::OSVersion.VersionString)"

# Test 1: Check if ConPTY API is available
Write-Host "`n--- Test 1: ConPTY API availability ---"
try {
    $signature = @"
[DllImport("kernel32.dll", SetLastError = true)]
public static extern int CreatePseudoConsole(
    long size, IntPtr hInput, IntPtr hOutput, uint dwFlags, out IntPtr phPC);
"@
    $type = Add-Type -MemberDefinition $signature -Name "ConPTY" -Namespace "Win32" -PassThru -ErrorAction Stop
    Write-Host "ConPTY API: AVAILABLE"
} catch {
    Write-Host "ConPTY API: NOT AVAILABLE - $_"
}

# Test 2: Does VS Code terminal work? (uses ConPTY)
Write-Host "`n--- Test 2: Known ConPTY users ---"
$conhostProcs = Get-Process conhost -ErrorAction SilentlyContinue
Write-Host "conhost.exe instances: $($conhostProcs.Count)"
$wtProcs = Get-Process WindowsTerminal -ErrorAction SilentlyContinue
Write-Host "WindowsTerminal.exe instances: $($wtProcs.Count)"

# Test 3: Try spawning a process through ConPTY-like mechanism
Write-Host "`n--- Test 3: Process spawn with redirected I/O ---"
try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = "/c echo CONPTY_TEST_OK"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    $output = $proc.StandardOutput.ReadToEnd()
    $proc.WaitForExit(5000)

    if ($output -match "CONPTY_TEST_OK") {
        Write-Host "Process spawn + pipe: OK ($($output.Trim()))"
    } else {
        Write-Host "Process spawn + pipe: UNEXPECTED OUTPUT: $output"
    }
} catch {
    Write-Host "Process spawn + pipe: FAILED - $_"
}

# Test 4: Check if ttyd's bundled winpty/conpty works
Write-Host "`n--- Test 4: ttyd process tree when running ---"
Write-Host "(Start ttyd manually and re-run this test to see its process tree)"

Write-Host "`n=== Done ==="
