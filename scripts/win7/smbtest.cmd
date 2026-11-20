@echo off
mkdir C:\lab\evidence 2>nul
echo %DATE% %TIME% smbtest start>> C:\lab\evidence\smbtest_trace.txt
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep 25; & 'C:\lab\smbtest.ps1'" >> C:\lab\evidence\smbtest_trace.txt 2>&1
del /f /q C:\lab\smbtest.ps1 C:\lab\smbtest.cmd 2>nul
sc delete LabSmbTest>> C:\lab\evidence\smbtest_trace.txt 2>&1
shutdown /s /t 8 /c "Lab SMB test done"
