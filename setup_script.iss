; Script generated for Jiggle Monitor
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Jiggle Monitor"
#define MyAppVersion "1.0"
#define MyAppPublisher "KG"
#define MyAppExeName "JiggleMonitor.exe"
#define MyConfigDir "JiggleMonitor" ; Name of the config folder in AppData

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the Inno Setup IDE.)
AppId={{A3B4C5D6-E7F8-9012-3456-7890ABCDEF12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; FIX: Changing PrivilegesRequired to admin ensures installation defaults to Program Files
PrivilegesRequired=admin
; NEW FIX: Forces the installer to use 64-bit mode (Program Files instead of x86)
ArchitecturesInstallIn64BitMode=x64
OutputDir=installer_output
OutputBaseFilename=JiggleMonitor_Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Run Jiggle Monitor on Windows Startup"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; IMPORTANT: Make sure the path to your EXE is correct here.
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Registry]
; The ValueData includes the --startup flag, which tells the app this is a background launch.
; FIX: Added Flags: createvalueifdoesntexist to ensure the key is always written 
; if the task is selected, even if the user previously manually disabled it.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"" --startup"; Flags: uninsdeletevalue createvalueifdoesntexist; Tasks: startup

[UninstallDelete]
; Ensures the removal of files from the installation directory (Program Files)
Name: "{app}\{#MyAppExeName}"; Type: files
Name: "{app}\icon.ico"; Type: files

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent


[Code]
// Helper function to delete the configuration directory in AppData during uninstallation
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigPath: String;
begin
  if CurUninstallStep = usUninstall then begin
    // Get the path to the JiggleMonitor AppData folder
    ConfigPath := ExpandConstant('{localappdata}\{#MyConfigDir}');
    
    // Check if the directory exists before attempting to delete it
    if DirExists(ConfigPath) then begin
      // This function deletes the directory and all files/subdirectories inside it.
      // The parameter True tells it to delete subdirectories and files first.
      if not DelTree(ConfigPath, True, True, True) then begin
        // If deletion fails (e.g., file locked), show a warning but don't stop uninstall.
        Log('Failed to fully delete config path: ' + ConfigPath);
        // Note: We rely on the improved single-instance check cleaning the lock file on exit.
      end;
    end;
  end;
end;