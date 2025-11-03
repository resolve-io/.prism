<#
.SYNOPSIS
    Checks if a repository needs to be rebuilt.

.DESCRIPTION
    Determines if a build is required by checking:
    1. Branch changes (current vs cached)
    2. Build output existence
    3. Source file timestamps vs build timestamps

.PARAMETER RepoInfo
    PSCustomObject from Get-ActionsRepos with Name, Path, BuildType, BinPath

.PARAMETER BranchCache
    Hashtable from Get-BranchCache with cached branch names

.OUTPUTS
    [PSCustomObject] with properties:
    - BuildRequired (bool)
    - Reason (string): "BranchChanged", "NoBuildOutput", "SourceNewer", or "UpToDate"
    - CurrentBranch (string)
    - CachedBranch (string or null)

.EXAMPLE
    $repo = @{ Name="orca"; Path="D:\dev\orca"; BinPath="Orca.AppHost/bin/Debug/net9.0" }
    $branchCache = @{ "orca" = "main" }
    $result = & .\Check-BuildRequired.ps1 -RepoInfo $repo -BranchCache $branchCache

.NOTES
    This is the core build detection logic.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [PSCustomObject]$RepoInfo,

    [Parameter(Mandatory=$true)]
    [hashtable]$BranchCache
)

$repoName = $RepoInfo.Name
$repoPath = $RepoInfo.Path

Write-Verbose "Checking if build required for: $repoName"

# Step 1: Get current branch
Push-Location $repoPath
try {
    $currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Verbose "  Not a git repository, assuming build not required"
        return [PSCustomObject]@{
            BuildRequired = $false
            Reason = "NotGitRepo"
            CurrentBranch = $null
            CachedBranch = $null
        }
    }
} finally {
    Pop-Location
}

Write-Verbose "  Current branch: $currentBranch"

# Step 2: Check branch cache
$cachedBranch = $BranchCache[$repoName]
Write-Verbose "  Cached branch: $cachedBranch"

if ($cachedBranch -and ($currentBranch -ne $cachedBranch)) {
    Write-Verbose "  Branch changed: $cachedBranch -> $currentBranch"
    return [PSCustomObject]@{
        BuildRequired = $true
        Reason = "BranchChanged"
        CurrentBranch = $currentBranch
        CachedBranch = $cachedBranch
    }
}

# Step 3: Check if build output exists
$binPath = Join-Path $repoPath $RepoInfo.BinPath
Write-Verbose "  Bin path: $binPath"

if (!(Test-Path $binPath)) {
    Write-Verbose "  Build output directory not found"
    return [PSCustomObject]@{
        BuildRequired = $true
        Reason = "NoBuildOutput"
        CurrentBranch = $currentBranch
        CachedBranch = $cachedBranch
    }
}

# Find newest DLL in bin path
$newestDll = Get-ChildItem -Path $binPath -Filter "*.dll" -Recurse -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (!$newestDll) {
    Write-Verbose "  No DLLs found in build output"
    return [PSCustomObject]@{
        BuildRequired = $true
        Reason = "NoBuildOutput"
        CurrentBranch = $currentBranch
        CachedBranch = $cachedBranch
    }
}

Write-Verbose "  Newest DLL: $($newestDll.FullName) ($($newestDll.LastWriteTime))"

# Step 4: Check if any source files are newer than build output
$sourceExtensions = @("*.cs", "*.vb", "*.csproj", "*.vbproj", "*.sln")
$newerSourceFiles = Get-ChildItem -Path $repoPath -Include $sourceExtensions -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notlike "*\bin\*" -and
        $_.FullName -notlike "*\obj\*" -and
        $_.LastWriteTime -gt $newestDll.LastWriteTime
    } |
    Select-Object -First 5

if ($newerSourceFiles) {
    Write-Verbose "  Found $(@($newerSourceFiles).Count) source file(s) newer than build output"
    return [PSCustomObject]@{
        BuildRequired = $true
        Reason = "SourceNewer"
        CurrentBranch = $currentBranch
        CachedBranch = $cachedBranch
    }
}

Write-Verbose "  Build is up to date"
return [PSCustomObject]@{
    BuildRequired = $false
    Reason = "UpToDate"
    CurrentBranch = $currentBranch
    CachedBranch = $cachedBranch
}
