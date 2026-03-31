Set shell = CreateObject("WScript.Shell")
projectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
pythonw = "C:\Users\User\AppData\Local\Programs\Python\Python311\pythonw.exe"
scriptPath = projectDir & "\instagram_store_search_gui.py"
shell.CurrentDirectory = projectDir
shell.Run """" & pythonw & """ """ & scriptPath & """", 0, False
