"""Leitores locais das conversas: Cursor, Claude Code, Cowork, Claude, VS Code e Antigravity."""
from __future__ import annotations

import antigravity_sessions as antigravity
import claude_app_sessions as claude_app
import claude_code_sessions as claude
import claude_desktop_sessions as desktop
import cursor_agent_sessions as cursor
import vscode_sessions as vscode

FONTES = {
    "cursor": cursor,
    "claude": claude,
    "desktop": desktop,
    "claude_app": claude_app,
    "vscode": vscode,
    "antigravity": antigravity,
}


def fonte(nome: str):
    return FONTES.get(nome, cursor)
