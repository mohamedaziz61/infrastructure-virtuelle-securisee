@echo off
REM cli01 (Windows 7) security tooling: Sysmon + windows_exporter + audit/firewall checks.
REM Runs as LocalSystem once at boot via the temporary service "LabBootstrap" (injected offline), then removes it.
REM Evidence is written to C:\lab\evidence for the report.
setlocal
set L=C:\lab
set E=%L%\evidence
mkdir %E% 2>nul
echo ==== %DATE% %TIME% start > %E%\install.log
ver >> %E%\install.log
wmic os get Caption,Version,CSDVersion,OSArchitecture /value >> %E%\install.log 2>&1

REM --- 1. Sysmon (current official build; Windows 7 is no longer officially supported by Sysmon 15)
%L%\sysmon\Sysmon64.exe -accepteula -i %L%\sysmon-lab.xml >> %E%\sysmon_install.log 2>&1
echo sysmon_rc=%ERRORLEVEL% >> %E%\install.log
sc query Sysmon64 >> %E%\install.log 2>&1

REM --- 2. windows_exporter v0.18.1 (last release documented for Windows 7) on :9182
msiexec /i %L%\windows_exporter-0.18.1-amd64.msi /qn /norestart /l*v %E%\windows_exporter_msi.log ENABLED_COLLECTORS="cpu,cs,logical_disk,memory,net,os,service,system,tcp" LISTEN_PORT=9182
echo exporter_rc=%ERRORLEVEL% >> %E%\install.log
REM Only Prometheus on srv01 may scrape it
netsh advfirewall firewall add rule name="windows_exporter from srv01" dir=in action=allow protocol=TCP localport=9182 remoteip=192.168.20.10 >> %E%\install.log
sc query windows_exporter >> %E%\install.log 2>&1

REM --- 3. Evidence: firewall, audit policy, accounts
netsh advfirewall show allprofiles > %E%\firewall_profiles.txt
netsh advfirewall firewall show rule name=all dir=in > %E%\firewall_inbound_rules.txt
auditpol /get /category:* > %E%\auditpol.txt
net accounts > %E%\password_policy.txt
net user > %E%\users.txt
net localgroup Administrators > %E%\admins.txt
ipconfig /all > %E%\ipconfig.txt

REM --- 4. Generate test activity and capture Sysmon events
ping -n 1 192.168.10.1 > nul
nslookup srv01.lab.local 192.168.10.1 > %E%\dns_test.txt 2>&1
timeout /t 20 /nobreak > nul
wevtutil qe Microsoft-Windows-Sysmon/Operational /c:30 /rd:true /f:text > %E%\sysmon_events.txt 2>&1
wevtutil qe Security /c:30 /rd:true /f:text > %E%\security_events.txt 2>&1

echo ==== %DATE% %TIME% done >> %E%\install.log
REM --- 5. self-removal of the bootstrap service
sc delete LabBootstrap >> %E%\install.log 2>&1
endlocal
