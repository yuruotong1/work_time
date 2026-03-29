pyinstaller --name "WorkTimeTracker" --onefile --windowed main.py
Write-Host "Packaging completed. The exe is at dist\WorkTimeTracker.exe"
Write-Host "NOTE: config.yaml must be placed at %USERPROFILE%\.work_time\config.yaml before running."
