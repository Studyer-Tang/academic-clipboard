Option Explicit

Dim shell, fileSystem, projectDirectory, pythonw, command
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

projectDirectory = fileSystem.GetParentFolderName(WScript.ScriptFullName)
pythonw = fileSystem.BuildPath(projectDirectory, ".venv\Scripts\pythonw.exe")

If Not fileSystem.FileExists(pythonw) Then
    MsgBox "Please install the project first. / 请先安装项目。", vbExclamation, "Academic Clipboard"
    WScript.Quit 1
End If

command = Chr(34) & pythonw & Chr(34) & " -m academic_clipboard run --hidden"
shell.Run command, 0, False
