Option Explicit
Dim shell, files, root, installed, portable, installer, python, command, arg
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
installed = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Graffy\Graffy.exe"
portable = root & "\dist\Graffy\Graffy.exe"
installer = root & "\dist\Graffy_Windows_Setup.exe"
python = root & "\.venv\Scripts\pythonw.exe"
If files.FileExists(installed) Then
    command = Chr(34) & installed & Chr(34)
ElseIf files.FileExists(portable) Then
    command = Chr(34) & portable & Chr(34)
ElseIf files.FileExists(installer) Then
    MsgBox "Let's install Graffy. Click Install, then Finish to open the app. Next time, use the Graffy desktop or Start menu shortcut.", vbInformation, "Welcome to Graffy"
    command = Chr(34) & installer & Chr(34)
ElseIf files.FileExists(python) Then
    command = Chr(34) & python & Chr(34) & " " & Chr(34) & root & "\main.py" & Chr(34)
Else
    MsgBox "Download the Graffy Windows installer from the Graffy download website. Open it, click Install, then launch Graffy from your desktop. You do not need Python.", vbInformation, "Install Graffy"
    shell.Run "https://graffy-scientific-graphing.recentdream1.chatgpt.site", 1, False
    WScript.Quit
End If
For Each arg In WScript.Arguments
    command = command & " " & Chr(34) & Replace(arg, Chr(34), "") & Chr(34)
Next
shell.CurrentDirectory = root
On Error Resume Next
shell.Run command, 1, False
If Err.Number <> 0 Then MsgBox "Graffy could not open. Please run the installer in the dist folder, or download it from the Graffy download website.", vbExclamation, "Graffy"
