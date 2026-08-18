VISION 2030 STATIC SITE

Run:
1. Extract the ZIP.
2. Right-click run_local.ps1 and choose Run with PowerShell.
3. If PowerShell blocks the script, open PowerShell in the folder and run:
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\run_local.ps1

The site opens at:
http://127.0.0.1:8000/briefing.html

Static pages:
- briefing.html
- insights.html
- data_explorer.html

This package preserves the captured static HTML states. Data wiring and generated insights are not connected yet.
