[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$ReuseEnvironment
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core') {
    throw 'MDPeek Windows packages must be built on Windows.'
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BuildEnvironment = Join-Path $RepoRoot '.release-venv'
$BuildDirectory = Join-Path $RepoRoot 'build'
$DistDirectory = Join-Path $RepoRoot 'dist'
$InstallerOutput = Join-Path $RepoRoot 'installer\output'
$ArtifactDirectory = Join-Path $DistDirectory 'artifacts'

function Remove-KnownOutput([string]$Path) {
    $resolvedParent = (Resolve-Path (Split-Path $Path -Parent)).Path
    if (-not $Path.StartsWith($RepoRoot, [StringComparison]::OrdinalIgnoreCase) -or
        $resolvedParent -eq $RepoRoot -and (Split-Path $Path -Leaf) -notin @('build', 'dist')) {
        throw "Refusing to clean unexpected path: $Path"
    }
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

Push-Location $RepoRoot
try {
    if (-not $ReuseEnvironment -or -not (Test-Path "$BuildEnvironment\Scripts\python.exe")) {
        if (-not (Test-Path "$BuildEnvironment\Scripts\python.exe")) {
            & py -3.12 -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                & py -3.12 -m venv $BuildEnvironment
            } else {
                Write-Warning 'Python 3.12 is unavailable; using the default Python 3 (CI releases use 3.12).'
                & py -3 -m venv $BuildEnvironment
            }
        }
        & "$BuildEnvironment\Scripts\python.exe" -m pip install --upgrade pip
        & "$BuildEnvironment\Scripts\python.exe" -m pip install -e '.[release]'
    }

    & "$BuildEnvironment\Scripts\python.exe" -m pytest tests
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; no release artifact was built.' }

    Remove-KnownOutput $BuildDirectory
    Remove-KnownOutput $DistDirectory
    Remove-KnownOutput $InstallerOutput
    New-Item -ItemType Directory -Force -Path $BuildDirectory, $ArtifactDirectory | Out-Null

    & "$BuildEnvironment\Scripts\python.exe" scripts\release.py --write-version-info build\windows-version-info.txt
    & "$BuildEnvironment\Scripts\python.exe" -m PyInstaller --noconfirm --clean packaging\mdpeek.spec
    if (-not (Test-Path 'dist\MDPeek\MDPeek.exe')) { throw 'PyInstaller did not produce dist\MDPeek\MDPeek.exe.' }
    if (-not (Test-Path 'dist\MDPeek\_internal\assets\mdpeek.ico')) { throw 'The bundled runtime icon is missing.' }

    $PortableName = & "$BuildEnvironment\Scripts\python.exe" scripts\release.py --artifact portable
    Compress-Archive -LiteralPath 'dist\MDPeek' -DestinationPath (Join-Path $ArtifactDirectory $PortableName)

    $InstallerPath = $null
    if (-not $SkipInstaller) {
        $isccCandidates = @(
            (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
            "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
        ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
        if (-not $isccCandidates) { throw 'Inno Setup 6 was not found. Install it or use -SkipInstaller.' }
        $Version = & "$BuildEnvironment\Scripts\python.exe" scripts\release.py --version
        $InstallerName = & "$BuildEnvironment\Scripts\python.exe" scripts\release.py --artifact installer
        $InstallerBase = [IO.Path]::GetFileNameWithoutExtension($InstallerName)
        & $isccCandidates[0] "/DAppVersion=$Version" "/DOutputBaseFilename=$InstallerBase" installer\MDPeek.iss
        $InstallerPath = Join-Path $InstallerOutput $InstallerName
        if (-not (Test-Path $InstallerPath)) { throw "Inno Setup did not produce $InstallerName." }
        Copy-Item -LiteralPath $InstallerPath -Destination $ArtifactDirectory
    }

    $ChecksumName = & "$BuildEnvironment\Scripts\python.exe" scripts\release.py --artifact checksums
    $checksumTargets = Get-ChildItem -LiteralPath $ArtifactDirectory -File |
        Where-Object { $_.Extension -in '.exe', '.zip' } |
        Sort-Object Name
    $checksumLines = foreach ($file in $checksumTargets) {
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $($file.Name)"
    }
    Set-Content -LiteralPath (Join-Path $ArtifactDirectory $ChecksumName) -Value $checksumLines -Encoding ascii
    Write-Host "Artifacts are in $ArtifactDirectory"
} finally {
    Pop-Location
}
