' WeChat Daily Export - Silent Execution
' Double-click to export yesterday's active chats (no window)

Set WshShell = CreateObject("WScript.Shell")
batPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\export-daily-hidden.bat"

' Run hidden
WshShell.Run "cmd /c """"" & batPath & """""", 0, True

' Show completion message
MsgBox "WeChat Daily Export Complete!" & vbCrLf & vbCrLf & "Output: C:\Users\13658\wechat-chats-backup" & vbCrLf & "Index: daily-index\YYYY-MM-DD.txt", vbInformation, "Export Complete"