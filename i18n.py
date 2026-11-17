"""Textos do Cursor2Notes em seis idiomas.

Cada chave tem a tradução em: pt-BR, en, es, fr, fr-CA, de (nessa ordem).
Termos genéricos (Salvar, Filtrar, Buscar, Exportar, Atualizar, Idioma)
seguem as traduções limpas do catálogo do KaptureBOARD.
"""
from __future__ import annotations

IDIOMAS = {
    "pt-BR": "Português (Brasil)",
    "en": "English",
    "es": "Español",
    "fr": "Français (France)",
    "fr-CA": "Français (Canada)",
    "de": "Deutsch",
}
PADRAO = "pt-BR"
_ORDEM = tuple(IDIOMAS)

# chave: (pt-BR, en, es, fr, fr-CA, de)
CATALOGO: dict[str, tuple[str, ...]] = {
    "nav.label": ("Página", "Page", "Página", "Page", "Page", "Seite"),
    "nav.conversas": ("Conversas", "Conversations", "Conversaciones", "Conversations", "Conversations", "Unterhaltungen"),
    "nav.ficha": ("Ficha técnica", "Technical sheet", "Ficha técnica", "Fiche technique", "Fiche technique", "Technisches Datenblatt"),
    "idioma.label": ("Idioma", "Language", "Idioma", "Langue", "Langue", "Sprache"),
    "tema.aparencia": ("Aparência", "Appearance", "Apariencia", "Apparence", "Apparence", "Erscheinung"),
    "tema.label": ("Tema", "Theme", "Tema", "Thème", "Thème", "Thema"),
    "folder.titulo": ("Folder", "Folder", "Carpeta", "Dossier", "Dossier", "Ordner"),
    "folder.filtrar": ("Filtrar pasta", "Filter folder", "Filtrar carpeta", "Filtrer le dossier", "Filtrer le dossier", "Ordner filtern"),
    "folder.filtrar_placeholder": ("Nome do projeto ou caminho", "Project name or path", "Nombre del proyecto o ruta", "Nom du projet ou chemin", "Nom du projet ou chemin", "Projektname oder Pfad"),
    "folder.temporarias": ("Incluir pastas temporárias", "Include temporary folders", "Incluir carpetas temporales", "Inclure les dossiers temporaires", "Inclure les dossiers temporaires", "Temporäre Ordner einbeziehen"),
    "folder.vazio": (
        "Nenhuma tela de agente encontrada nas pastas do Cursor deste computador.",
        "No agent sessions found in the Cursor folders on this computer.",
        "No se encontraron sesiones del agente en las carpetas de Cursor de este equipo.",
        "Aucune session d'agent trouvée dans les dossiers Cursor de cet ordinateur.",
        "Aucune session d'agent trouvée dans les dossiers Cursor de cet ordinateur.",
        "In den Cursor-Ordnern auf diesem Computer wurden keine Agentensitzungen gefunden.",
    ),
    "btn.atualizar": ("Atualizar", "Refresh", "Actualizar", "Actualiser", "Actualiser", "Aktualisieren"),
    "app.ajuda": (
        "Escolha a pasta que corresponde ao Folder aberto no Cursor.",
        "Choose the folder that matches the Folder open in Cursor.",
        "Elija la carpeta que corresponde al Folder abierto en Cursor.",
        "Choisissez le dossier correspondant au Folder ouvert dans Cursor.",
        "Choisissez le dossier correspondant au Folder ouvert dans Cursor.",
        "Wähle den Ordner, der dem in Cursor geöffneten Folder entspricht.",
    ),
    "app.lista_ajuda": (
        "A lista mostra cada tela de agente, os comandos e o comentário final, lidos neste computador.",
        "The list shows each agent session, its commands and the final comment, read from this computer.",
        "La lista muestra cada sesión del agente, sus comandos y el comentario final, leídos de este equipo.",
        "La liste affiche chaque session d'agent, ses commandes et le commentaire final, lus sur cet ordinateur.",
        "La liste affiche chaque session d'agent, ses commandes et le commentaire final, lus sur cet ordinateur.",
        "Die Liste zeigt jede Agentensitzung, ihre Befehle und den Abschlusskommentar, gelesen von diesem Computer.",
    ),
    "busca.pasta": ("Buscar na pasta", "Search in folder", "Buscar en la carpeta", "Rechercher dans le dossier", "Rechercher dans le dossier", "Im Ordner suchen"),
    "busca.placeholder": ("Pedido, comando ou comentário", "Request, command or comment", "Pedido, comando o comentario", "Demande, commande ou commentaire", "Demande, commande ou commentaire", "Anfrage, Befehl oder Kommentar"),
    "filtro.favoritas": ("Somente favoritas", "Favorites only", "Solo favoritas", "Favoris uniquement", "Favoris uniquement", "Nur Favoriten"),
    "filtro.tag": ("Tag", "Tag", "Etiqueta", "Tag", "Tag", "Tag"),
    "filtro.todas": ("(todas)", "(all)", "(todas)", "(toutes)", "(toutes)", "(alle)"),
    "lista.titulo": ("Conversas ({n})", "Conversations ({n})", "Conversaciones ({n})", "Conversations ({n})", "Conversations ({n})", "Unterhaltungen ({n})"),
    "lista.vazia": ("Nenhuma tela nesta pasta.", "No sessions in this folder.", "No hay sesiones en esta carpeta.", "Aucune session dans ce dossier.", "Aucune session dans ce dossier.", "Keine Sitzungen in diesem Ordner."),
    "lista.sem_pedido": ("(sem pedido)", "(no request)", "(sin pedido)", "(sans demande)", "(sans demande)", "(ohne Anfrage)"),
    "lista.pedidos": ("{n} pedidos", "{n} requests", "{n} pedidos", "{n} demandes", "{n} demandes", "{n} Anfragen"),
    "lista.comandos": ("{n} comandos", "{n} commands", "{n} comandos", "{n} commandes", "{n} commandes", "{n} Befehle"),
    "lista.comentarios": ("{n} comentários", "{n} comments", "{n} comentarios", "{n} commentaires", "{n} commentaires", "{n} Kommentare"),
    "detalhe.titulo": ("Conversa", "Conversation", "Conversación", "Conversation", "Conversation", "Unterhaltung"),
    "detalhe.escolha": (
        "Escolha uma tela para ver pedidos, comandos e comentários.",
        "Choose a session to see requests, commands and comments.",
        "Elija una sesión para ver pedidos, comandos y comentarios.",
        "Choisissez une session pour voir les demandes, commandes et commentaires.",
        "Choisissez une session pour voir les demandes, commandes et commentaires.",
        "Wähle eine Sitzung, um Anfragen, Befehle und Kommentare zu sehen.",
    ),
    "detalhe.agentes": ("{n} agente(s) auxiliar(es)", "{n} helper agent(s)", "{n} agente(s) auxiliar(es)", "{n} agent(s) auxiliaire(s)", "{n} agent(s) auxiliaire(s)", "{n} Hilfsagent(en)"),
    "detalhe.final": ("Comentário final", "Final comment", "Comentario final", "Commentaire final", "Commentaire final", "Abschlusskommentar"),
    "detalhe.filtro": ("Filtro", "Filter", "Filtro", "Filtre", "Filtre", "Filter"),
    "vista.conversa": ("Conversa", "Conversation", "Conversación", "Conversation", "Conversation", "Unterhaltung"),
    "vista.pedido": ("Pedido", "Request", "Pedido", "Demande", "Demande", "Anfrage"),
    "vista.comentario": ("Comentário", "Comment", "Comentario", "Commentaire", "Commentaire", "Kommentar"),
    "vista.comando": ("Comando", "Command", "Comando", "Commande", "Commande", "Befehl"),
    "detalhe.ferramentas": ("Mostrar leituras e buscas", "Show reads and searches", "Mostrar lecturas y búsquedas", "Afficher les lectures et recherches", "Afficher les lectures et recherches", "Lesevorgänge und Suchen anzeigen"),
    "detalhe.omitidos_tela": (
        "Trechos do meio foram omitidos na tela.",
        "Middle parts were left out on screen.",
        "Se omitieron partes intermedias en pantalla.",
        "Des passages du milieu ont été omis à l'écran.",
        "Des passages du milieu ont été omis à l'écran.",
        "Mittlere Abschnitte wurden auf dem Bildschirm ausgelassen.",
    ),
    "detalhe.omitidos_arquivo": (
        "O arquivo exportado leva a conversa inteira, e o comentário final permanece acima.",
        "The exported file contains the whole conversation, and the final comment stays above.",
        "El archivo exportado incluye la conversación completa, y el comentario final permanece arriba.",
        "Le fichier exporté contient toute la conversation, et le commentaire final reste au-dessus.",
        "Le fichier exporté contient toute la conversation, et le commentaire final reste au-dessus.",
        "Die exportierte Datei enthält die ganze Unterhaltung, und der Abschlusskommentar bleibt oben.",
    ),
    "export.conversa": ("Exportar esta conversa", "Export this conversation", "Exportar esta conversación", "Exporter cette conversation", "Exporter cette conversation", "Diese Unterhaltung exportieren"),
    "export.preparando": ("Preparando o arquivo…", "Preparing the file…", "Preparando el archivo…", "Préparation du fichier…", "Préparation du fichier…", "Datei wird vorbereitet…"),
    "export.pasta": ("Exportar pasta inteira", "Export whole folder", "Exportar carpeta completa", "Exporter tout le dossier", "Exporter tout le dossier", "Ganzen Ordner exportieren"),
    "export.formatos": ("Formatos", "Formats", "Formatos", "Formats", "Formats", "Formate"),
    "export.so_novas": ("Só conversas novas ou alteradas", "Only new or changed conversations", "Solo conversaciones nuevas o modificadas", "Seulement les conversations nouvelles ou modifiées", "Seulement les conversations nouvelles ou modifiées", "Nur neue oder geänderte Unterhaltungen"),
    "export.preparar_zip": ("Preparar ZIP", "Prepare ZIP", "Preparar ZIP", "Préparer le ZIP", "Préparer le ZIP", "ZIP vorbereiten"),
    "export.preparando_zip": ("Preparando o ZIP…", "Preparing the ZIP…", "Preparando el ZIP…", "Préparation du ZIP…", "Préparation du ZIP…", "ZIP wird vorbereitet…"),
    "export.arquivos_zip": ("{n} arquivo(s) no ZIP.", "{n} file(s) in the ZIP.", "{n} archivo(s) en el ZIP.", "{n} fichier(s) dans le ZIP.", "{n} fichier(s) dans le ZIP.", "{n} Datei(en) im ZIP."),
    "export.baixar_zip": ("Baixar ZIP", "Download ZIP", "Descargar ZIP", "Télécharger le ZIP", "Télécharger le ZIP", "ZIP herunterladen"),
    "org.titulo": ("Organização", "Organization", "Organización", "Organisation", "Organisation", "Organisation"),
    "org.favorita": ("★ Favorita", "★ Favorite", "★ Favorita", "★ Favori", "★ Favori", "★ Favorit"),
    "org.favoritar": ("☆ Favoritar", "☆ Mark as favorite", "☆ Marcar como favorita", "☆ Mettre en favori", "☆ Mettre en favori", "☆ Als Favorit markieren"),
    "org.tags": ("Tags (separadas por vírgula)", "Tags (comma-separated)", "Etiquetas (separadas por coma)", "Tags (séparées par des virgules)", "Tags (séparées par des virgules)", "Tags (durch Kommas getrennt)"),
    "org.salvar_tags": ("Salvar tags", "Save tags", "Guardar etiquetas", "Enregistrer les tags", "Enregistrer les tags", "Tags speichern"),
    "ficha.titulo": ("Ficha técnica", "Technical sheet", "Ficha técnica", "Fiche technique", "Fiche technique", "Technisches Datenblatt"),
    "ficha.badge": ("Sistema · somente leitura", "System · read-only", "Sistema · solo lectura", "Système · lecture seule", "Système · lecture seule", "System · nur lesen"),
    "ficha.subtitulo": (
        "Informações do aplicativo, sem senhas nem conteúdo das conversas.",
        "Application information, without passwords or conversation content.",
        "Información de la aplicación, sin contraseñas ni contenido de las conversaciones.",
        "Informations sur l'application, sans mots de passe ni contenu des conversations.",
        "Informations sur l'application, sans mots de passe ni contenu des conversations.",
        "Informationen zur Anwendung, ohne Passwörter oder Inhalte der Unterhaltungen.",
    ),
    "ficha.identidade": ("Identidade", "Identity", "Identidad", "Identité", "Identité", "Identität"),
    "ficha.stack": ("Stack", "Stack", "Stack", "Stack", "Stack", "Stack"),
    "ficha.dados": ("Dados e runtime", "Data and runtime", "Datos y ejecución", "Données et exécution", "Données et exécution", "Daten und Laufzeit"),
    "ficha.integracoes": ("Integrações", "Integrations", "Integraciones", "Intégrations", "Intégrations", "Integrationen"),
    "ficha.fronteiras": ("Fronteiras", "Boundaries", "Límites", "Limites", "Limites", "Grenzen"),
    "ficha.operacao": ("Operação", "Operation", "Operación", "Fonctionnement", "Fonctionnement", "Betrieb"),
    "ficha.campo.nome": ("Nome", "Name", "Nombre", "Nom", "Nom", "Name"),
    "ficha.campo.descricao": ("Descrição", "Description", "Descripción", "Description", "Description", "Beschreibung"),
    "ficha.campo.licenca": ("Licença", "License", "Licencia", "Licence", "Licence", "Lizenz"),
    "ficha.campo.repositorio": ("Repositório", "Repository", "Repositorio", "Dépôt", "Dépôt", "Repository"),
    "ficha.campo.idiomas": ("Idiomas disponíveis", "Available languages", "Idiomas disponibles", "Langues disponibles", "Langues disponibles", "Verfügbare Sprachen"),
    "ficha.campo.componentes": ("Componentes", "Components", "Componentes", "Composants", "Composants", "Komponenten"),
    "ficha.campo.pasta_app": ("Pasta do app", "App folder", "Carpeta de la app", "Dossier de l'application", "Dossier de l'application", "App-Ordner"),
    "ficha.campo.origem": ("Origem das conversas", "Conversation source", "Origen de las conversaciones", "Source des conversations", "Source des conversations", "Quelle der Unterhaltungen"),
    "ficha.campo.arquivos": ("Arquivos locais", "Local files", "Archivos locales", "Fichiers locaux", "Fichiers locaux", "Lokale Dateien"),
    "ficha.valor.descricao": (
        "Consulta local das conversas do agente do Cursor, com exportação para PDF, HTML e Markdown.",
        "Local viewer for Cursor agent conversations, with export to PDF, HTML and Markdown.",
        "Consulta local de las conversaciones del agente de Cursor, con exportación a PDF, HTML y Markdown.",
        "Consultation locale des conversations de l'agent Cursor, avec export en PDF, HTML et Markdown.",
        "Consultation locale des conversations de l'agent Cursor, avec export en PDF, HTML et Markdown.",
        "Lokale Ansicht der Cursor-Agent-Unterhaltungen mit Export als PDF, HTML und Markdown.",
    ),
    "ficha.valor.integracoes": (
        "Nenhuma. Não usa API, login nem serviço externo.",
        "None. It uses no API, login or external service.",
        "Ninguna. No usa API, inicio de sesión ni servicio externo.",
        "Aucune. Pas d'API, de connexion ni de service externe.",
        "Aucune. Pas d'API, de connexion ni de service externe.",
        "Keine. Keine API, kein Login und kein externer Dienst.",
    ),
    "ficha.valor.fronteiras": (
        "Não altera as conversas do Cursor. Os arquivos exportados passam pela redação de segredos.",
        "It does not change Cursor conversations. Exported files go through secret redaction.",
        "No modifica las conversaciones de Cursor. Los archivos exportados pasan por la redacción de secretos.",
        "Ne modifie pas les conversations Cursor. Les fichiers exportés passent par le masquage des secrets.",
        "Ne modifie pas les conversations Cursor. Les fichiers exportés passent par le masquage des secrets.",
        "Verändert die Cursor-Unterhaltungen nicht. Exportierte Dateien durchlaufen die Schwärzung von Geheimnissen.",
    ),
    "ficha.valor.operacao": (
        "Iniciar: streamlit run app.py, dentro da pasta do app. Porta padrão: 8501. Testes: python -m unittest discover -p \"test_*.py\".",
        "Start: streamlit run app.py inside the app folder. Default port: 8501. Tests: python -m unittest discover -p \"test_*.py\".",
        "Iniciar: streamlit run app.py dentro de la carpeta de la app. Puerto predeterminado: 8501. Pruebas: python -m unittest discover -p \"test_*.py\".",
        "Démarrer : streamlit run app.py dans le dossier de l'application. Port par défaut : 8501. Tests : python -m unittest discover -p \"test_*.py\".",
        "Démarrer : streamlit run app.py dans le dossier de l'application. Port par défaut : 8501. Tests : python -m unittest discover -p \"test_*.py\".",
        "Starten: streamlit run app.py im App-Ordner. Standardport: 8501. Tests: python -m unittest discover -p \"test_*.py\".",
    ),
    'ficha.valor.origem': ('Pasta de projetos do Cursor indicada em CURSOR2NOTES_PROJECTS_ROOT (padrão ~/.cursor/projects). Somente leitura.', 'Cursor projects folder set in CURSOR2NOTES_PROJECTS_ROOT (default ~/.cursor/projects). Read-only.', 'Carpeta de proyectos de Cursor indicada en CURSOR2NOTES_PROJECTS_ROOT (predeterminado ~/.cursor/projects). Solo lectura.', 'Dossier des projets Cursor indiqué dans CURSOR2NOTES_PROJECTS_ROOT (par défaut ~/.cursor/projects). Lecture seule.', 'Dossier des projets Cursor indiqué dans CURSOR2NOTES_PROJECTS_ROOT (par défaut ~/.cursor/projects). Lecture seule.', 'Cursor-Projektordner aus CURSOR2NOTES_PROJECTS_ROOT (Standard ~/.cursor/projects). Nur lesend.'),
    'ficha.valor.arquivos': ('metadados.json (favoritas, tags, exportações), redacao.json, export.json, temas.json, assets/logo.png. Ficam na pasta do app e não vão para o Git.', 'metadados.json (favorites, tags, exports), redacao.json, export.json, temas.json, assets/logo.png. They stay in the app folder and are not committed to Git.', 'metadados.json (favoritas, etiquetas, exportaciones), redacao.json, export.json, temas.json, assets/logo.png. Quedan en la carpeta de la app y no van a Git.', "metadados.json (favoris, tags, exports), redacao.json, export.json, temas.json, assets/logo.png. Ils restent dans le dossier de l'application et ne vont pas dans Git.", "metadados.json (favoris, tags, exports), redacao.json, export.json, temas.json, assets/logo.png. Ils restent dans le dossier de l'application et ne vont pas dans Git.", 'metadados.json (Favoriten, Tags, Exporte), redacao.json, export.json, temas.json, assets/logo.png. Sie bleiben im App-Ordner und werden nicht in Git übernommen.'),
}


def texto(idioma: str, chave: str, **kwargs) -> str:
    """Devolve o texto da chave no idioma. Sem tradução, usa o pt-BR."""
    posicao = _ORDEM.index(idioma) if idioma in _ORDEM else 0
    valores = CATALOGO.get(chave)
    if valores is None:
        return chave
    valor = valores[posicao] or valores[0]
    return valor.format(**kwargs) if kwargs else valor
