# PowerShell Examples for ULog Classifier HTTP API
#
# Prerequisites:
# 1. Start the service: uvicorn ulog.classifier.http:app --reload
# 2. Run in PowerShell: .\curl_examples.ps1

$BaseUrl = "http://localhost:8000"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "ULog Classifier HTTP API - Example Requests" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Health Check
Write-Host "1. Health Check" -ForegroundColor Yellow
Write-Host "   GET $BaseUrl/health" -ForegroundColor Gray
Write-Host ""
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host ""

# 2. Parse Endpoint - Single Raw Log
Write-Host "2. Parse Endpoint - Single Raw Log" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/parse" -ForegroundColor Gray
Write-Host ""
$body = @(
    @{
        "@timestamp" = "2025-10-22T10:15:30.123Z"
        "@message" = "INFO: Uvicorn running on http://0.0.0.0:8000"
    }
) | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/parse" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host ""

# 3. Parse Endpoint - Multiple Raw Logs
Write-Host "3. Parse Endpoint - Multiple Raw Logs" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/parse" -ForegroundColor Gray
Write-Host ""
$body = @(
    @{
        "@timestamp" = "2025-10-22T10:15:30.123Z"
        "@message" = "INFO: Uvicorn running on http://0.0.0.0:8000"
    },
    @{
        "@timestamp" = "2025-10-22T10:15:31.456Z"
        "@message" = "INFO: GET /api/users/123 returned 200 in 45ms"
    },
    @{
        "@timestamp" = "2025-10-22T10:15:32.789Z"
        "@message" = "ERROR: Database connection failed - timeout after 30s"
    }
) | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/parse" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host ""

# 4. Classify Endpoint - Raw Format
Write-Host "4. Classify Endpoint - Raw Format" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/classify" -ForegroundColor Gray
Write-Host ""
$body = @(
    @{
        "@timestamp" = "2025-10-22T10:15:32.789Z"
        "@message" = "ERROR: Database connection failed - timeout after 30s"
    }
) | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/classify" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host ""

# 5. Classify Endpoint - Normalized Format
Write-Host "5. Classify Endpoint - Normalized Format" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/classify" -ForegroundColor Gray
Write-Host ""
$body = @(
    @{
        timestamp = "2025-10-22T10:20:00.000Z"
        level = "info"
        category = "core_api"
        message = "Service started"
        outcome = "success"
    },
    @{
        timestamp = "2025-10-22T10:20:01.000Z"
        level = "error"
        category = "core_api"
        message = "Connection timeout"
        outcome = "failure"
    }
) | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/classify" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host ""

# 6. Error Case - Missing Required Field
Write-Host "6. Error Case - Missing Required Field (@timestamp)" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/parse" -ForegroundColor Gray
Write-Host ""
$body = @(
    @{
        "@message" = "This log is missing @timestamp field"
    }
) | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/parse" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Expected error (422):" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Gray
}
Write-Host ""
Write-Host ""

# 7. Error Case - Invalid JSON Structure
Write-Host "7. Error Case - Invalid JSON Structure (not an array)" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/classify" -ForegroundColor Gray
Write-Host ""
$body = @{
    timestamp = "2025-10-22T10:20:00.000Z"
    level = "info"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/classify" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Expected error (422):" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Gray
}
Write-Host ""
Write-Host ""

# 8. Using File Input
Write-Host "8. Parse Endpoint - Using File Input" -ForegroundColor Yellow
Write-Host "   POST $BaseUrl/parse (data from file)" -ForegroundColor Gray
Write-Host ""
if (Test-Path "sample_raw.jsonl") {
    # Read JSONL and convert to array
    $logs = @()
    Get-Content "sample_raw.jsonl" | ForEach-Object {
        $logs += $_ | ConvertFrom-Json
    }
    $body = $logs | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/parse" -Method Post -Body $body -ContentType "application/json"
        $response | ConvertTo-Json -Depth 10 | Select-Object -First 50
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   (sample_raw.jsonl not found - skipping)" -ForegroundColor Gray
}
Write-Host ""
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "All examples completed!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
