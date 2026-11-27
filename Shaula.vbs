' Abre a Shaula SEM janela de console.
'
' O Shaula.bat roda em modo "oculto": a janela do console existe, mas
' fica invisivel, e tudo o que ela mostraria vai para
' %USERPROFILE%\.shaula\logs\shaula.log
'
' Se a Shaula nao conseguir abrir, aparece uma mensagem com o final do
' registro. Para abrir COM console (acompanhar o que ela faz), use o
' Shaula.bat direto.

Option Explicit

Dim shell, fso, pasta, bat, codigo, log

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

pasta = fso.GetParentFolderName(WScript.ScriptFullName)
bat = pasta & "\Shaula.bat"

shell.CurrentDirectory = pasta

If Not fso.FileExists(bat) Then
    MsgBox "Nao encontrei o Shaula.bat em:" & vbCrLf & pasta, 16, "Shaula"
    WScript.Quit 1
End If

' 0 = janela oculta; True = espera a Shaula fechar para ver como terminou.
codigo = shell.Run("""" & bat & """ oculto", 0, True)

If codigo <> 0 Then
    log = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.shaula\logs\shaula.log"
    MsgBox "A Shaula nao conseguiu iniciar (codigo " & codigo & ")." & _
        vbCrLf & vbCrLf & "Final do registro:" & vbCrLf & _
        UltimasLinhas(log, 10) & vbCrLf & "Registro completo:" & vbCrLf & log, _
        16, "Shaula"
End If

Function UltimasLinhas(caminho, quantas)
    Dim arquivo, texto, linhas, i, inicio, saida

    If Not fso.FileExists(caminho) Then
        UltimasLinhas = "(o registro nao foi criado)" & vbCrLf
        Exit Function
    End If

    Set arquivo = fso.OpenTextFile(caminho, 1, False)

    If arquivo.AtEndOfStream Then
        arquivo.Close
        UltimasLinhas = "(o registro esta vazio)" & vbCrLf
        Exit Function
    End If

    texto = arquivo.ReadAll
    arquivo.Close

    linhas = Split(texto, vbCrLf)
    inicio = UBound(linhas) - quantas + 1

    If inicio < 0 Then inicio = 0

    For i = inicio To UBound(linhas)
        If Trim(linhas(i)) <> "" Then saida = saida & linhas(i) & vbCrLf
    Next

    ' MsgBox corta textos muito longos: fica so o final.
    If Len(saida) > 700 Then saida = "..." & Right(saida, 700)

    UltimasLinhas = saida
End Function
