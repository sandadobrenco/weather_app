Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root        = Split-Path -Parent $PSScriptRoot
$ProtoDir    = Join-Path $Root 'proto'
$OutDir      = Join-Path $Root 'generated'
$VenvPy      = Join-Path $Root 'venv\Scripts\python.exe'
$VenvScripts = Join-Path $Root 'venv\Scripts'

if (Test-Path $VenvPy) { $Python = $VenvPy } else { $Python = 'python' }
if (Test-Path $VenvScripts) { $env:PATH = "$VenvScripts;$env:PATH" }

Write-Host "Root: $Root"
Write-Host "ProtoDir: $ProtoDir"
Write-Host "OutDir: $OutDir"
Write-Host "Python: $Python"

$ProtoFile = Join-Path $ProtoDir 'weather.proto'
if (-not (Test-Path $ProtoFile)) { throw "Missing proto file: $ProtoFile" }

$PyInclude = & $Python -c "import os, grpc_tools; print(os.path.join(os.path.dirname(grpc_tools.__file__), '_proto'))"
Write-Host "PyInclude: $PyInclude"

New-Item -ItemType Directory -Force $OutDir | Out-Null
$initFile = Join-Path $OutDir '__init__.py'
if (-not (Test-Path $initFile)) { New-Item -ItemType File -Path $initFile | Out-Null }

$HasMypy     = Test-Path (Join-Path $VenvScripts 'protoc-gen-mypy.exe')
$HasMypyGrpc = Test-Path (Join-Path $VenvScripts 'protoc-gen-mypy_grpc.exe')

$args = @(
  '-I', $ProtoDir,
  '-I', $PyInclude,
  '--python_out', $OutDir,
  '--grpc_python_out', $OutDir
)

if ($HasMypy)     { $args += @('--mypy_out', $OutDir) }
if ($HasMypyGrpc) { $args += @('--mypy_grpc_out', $OutDir) }

Write-Host "Running protoc..."
& $Python -m grpc_tools.protoc @args $ProtoFile
if ($LASTEXITCODE -ne 0) { throw "protoc failed with exit code $LASTEXITCODE" }

$expected = @('weather_pb2.py','weather_pb2_grpc.py','weather_pb2.pyi','weather_pb2_grpc.pyi')
foreach ($f in $expected) {
  $p = Join-Path $OutDir $f
  if (Test-Path $p) { Write-Host "[OK] $p" } else { Write-Host "[info] missing: $p" }
}
Write-Host "Generation completed. Output dir: $OutDir"
