' Lanza analizar_lote.cmd sin ventana de consola (la usa el Programador de
' tareas: con una ventana visible, cerrarla corta la pasada a medias).
' Devuelve el código de salida del .cmd como resultado de la tarea.
Set sh = CreateObject("WScript.Shell")
cmd = Replace(WScript.ScriptFullName, WScript.ScriptName, "analizar_lote.cmd")
WScript.Quit sh.Run("cmd.exe /c """ & cmd & """", 0, True)
