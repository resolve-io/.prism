<#
.SYNOPSIS
    Discovers the development root directory dynamically.

.DESCRIPTION
    Attempts to find the dev root using multiple strategies:
    1. Check for DEV_ROOT environment variable
    2. Look for common dev root indicators (resolve.dev.resources repo)
    3. Search parent directories from current location
    4. Fall back to D:\dev if nothing else works

.OUTPUTS
    String - Absolute path to dev root (e.g., "D:\dev")

.EXAMPLE
    $devRoot = & .\Get-DevRoot.ps1
    # Returns: D:\dev

.NOTES
    This script enables portability across different dev root locations.
#>

[CmdletBinding()]
param()

Write-Verbose "Discovering dev root..."

# Strategy 1: Check environment variable
if ($env:DEV_ROOT) {
    if (Test-Path $env:DEV_ROOT) {
        Write-Verbose "Found dev root from DEV_ROOT environment variable: $env:DEV_ROOT"
        return $env:DEV_ROOT
    }
}

# Strategy 2: Check current directory and parents for resolve.dev.resources
$currentDir = Get-Location
$searchDir = $currentDir

while ($searchDir) {
    $indicator = Join-Path $searchDir "resolve.dev.resources"
    if (Test-Path $indicator) {
        Write-Verbose "Found dev root by searching upward: $searchDir"
        return $searchDir.Path
    }

    # Move to parent directory
    $parent = Split-Path -Parent $searchDir
    if ($parent -eq $searchDir) {
        # Reached root, stop
        break
    }
    $searchDir = $parent
}

# Strategy 3: Check common locations
$commonLocations = @(
    "D:\dev",
    "C:\dev",
    "C:\source\resolve",
    "$env:USERPROFILE\dev",
    "$env:USERPROFILE\source\resolve"
)

foreach ($location in $commonLocations) {
    $indicator = Join-Path $location "resolve.dev.resources"
    if (Test-Path $indicator) {
        Write-Verbose "Found dev root at common location: $location"
        return $location
    }
}

# Strategy 4: Fall back to D:\dev (original default)
Write-Verbose "Using fallback dev root: D:\dev"
return "D:\dev"
