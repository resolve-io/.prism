<#
.SYNOPSIS
    Gets the list of Actions repositories to check for builds.

.DESCRIPTION
    Returns the definitive list of repositories that are part of the Actions/Orca system.
    This replaces the external dependency on resolve.dev.resources PowerShell script.

.OUTPUTS
    Array of PSCustomObjects with properties:
    - Name: Repository name (e.g., "orca", "actions.api")
    - Path: Full path to repository
    - BuildType: "dotnet" or "msbuild"
    - SolutionPath: Relative path to .sln file from repo root

.EXAMPLE
    $repos = & .\Get-ActionsRepos.ps1
    foreach ($repo in $repos) {
        Write-Host "$($repo.Name): $($repo.BuildType)"
    }

.NOTES
    This script is embedded to eliminate external dependencies.
#>

[CmdletBinding()]
param()

# Get dev root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$getDevRootScript = Join-Path $scriptDir "Get-DevRoot.ps1"
$devRoot = & $getDevRootScript

Write-Verbose "Dev root: $devRoot"

# Define repository configurations
$repos = @(
    # .NET Core/9 projects (use dotnet build)
    [PSCustomObject]@{
        Name = "orca"
        Path = Join-Path $devRoot "orca"
        BuildType = "dotnet"
        SolutionPath = "orca.sln"
        BinPath = "Orca.AppHost/bin/Debug/net9.0"
    },
    [PSCustomObject]@{
        Name = "actions.api"
        Path = Join-Path $devRoot "actions.api"
        BuildType = "dotnet"
        SolutionPath = "actions.api.sln"
        BinPath = "src/bin/Debug/net9.0"
    },
    [PSCustomObject]@{
        Name = "actions.engine"
        Path = Join-Path $devRoot "actions.engine"
        BuildType = "dotnet"
        SolutionPath = "actions.engine.sln"
        BinPath = "libs"
    },
    [PSCustomObject]@{
        Name = "actions.manager"
        Path = Join-Path $devRoot "actions.manager"
        BuildType = "dotnet"
        SolutionPath = "actions.manager.sln"
        BinPath = "src/bin/Debug/net9.0"
    },

    # .NET Framework projects (use msbuild)
    [PSCustomObject]@{
        Name = "express-comm"
        Path = Join-Path $devRoot "express-comm"
        BuildType = "msbuild"
        SolutionPath = "src/eyeShare Comm Server/eyeShare Comm Server.sln"
        BinPath = "src/eyeShare Comm Server/bin"
    },
    [PSCustomObject]@{
        Name = "express-remote-comm"
        Path = Join-Path $devRoot "express-remote-comm"
        BuildType = "msbuild"
        SolutionPath = "eyeShareProj/eyeShare Comm Server Remote/eyeShare Comm Server Remote.sln"
        BinPath = "eyeShareProj/eyeShare Comm Server Remote/bin"
    },
    [PSCustomObject]@{
        Name = "express-engine"
        Path = Join-Path $devRoot "express-engine"
        BuildType = "msbuild"
        SolutionPath = "eyeShareEngine/eyeShareEngine.sln"
        BinPath = "eyeShareEngine/bin"
    },
    [PSCustomObject]@{
        Name = "express-executor"
        Path = Join-Path $devRoot "express-executor"
        BuildType = "msbuild"
        SolutionPath = "eyeShareExecutor/eyeShareExecutorServer.sln"
        BinPath = "eyeShareExecutor/eyeShareExecutorServer/bin"
    },
    [PSCustomObject]@{
        Name = "express-scheduler"
        Path = Join-Path $devRoot "express-scheduler"
        BuildType = "msbuild"
        SolutionPath = "eyeShareSchedulerServer/eyeShareSchedulerServer.sln"
        BinPath = "eyeShareSchedulerServer/bin"
    },
    [PSCustomObject]@{
        Name = "express-integrations"
        Path = Join-Path $devRoot "express-integrations"
        BuildType = "msbuild"
        SolutionPath = "ModulesSharedProject.sln"
        BinPath = "bin"
    },
    [PSCustomObject]@{
        Name = "express-web-api"
        Path = Join-Path $devRoot "express-web-api"
        BuildType = "msbuild"
        SolutionPath = "AyehuWebApi/EyeShare.sln"
        BinPath = "AyehuWebApi/EyeShare.Api/bin"
    }
)

# Filter to only repos that exist
$existingRepos = $repos | Where-Object { Test-Path $_.Path }

Write-Verbose "Found $($existingRepos.Count) existing repositories out of $($repos.Count) defined"

return $existingRepos
