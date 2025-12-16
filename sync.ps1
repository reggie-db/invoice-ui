param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspacePath
)

$ErrorActionPreference = "Stop"

$gitPullJob = Start-Job -ScriptBlock {
    while ($true) {
        try {
            git pull --rebase --autostash | Out-Null
        }
        catch {
        }
        Start-Sleep -Seconds 10
    }
}

try {
    databricks sync --watch . $WorkspacePath
}
finally {
    Stop-Job $gitPullJob -Force | Out-Null
    Remove-Job $gitPullJob | Out-Null
}