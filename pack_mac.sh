#!/bin/bash
echo "Installing PyInstaller..."
pip install pyinstaller
echo "Packaging the application..."
pyinstaller --name "WorkTimeTracker" --onedir --windowed --add-data "config.yaml:." main.py
echo "Packaging completed. The application directory is in the dist folder." 