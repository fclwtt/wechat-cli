' 微信聊天每日导出 - 隙执行（无窗口）
' 双击此文件即可后台运行

Set WshShell = CreateObject("WScript.Shell")
batPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\export-daily-html-hidden.bat"

' 隐藏窗口执行
WshShell.Run "cmd /c """"" & batPath & """""", 0, True

' 执行完成，弹窗提示
MsgBox "微信聊天每日导出完成！" & vbCrLf & vbCrLf & "输出目录: E:\wechat-chats-backup", vbInformation, "导出完成"