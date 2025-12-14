# --- Function Definition ---
function Get-DirectoryTreeString {
    param(
        [string]$Path,
        [string[]]$ExcludeList,
        [string]$Indent = ""
    )

    $treeString = ""

    Get-ChildItem -Path $Path -Directory | ForEach-Object {
        $directory = $_
        $isExcluded = $ExcludeList | Where-Object { (Split-Path $directory.FullName -Parent) -ilike $_ }

        if (-not $isExcluded) {
            $treeString += "$Indent|-- $($directory.Name)`n"
            $treeString += Get-DirectoryTreeString -Path $directory.FullName -ExcludeList $ExcludeList -Indent ($Indent + "|   ")
        }
    }

    Get-ChildItem -Path $Path -File -Exclude $ExcludeList | ForEach-Object {
        $file = $_
        $treeString += "$Indent|-- $($file.Name)`n"
    }
    return $treeString
}

# Ensure the console itself can display UTF8 (Optional, helpful for debugging logs)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

[string[]]$excludeFolderList = @( # Exclusion list
    "*list_dirs_and_files*",
    "apply_rules_update.py",
    "*\node_modules*",
    "*.git*",
    "*.clinerules",
    "*.mypy_cache*",
    "*.pytest_cache*",
    "*.vscode",
    "*.gitkeep",
    "*.ruff_cache*",
    "*\output*",
    "*\dist*",
    "*\build\*",
    "*\temp*",
    "*.log",
    "*.map",
    "*.bak",
    "*.bat",
    "*.temp",
    "*.env",
    "*.md",
    "*.json",
    "*.lnk",
    "*.exe",
    "*.dll",
    "*.ico",
    "**.db",
    "**.db-shm",
    "**.db-wal",
    "*\.VSCodeCounter*",
    "*LICENSE",
    "*\chroma_db*",
    "*pnpm-lock.yaml",
    "*campaign_load.log*",
    "*.pyc",
    "*.md",
    "*.roo*",
	"*\examples*",
	"*__pycache__*",
	"*\tests\*",
    "*package-lock.json",
    "*.DS_Store", 
    "*\docs*"
)

$directoryToCrawl = ".\" 
$outputFilePath = ".\list_dirs_and_files.txt" 

# Use a StringBuilder for better memory performance with large text
$sb = [System.Text.StringBuilder]::new()

Write-Host "Crawling directory: $($directoryToCrawl)" -ForegroundColor Cyan
Write-Host "Excluding items:" $($excludeFolderList -join ", ") -ForegroundColor Cyan

Write-Host "Generating directory tree..." -ForegroundColor Cyan
$treeOutput = Get-DirectoryTreeString -Path $directoryToCrawl -ExcludeList $excludeFolderList
Write-Host "Directory tree generated." -ForegroundColor Cyan

# Append Header info
[void]$sb.AppendLine("--- Directory Tree Structure ---")
[void]$sb.AppendLine('```')
[void]$sb.AppendLine($treeOutput)
[void]$sb.AppendLine('```')
[void]$sb.AppendLine("`n--- File List and Contents ---")

Get-ChildItem -Path $directoryToCrawl -Recurse -File -Exclude $excludeFolderList | ForEach-Object {
    $allowed = $true
    foreach ($exclude in $excludeFolderList) { 
        if ((Split-Path $_.FullName -Parent) -ilike $exclude) { 
            $allowed = $false
            break
        }
    }
    if ($allowed) {
        Write-Host "Processing file: $($_.FullName)" -ForegroundColor Cyan 
        
        # Append File Header
        [void]$sb.AppendLine('```')
        [void]$sb.AppendLine("File: $($_.FullName)")
        
        # --- THE FIX: Use .NET File Reader to force UTF8 reading ---
        try {
            # This reads the file forcing UTF-8 encoding. 
            # If your files are strictly ASCII or UTF-8, this works perfectly.
            $fileContent = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
            [void]$sb.AppendLine($fileContent)
        }
        catch {
            Write-Host "Error reading file $($_.FullName): $_" -ForegroundColor Red
            [void]$sb.AppendLine("[Error reading file content]")
        }

        # Append File Footer
        [void]$sb.AppendLine('```')
        [void]$sb.AppendLine("") 
    } else {
        Write-Host "Ignoring: $($_.FullName)" -ForegroundColor Gray 
    }
}

# --- THE FIX: Use .NET File Writer to ensure output is UTF8 ---
try {
    [System.IO.File]::WriteAllText($outputFilePath, $sb.ToString(), [System.Text.Encoding]::UTF8)
    Write-Host "Output written to: $($outputFilePath)" -ForegroundColor Cyan 
}
catch {
    Write-Host "Failed to write output file: $_" -ForegroundColor Red
}

Write-Host "Run script with -Verbose to see 'Ignoring' messages." -ForegroundColor DarkGray 

pause