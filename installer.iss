[Setup]
AppName=TO2 Skill Rate
AppVersion=1.0
DefaultDirName={pf}\TO2 Skill Rate
OutputBaseFilename=TO2SkillRateInstaller
SetupIconFile=icon.ico

[Files]
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TO2 Skill Rate"; Filename: "{app}\TO2 Skill Rate.exe"; IconFilename: "icon.ico"
Name: "{userdesktop}\TO2 Skill Rate"; Filename: "{app}\TO2 Skill Rate"; IconFilename: "icon.ico"

