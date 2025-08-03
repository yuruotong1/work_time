pyinstaller --name "WorkTimeTracker" --onedir --windowed --add-data "config.yaml;." main.py
Write-Host "Packaging completed. The application directory is in the dist folder." 