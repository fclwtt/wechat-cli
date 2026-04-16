' WeChat Daily Export - Silent Execution
' Double-click to run without visible window

Set WshShell = CreateObject("WScript.Shell")
batPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\export-daily-html-hidden.bat"

' Run hidden
WshShell.Run "cmd /c """"" & batPath & """""", 0, True

' Show completion message
MsgBox "WeChat Daily Export Complete!" & vbCrLf & vbCrLf & "Output: E:\wechat-chats-backup", vbInformation, "Export Complete"