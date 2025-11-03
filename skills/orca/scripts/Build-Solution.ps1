<#
.SYNOPSIS
    Builds a solution using the appropriate build tool (dotnet or msbuild).

.DESCRIPTION
    Wrapper script that calls the correct build tool based on project type.
    Embedded from resolve.dev.resources/scripts/General Utils.ps1

.PARAMETER SolutionPath
    Full path to the .sln file

.PARAMETER BuildType
    "dotnet" or "msbuild"

.PARAMETER Configuration
    Build configuration (default: "Debug")

.OUTPUTS
    [PSCustomObject] with properties:
    - Success (bool)
    - BuildType (string)
    - SolutionPath (string)
    - Message (string)

.EXAMPLE
    & .\Build-Solution.ps1 -SolutionPath "D:\dev\orca\orca.sln" -BuildType "dotnet"

.NOTES
    Replaces external PowerShell script dependencies.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$SolutionPath,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dotnet", "msbuild")]
    [string]$BuildType,

    [string]$Configuration = "Debug"
)

if (!(Test-Path $SolutionPath)) {
    throw "Solution file not found: $SolutionPath"
}

$solutionName = Split-Path -Leaf $SolutionPath

Write-Host "Building $solutionName ($BuildType)..." -ForegroundColor Yellow

try {
    if ($BuildType -eq "dotnet") {
        # .NET Core/9 build
        Write-Verbose "Running: dotnet build `"$SolutionPath`" -c $Configuration -v q"

        $output = dotnet build "$SolutionPath" -c $Configuration -v q 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR] Build failed" -ForegroundColor Red
            Write-Host $output
            throw "dotnet build failed with exit code $LASTEXITCODE"
        }

        Write-Host "  [OK] Build succeeded" -ForegroundColor Green

    } elseif ($BuildType -eq "msbuild") {
        # .NET Framework build
        $msbuildPath = "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe"

        if (!(Test-Path $msbuildPath)) {
            throw "MSBuild not found at: $msbuildPath"
        }

        Write-Verbose "Running: MSBuild `"$SolutionPath`" /p:Configuration=$Configuration /verbosity:minimal"

        $output = & $msbuildPath "$SolutionPath" "/p:Configuration=$Configuration" "/verbosity:minimal" 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR] Build failed" -ForegroundColor Red
            Write-Host $output
            throw "MSBuild failed with exit code $LASTEXITCODE"
        }

        Write-Host "  [OK] Build succeeded" -ForegroundColor Green
    }

    return [PSCustomObject]@{
        Success = $true
        BuildType = $BuildType
        SolutionPath = $SolutionPath
        Message = "Build succeeded"
    }

} catch {
    return [PSCustomObject]@{
        Success = $false
        BuildType = $BuildType
        SolutionPath = $SolutionPath
        Message = "Build failed: $_"
    }
}
