# Prepare/build only on an explicitly authorized Windows machine.
# Never installs Python, Inno Setup, or the resulting application.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(Mandatory=$true)][string]$IsccExe,
    [switch]$InstallBuildDependencies,
    [string]$ExtraNoticesDirectory = ""
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "A Windows build host is required; no cross-compilation." }
$Root = $PSScriptRoot
$PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
$IsccExe = (Resolve-Path -LiteralPath $IsccExe).Path
$Info = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($IsccExe)
if ($Info.FileMajorPart -ne 7 -or $Info.FileMinorPart -ne 1 -or $Info.FileBuildPart -ne 0) {
    throw "Pinned installer compiler required: Inno Setup 7.1.0. No tools will be installed automatically."
}
function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE : $Executable" }
}
Push-Location $Root
try {
    Invoke-Checked $PythonExe @('-c', 'import sys,struct,platform,sysconfig; assert sys.version_info[:3]==(3,13,17) and struct.calcsize("P")==8 and platform.machine().lower() in ("amd64","x86_64") and not sysconfig.get_config_var("Py_GIL_DISABLED"), "Use standard CPython 3.13.17 x64"')
    $Venv = Join-Path $Root '.venv-build'
    $VenvPython = Join-Path $Venv 'Scripts\python.exe'
    if ($InstallBuildDependencies) {
        # Run this branch only after approval for these exact build dependency installs.
        if (-not (Test-Path -LiteralPath $VenvPython)) {
            Invoke-Checked $PythonExe @('-m','venv',$Venv)
        }
        Invoke-Checked $VenvPython @('-c','import pip; assert pip.__version__=="26.2.2", "Use pip 26.2.2 from the pinned Python; update tooling only after approval"')
        Invoke-Checked $VenvPython @('-m','pip','install','--only-binary=:all:','-r','requirements-build.txt')
    }
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        throw 'Build venv is absent. Approval is required before using -InstallBuildDependencies.'
    }
    New-Item -ItemType Directory -Path '.build','release' -Force | Out-Null
    # Includes the historical pip pin on both new and reused build-venv paths.
    & $VenvPython 'tools\verify_build_environment.py' | Set-Content -Encoding UTF8 '.build\environment.json'
    if ($LASTEXITCODE -ne 0) { throw 'Build environment verification failed.' }
    Invoke-Checked $VenvPython @('-m','pip','check')
    & $VenvPython -m pip freeze --all | Set-Content -Encoding UTF8 '.build\resolved-requirements.txt'
    if ($LASTEXITCODE -ne 0) { throw 'Dependency inventory failed.' }
    Invoke-Checked $VenvPython @('tools\run_tests.py','--out','.build\tests.json','--require-native')
    if (Test-Path -LiteralPath '.build\notices') { Remove-Item -LiteralPath '.build\notices' -Recurse }
    $NoticeArgs = @('tools\collect_notices.py','--out','.build\notices')
    if ($ExtraNoticesDirectory) { $NoticeArgs += @('--extra',(Resolve-Path -LiteralPath $ExtraNoticesDirectory).Path) }
    Invoke-Checked $VenvPython $NoticeArgs
    Invoke-Checked $VenvPython @('-m','PyInstaller','--clean','--noconfirm','packaging\CrystallographicOrthogonalIndexer.spec')
    $Exe = Join-Path $Root 'dist\CrystallographicOrthogonalIndexer\CrystallographicOrthogonalIndexer.exe'
    if (-not (Test-Path -LiteralPath $Exe)) { throw 'The Windows executable was not produced.' }
    $Smoke = Join-Path $Root '.build\frozen-smoke.json'
    if (Test-Path -LiteralPath $Smoke) { Remove-Item -LiteralPath $Smoke }
    $Process = Start-Process -FilePath $Exe -ArgumentList @('--smoke-test', ('"' + $Smoke + '"')) -Wait -PassThru
    if ($Process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $Smoke)) { throw 'Frozen application smoke test failed.' }
    $SmokeResult = Get-Content -Raw -LiteralPath $Smoke | ConvertFrom-Json
    if ($SmokeResult.status -ne 'passed' -or -not $SmokeResult.frozen -or $SmokeResult.platform -ne 'win32') {
        throw 'The smoke receipt does not confirm a frozen Windows application.'
    }
    Invoke-Checked $IsccExe @('packaging\installer.iss')
    $Installer = Join-Path $Root 'release\CrystallographicOrthogonalIndexer-1.0-windows-x64-Setup.exe'
    if (-not (Test-Path -LiteralPath $Installer)) { throw 'Installer compilation produced no expected artifact.' }
    Get-FileHash -Algorithm SHA256 -LiteralPath $Exe,$Installer | Format-List | Out-File -Encoding UTF8 'release\SHA256.txt'
    @{
        state='built-not-installation-tested'; application='Crystallographic Orthogonal Indexer'; version='1.0';
        signed=$false; installer_executed=$false; native_dialog_manual_tested=$false;
        iscc_version=$Info.FileVersion; built_utc=(Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json | Set-Content -Encoding UTF8 'release\build-receipt.json'
    Write-Host "Built candidate: $Installer"
    Write-Host 'Unsigned. Installer has NOT been executed. Complete WINDOWS_QA.md before distribution.'
} finally {
    Pop-Location
}
