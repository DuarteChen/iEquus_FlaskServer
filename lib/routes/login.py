'''
FE -> BE end recebe um pedido de login com email e com o datetime.now()
BE -> FE envia uma password de sessão gerada encriptada com a chave pública do FE
    se consefuir ler a chave continua, se falhar dá erro e nunca envia a pass
FE -> BE envia um hash da pass encriptada com a chave de sessão
BE compara o hash e aceita
'''