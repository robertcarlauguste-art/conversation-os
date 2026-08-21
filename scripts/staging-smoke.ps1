param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$BearerToken
)

$ErrorActionPreference = "Stop"
$apiBase = $BaseUrl.TrimEnd("/")
$headers = @{ Authorization = "Bearer $BearerToken" }

function Assert-Status {
    param(
        [string]$Name,
        [string]$Path,
        [hashtable]$RequestHeaders = @{}
    )

    $response = Invoke-WebRequest `
        -Uri "$apiBase$Path" `
        -Headers $RequestHeaders `
        -Method Get `
        -UseBasicParsing

    if ($response.StatusCode -ne 200) {
        throw "$Name failed with HTTP $($response.StatusCode)."
    }
    Write-Host "PASS $Name"
    return $response.Content | ConvertFrom-Json
}

$health = Assert-Status -Name "liveness" -Path "/health"
if ($health.status -ne "ok") {
    throw "Liveness response did not report ok."
}

$readiness = Assert-Status -Name "readiness" -Path "/ready"
if ($readiness.status -ne "ready") {
    throw "Readiness response did not report ready."
}

$identity = Assert-Status -Name "authenticated identity" -Path "/api/v1/auth/me" `
    -RequestHeaders $headers
if (-not $identity.data.user_id) {
    throw "Authenticated identity response was incomplete."
}

$operations = Assert-Status -Name "operational status" -Path "/api/v1/operations" `
    -RequestHeaders $headers
if (-not $operations.success -or -not $operations.data.observed_at) {
    throw "Operational status response was incomplete."
}

Write-Host "Staging smoke checks passed for $apiBase."
