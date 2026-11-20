@echo off
REM One-shot VLAN10 segmentation test on cli01, run as LocalSystem by the temporary service LabNetTest.
REM Ends with a clean shutdown so the VM never needs a hard power-off before evidence collection.
mkdir C:\lab\evidence 2>nul
echo %DATE% %TIME% start>> C:\lab\evidence\nettest_trace.txt
whoami>> C:\lab\evidence\nettest_trace.txt 2>&1
%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep 20; & 'C:\lab\nettest.ps1'" > C:\lab\evidence\nettest_run.log 2>&1
echo %DATE% %TIME% ps_rc=%ERRORLEVEL%>> C:\lab\evidence\nettest_trace.txt
sc delete LabNetTest>> C:\lab\evidence\nettest_trace.txt 2>&1
echo %DATE% %TIME% shutdown>> C:\lab\evidence\nettest_trace.txt
shutdown /s /t 10 /c "Lab: tests termines"
