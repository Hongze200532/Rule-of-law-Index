$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms.DataVisualization

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir

$ruleOfLawFile = Join-Path $scriptDir "WB_index\API_RL.EST_DS2_en_csv_v2_5814.csv"
$metadataFile = Join-Path $scriptDir "WB_index\Metadata_Country_API_RL.EST_DS2_en_csv_v2_5814.csv"
$outputPng = Join-Path $projectDir "rl_est_us_china_japan_africa_latam_euro_area_1990_2025.png"
$outputCsv = Join-Path $projectDir "rl_est_us_china_japan_africa_latam_euro_area_1990_2025.csv"

$startYear = 1990
$endYear = 2025
$years = $startYear..$endYear

$singleSeries = [ordered]@{
    "United States" = "USA"
    "China" = "CHN"
    "Japan" = "JPN"
}

$euroAreaMembers2015 = @(
    "AUT", "BEL", "CYP", "DEU", "ESP", "EST", "FIN", "FRA", "GRC", "IRL",
    "ITA", "LTU", "LUX", "LVA", "MLT", "NLD", "PRT", "SVK", "SVN"
)

$seriesStyles = @{
    "United States" = @{ Color = "31,119,180"; Width = 2 }
    "China" = @{ Color = "214,39,40"; Width = 2 }
    "Japan" = @{ Color = "44,160,44"; Width = 2 }
    "Africa" = @{ Color = "140,86,75"; Width = 2 }
    "Latin America" = @{ Color = "255,127,14"; Width = 2 }
    "Euro area" = @{ Color = "148,103,189"; Width = 2 }
}

function Get-CsvRowsAfterHeaderOffset {
    param(
        [string]$Path,
        [int]$SkipLines
    )

    return Get-Content -Path $Path | Select-Object -Skip $SkipLines | ConvertFrom-Csv
}

function Convert-ToNullableDouble {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    $parsed = 0.0
    if ([double]::TryParse($Value, [ref]$parsed)) {
        return $parsed
    }

    return $null
}

$ruleOfLawRows = Get-CsvRowsAfterHeaderOffset -Path $ruleOfLawFile -SkipLines 4
$metadataRows = Import-Csv -Path $metadataFile -Header country_code, region, income_group, special_notes, country_name

$regionByCode = @{}
foreach ($row in $metadataRows) {
    $countryCode = ($row.country_code -replace '"', '').Trim()
    $region = ($row.region -replace '"', '').Trim()
    if ($countryCode) {
        $regionByCode[$countryCode] = $region
    }
}

$seriesData = New-Object System.Collections.Generic.List[object]

foreach ($seriesName in $singleSeries.Keys) {
    $countryCode = $singleSeries[$seriesName]
    $row = $ruleOfLawRows | Where-Object { $_.'Country Code' -eq $countryCode } | Select-Object -First 1
    if (-not $row) {
        continue
    }

    foreach ($year in $years) {
        $value = Convert-ToNullableDouble $row."$year"
        $seriesData.Add([pscustomobject]@{
            series = $seriesName
            year = $year
            rl_est = $value
        })
    }
}

$countryRows = $ruleOfLawRows | Where-Object { $regionByCode.ContainsKey($_.'Country Code') }

foreach ($year in $years) {
    $africaValues = @(
        $countryRows |
        Where-Object { $regionByCode[$_.'Country Code'] -eq "Sub-Saharan Africa" } |
        ForEach-Object { Convert-ToNullableDouble $_."$year" } |
        Where-Object { $_ -ne $null }
    )

    $latamValues = @(
        $countryRows |
        Where-Object { $regionByCode[$_.'Country Code'] -eq "Latin America & Caribbean" } |
        ForEach-Object { Convert-ToNullableDouble $_."$year" } |
        Where-Object { $_ -ne $null }
    )

    $euroValues = @(
        $countryRows |
        Where-Object { $euroAreaMembers2015 -contains $_.'Country Code' } |
        ForEach-Object { Convert-ToNullableDouble $_."$year" } |
        Where-Object { $_ -ne $null }
    )

    $africaMean = if ($africaValues.Count -gt 0) { ($africaValues | Measure-Object -Average).Average } else { $null }
    $latamMean = if ($latamValues.Count -gt 0) { ($latamValues | Measure-Object -Average).Average } else { $null }
    $euroMean = if ($euroValues.Count -gt 0) { ($euroValues | Measure-Object -Average).Average } else { $null }

    $seriesData.Add([pscustomobject]@{ series = "Africa"; year = $year; rl_est = $africaMean })
    $seriesData.Add([pscustomobject]@{ series = "Latin America"; year = $year; rl_est = $latamMean })
    $seriesData.Add([pscustomobject]@{ series = "Euro area"; year = $year; rl_est = $euroMean })
}

$seriesData |
    Sort-Object series, year |
    Export-Csv -Path $outputCsv -NoTypeInformation -Encoding UTF8

$chart = New-Object System.Windows.Forms.DataVisualization.Charting.Chart
$chart.Width = 3570
$chart.Height = 2066
$chart.BackColor = [System.Drawing.Color]::White

$chartArea = New-Object System.Windows.Forms.DataVisualization.Charting.ChartArea
$chartArea.Name = "Main"
$chartArea.BackColor = [System.Drawing.Color]::White
$chartArea.Position.Auto = $false
$chartArea.Position.X = 8
$chartArea.Position.Y = 10
$chartArea.Position.Width = 68
$chartArea.Position.Height = 78
$chartArea.AxisX.Title = "Year"
$chartArea.AxisX.TitleFont = New-Object System.Drawing.Font("Arial", 18)
$chartArea.AxisX.LabelStyle.Font = New-Object System.Drawing.Font("Arial", 14)
$chartArea.AxisX.Minimum = $startYear
$chartArea.AxisX.Maximum = $endYear
$chartArea.AxisX.Interval = 5
$chartArea.AxisX.MajorGrid.LineColor = [System.Drawing.Color]::LightGray
$chartArea.AxisY.Title = "Rule of Law Estimate (RL.EST)"
$chartArea.AxisY.TitleFont = New-Object System.Drawing.Font("Arial", 18)
$chartArea.AxisY.LabelStyle.Font = New-Object System.Drawing.Font("Arial", 14)
$chartArea.AxisY.MajorGrid.LineColor = [System.Drawing.Color]::LightGray
$chart.ChartAreas.Add($chartArea)

$title = New-Object System.Windows.Forms.DataVisualization.Charting.Title
$title.Text = "World Bank Rule of Law Estimate Over Time by Country"
$title.Font = New-Object System.Drawing.Font("Arial", 20)
$chart.Titles.Add($title)

$legend = New-Object System.Windows.Forms.DataVisualization.Charting.Legend
$legend.Title = "Country"
$legend.Font = New-Object System.Drawing.Font("Arial", 14)
$legend.TitleFont = New-Object System.Drawing.Font("Arial", 16)
$legend.Docking = "Right"
$legend.Alignment = "Near"
$legend.IsDockedInsideChartArea = $false
$chart.Legends.Add($legend)

$plotOrder = @(
    "United States",
    "China",
    "Japan",
    "Africa",
    "Latin America",
    "Euro area"
)

foreach ($seriesName in $plotOrder) {
    $series = New-Object System.Windows.Forms.DataVisualization.Charting.Series
    $series.Name = $seriesName
    $series.ChartType = [System.Windows.Forms.DataVisualization.Charting.SeriesChartType]::Line
    $series.BorderWidth = $seriesStyles[$seriesName].Width
    $series.MarkerStyle = [System.Windows.Forms.DataVisualization.Charting.MarkerStyle]::Circle
    $series.MarkerSize = 8

    $rgb = $seriesStyles[$seriesName].Color.Split(",") | ForEach-Object { [int]$_ }
    $series.Color = [System.Drawing.Color]::FromArgb($rgb[0], $rgb[1], $rgb[2])

    $points = $seriesData |
        Where-Object { $_.series -eq $seriesName -and $_.rl_est -ne $null } |
        Sort-Object year

    foreach ($point in $points) {
        [void]$series.Points.AddXY([double]$point.year, [double]$point.rl_est)
    }

    [void]$chart.Series.Add($series)
}

$chart.SaveImage($outputPng, "Png")

$firstAvailable = $seriesData |
    Where-Object { $_.rl_est -ne $null } |
    Group-Object series |
    Sort-Object Name |
    ForEach-Object {
        $year = ($_.Group | Sort-Object year | Select-Object -First 1).year
        [pscustomobject]@{
            series = $_.Name
            first_year = $year
        }
    }

Write-Output "Saved:"
Write-Output "- $outputPng"
Write-Output "- $outputCsv"
Write-Output "First available year by series:"
$firstAvailable | ForEach-Object { Write-Output "- $($_.series): $($_.first_year)" }
