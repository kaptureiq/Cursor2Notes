# Cursor2Notes

Consulta local das conversas do agente do Cursor. O aplicativo roda localmente: não sobe servidor, não pede login e não altera as conversas originais do Cursor.

Cada Folder aberto no Cursor corresponde a uma pasta deste computador. A tela lista as conversas desse Folder, com o pedido, os comandos executados, os comentários e o comentário final. Dá para filtrar a pasta, buscar por pedido, comando ou comentário, e restringir a leitura a pedidos, comentários ou comandos.

A conversa aberta tem três botões de exportação:

- **HTML** — página única, para abrir no navegador ou imprimir
- **Markdown** — texto para arquivar ou colar em outro editor
- **PDF** — documento paginado, com acentos

O arquivo exportado leva a conversa inteira. O corpo de arquivos gravados ou editados na conversa não entra: o registro fica só com o caminho.

Na barra lateral, escolha o idioma da interface e abra a página **Ficha técnica**, que descreve o aplicativo, o stack e as fronteiras de leitura.

## Organização e exportação

- **Favoritas e tags:** marque uma conversa como favorita e atribua tags separadas por vírgula. Na barra lateral, filtre por favoritas ou por tag. Os dados ficam em `metadados.json`, ao lado do app, e as conversas do Cursor não são alteradas.
- **Front matter no Markdown:** cada `.md` começa com título, sessão, pasta, datas, favorita e tags, para importar no Obsidian ou no Notion sem ajustes.
- **Exportar pasta inteira:** na barra lateral, escolha os formatos e gere um ZIP com todas as conversas da pasta e um `indice.html`. Com "Só conversas novas ou alteradas", o ZIP leva apenas o que mudou desde a última exportação de cada formato.
- **Cabeçalho e logo do PDF:** edite `export.json` com o texto do cabeçalho e o caminho de um logo PNG ou JPG (relativo a esta pasta ou absoluto).
- **Redação de segredos:** antes de qualquer exportação, senhas, tokens, chaves e strings de conexão são trocados por `[REDIGIDO]`. Os padrões embutidos estão em `redacao.py`. Em `redacao.json` você pode adicionar regras próprias ou desativar regras embutidas pelo nome. A tela continua mostrando o texto original.

Para o caminho das conversas, defina a variável `CURSOR2NOTES_PROJECTS_ROOT` se o Cursor não estiver na pasta padrão `~/.cursor/projects`.

## Aparência e idioma

- **Temas:** 18 temas dos grupos Oficiais, Fintech e GeoTech, extraídos do KaptureBOARD e guardados em `temas.json`. O padrão é Kapture SAP. Escolha em **Aparência**, na barra lateral.
- **Idiomas:** português (Brasil), inglês, espanhol, francês (França), francês (Canadá) e alemão. Os textos ficam em `i18n.py`. A troca vale para a interface; os arquivos exportados e as mensagens vindas da leitura do Cursor continuam em português.

## Testes

Na pasta do aplicativo, com o `.venv` ativo:

```powershell
python -m unittest discover -p "test_*.py"
```

## Instalação

A pasta do aplicativo é autossuficiente. O leitor das conversas está em `cursor_agent_sessions.py`, ao lado de `app.py`, então a pasta pode ser copiada para qualquer lugar.

É preciso ter Python 3.11 ou mais recente no PATH.

Na pasta do aplicativo, crie o ambiente virtual, instale as dependências e inicie:

```powershell
cd caminho\para\cursor2notes
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O `requirements.txt` pede o Streamlit, para a tela, e o fpdf2, para o PDF. O ambiente `.venv` fica só nesta pasta.

O navegador abre em `http://localhost:8501`. Para encerrar, use Ctrl+C no terminal. Na próxima vez, basta ativar o `.venv` e repetir o `streamlit run`.
