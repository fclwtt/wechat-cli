' WeChat Full Export - Silent Execution
' Double-click to export all chats (no window)

Set WshShell = CreateObject("WScript.Shell")
batPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\export-all-hidden.bat"

' Run hidden
WshShell.Run "cmd /c """"" & batPath & """""", 0, True

' Show completion message
MsgBox "WeChat Full Export Complete!" & vbCrLf & vbCrLf & "Output: E:\共享文件夹\wechat-chats-backup", vbInformation, "Export Complete"