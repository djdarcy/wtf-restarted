/*
 * test_conpty_standalone.c -- Minimal ConPTY test replicating ttyd's pty.c pathway
 *
 * Tests each Win32 API call that ttyd makes to create a pseudo-console:
 *   1. CreateNamedPipeA (in + out)
 *   2. CreatePseudoConsole
 *   3. InitializeProcThreadAttributeList + UpdateProcThreadAttribute
 *   4. CreateProcessW with EXTENDED_STARTUPINFO_PRESENT
 *   5. Read data from the output pipe
 *
 * Compile with MSVC:  cl.exe test_conpty_standalone.c /Fe:test_conpty.exe
 * Compile with MinGW: x86_64-w64-mingw32-gcc test_conpty_standalone.c -o test_conpty_mingw.exe
 */

#include <windows.h>
#include <stdio.h>
#include <string.h>

#ifndef PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE
#define PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE 0x00020016
#endif

typedef VOID* HPCON;
typedef HRESULT (WINAPI *FnCreatePseudoConsole)(COORD, HANDLE, HANDLE, DWORD, HPCON*);
typedef void (WINAPI *FnClosePseudoConsole)(HPCON);

static void print_last_error(const char *func) {
    DWORD err = GetLastError();
    char buf[512];
    FormatMessageA(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                   NULL, err, 0, buf, sizeof(buf), NULL);
    printf("  FAIL: %s -> error %lu: %s", func, err, buf);
}

int main(void) {
    printf("=== ConPTY Standalone Test (replicating ttyd pty.c) ===\n\n");

    /* ---- Step 0: Load ConPTY functions dynamically (same as ttyd) ---- */
    printf("[Step 0] Loading ConPTY functions from kernel32.dll...\n");
    HMODULE kernel = LoadLibraryA("kernel32.dll");
    if (!kernel) { print_last_error("LoadLibrary"); return 1; }

    FnCreatePseudoConsole pCreatePC = (FnCreatePseudoConsole)GetProcAddress(kernel, "CreatePseudoConsole");
    FnClosePseudoConsole pClosePC = (FnClosePseudoConsole)GetProcAddress(kernel, "ClosePseudoConsole");
    if (!pCreatePC || !pClosePC) {
        printf("  FAIL: ConPTY functions not found (need Win10 1809+)\n");
        return 1;
    }
    printf("  OK: CreatePseudoConsole @ %p, ClosePseudoConsole @ %p\n", pCreatePC, pClosePC);

    /* ---- Step 1: Create named pipes (EXACTLY as ttyd does) ---- */
    printf("\n[Step 1] Creating named pipes...\n");
    DWORD pid = GetCurrentProcessId();
    char in_name[256], out_name[256];
    snprintf(in_name, sizeof(in_name), "\\\\.\\pipe\\ttyd-test-in-%lu-0", pid);
    snprintf(out_name, sizeof(out_name), "\\\\.\\pipe\\ttyd-test-out-%lu-0", pid);

    /* BUG REPLICATION: ttyd uses sa = {0} without setting nLength */
    SECURITY_ATTRIBUTES sa_bug = {0};  /* nLength = 0 (ttyd's code) */
    const DWORD open_mode = PIPE_ACCESS_INBOUND | PIPE_ACCESS_OUTBOUND | FILE_FLAG_FIRST_PIPE_INSTANCE;
    const DWORD pipe_mode = PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT;

    printf("  Creating pipes WITH sa.nLength = 0 (ttyd's code)...\n");
    HANDLE in_pipe_bug = CreateNamedPipeA(in_name, open_mode, pipe_mode, 1, 0, 0, 30000, &sa_bug);
    HANDLE out_pipe_bug = CreateNamedPipeA(out_name, open_mode, pipe_mode, 1, 0, 0, 30000, &sa_bug);

    if (in_pipe_bug == INVALID_HANDLE_VALUE || out_pipe_bug == INVALID_HANDLE_VALUE) {
        print_last_error("CreateNamedPipeA (sa.nLength=0)");
        printf("  >>> sa.nLength=0 IS the bug!\n");
    } else {
        printf("  OK: Both pipes created with sa.nLength=0\n");
        CloseHandle(in_pipe_bug);
        CloseHandle(out_pipe_bug);
    }

    /* Now try with correct sa.nLength */
    SECURITY_ATTRIBUTES sa_fix = {0};
    sa_fix.nLength = sizeof(SECURITY_ATTRIBUTES);

    /* Use different pipe names to avoid collision */
    snprintf(in_name, sizeof(in_name), "\\\\.\\pipe\\ttyd-test-in-%lu-1", pid);
    snprintf(out_name, sizeof(out_name), "\\\\.\\pipe\\ttyd-test-out-%lu-1", pid);

    printf("  Creating pipes WITH sa.nLength = %u (correct)...\n", (unsigned)sizeof(SECURITY_ATTRIBUTES));
    HANDLE in_pipe = CreateNamedPipeA(in_name, open_mode, pipe_mode, 1, 0, 0, 30000, &sa_fix);
    HANDLE out_pipe = CreateNamedPipeA(out_name, open_mode, pipe_mode, 1, 0, 0, 30000, &sa_fix);

    if (in_pipe == INVALID_HANDLE_VALUE || out_pipe == INVALID_HANDLE_VALUE) {
        print_last_error("CreateNamedPipeA (sa.nLength=correct)");
        return 1;
    }
    printf("  OK: in_pipe=%p, out_pipe=%p\n", in_pipe, out_pipe);

    /* ---- Step 2: CreatePseudoConsole ---- */
    printf("\n[Step 2] Creating pseudo console...\n");
    COORD size = {80, 24};
    HPCON hpc = NULL;
    HRESULT hr = pCreatePC(size, in_pipe, out_pipe, 0, &hpc);
    printf("  HRESULT = 0x%08lX\n", hr);
    if (FAILED(hr)) {
        printf("  FAIL: CreatePseudoConsole failed!\n");
        /* Try with the buggy sa pipes too */
        CloseHandle(in_pipe);
        CloseHandle(out_pipe);
        return 1;
    }
    printf("  OK: pseudo console handle = %p\n", hpc);

    /* Close pipe handles after ConPTY takes ownership (same as ttyd) */
    CloseHandle(in_pipe);
    CloseHandle(out_pipe);

    /* ---- Step 3: Set up STARTUPINFOEXW with pseudo console attribute ---- */
    printf("\n[Step 3] Setting up STARTUPINFOEXW...\n");
    STARTUPINFOEXW si = {0};
    si.StartupInfo.cb = sizeof(STARTUPINFOEXW);

    SIZE_T attr_size = 0;
    InitializeProcThreadAttributeList(NULL, 1, 0, &attr_size);
    printf("  Attribute list size: %llu bytes\n", (unsigned long long)attr_size);

    si.lpAttributeList = (PPROC_THREAD_ATTRIBUTE_LIST)malloc(attr_size);
    if (!InitializeProcThreadAttributeList(si.lpAttributeList, 1, 0, &attr_size)) {
        print_last_error("InitializeProcThreadAttributeList");
        return 1;
    }
    printf("  OK: Attribute list initialized\n");

    if (!UpdateProcThreadAttribute(si.lpAttributeList, 0,
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE, hpc, sizeof(HPCON), NULL, NULL)) {
        print_last_error("UpdateProcThreadAttribute");
        return 1;
    }
    printf("  OK: Pseudo console attribute set\n");

    /* ---- Step 4: CreateProcessW ---- */
    printf("\n[Step 4] Creating process (cmd.exe /c echo CONPTY_OK)...\n");
    PROCESS_INFORMATION pi = {0};
    WCHAR cmdline[] = L"cmd.exe /c echo CONPTY_OK && timeout /t 2 /nobreak >nul";
    DWORD flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT;

    if (!CreateProcessW(NULL, cmdline, NULL, NULL, FALSE, flags, NULL, NULL,
            &si.StartupInfo, &pi)) {
        print_last_error("CreateProcessW");
        return 1;
    }
    printf("  OK: Process created, PID = %lu\n", pi.dwProcessId);

    /* ---- Step 5: Read output via named pipe ---- */
    printf("\n[Step 5] Reading output from pseudo console...\n");

    /* Connect to the output pipe as a client (same as ttyd's uv_pipe_connect) */
    snprintf(out_name, sizeof(out_name), "\\\\.\\pipe\\ttyd-test-out-%lu-1", pid);
    HANDLE out_client = CreateFileA(out_name, GENERIC_READ, 0, NULL,
                                     OPEN_EXISTING, 0, NULL);
    if (out_client == INVALID_HANDLE_VALUE) {
        print_last_error("CreateFile (connect to output pipe)");
        /* This is expected -- the pipe server was closed. Try the input pipe name */
        printf("  Note: Pipe server handles were closed, client connect expected to fail.\n");
        printf("  This is likely how ttyd fails too -- pipe handles closed before client connects.\n");
    } else {
        char buf[4096];
        DWORD bytesRead = 0;
        /* Try to read with a timeout */
        if (ReadFile(out_client, buf, sizeof(buf) - 1, &bytesRead, NULL)) {
            buf[bytesRead] = '\0';
            printf("  SUCCESS: Read %lu bytes: [%s]\n", bytesRead, buf);
        } else {
            print_last_error("ReadFile");
        }
        CloseHandle(out_client);
    }

    /* ---- Cleanup ---- */
    printf("\n[Cleanup]\n");
    WaitForSingleObject(pi.hProcess, 3000);
    DWORD exitCode = 0;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    printf("  Process exit code: %lu\n", exitCode);

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    DeleteProcThreadAttributeList(si.lpAttributeList);
    free(si.lpAttributeList);
    pClosePC(hpc);

    printf("\n=== Test Complete ===\n");
    return 0;
}
