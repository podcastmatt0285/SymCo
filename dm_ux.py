"""
dm_ux.py - Direct Message UI and WebSocket Endpoint

P2P direct messaging UI that mirrors the Chatrooms layout.
- Left sidebar: avatar, Upload Pic, player search bar, recent chats list
- Main area: conversation messages, typing indicator, input bar
- WebSocket for real-time messaging
"""

import json
import base64
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from dm import (
    dm_manager, MAX_DM_LENGTH, DM_UPLOAD_BYTES,
    make_conversation_id, get_or_create_conversation,
    get_dm_messages, save_dm, get_player_conversations,
    search_players,
)
from chat import (
    ADMIN_PLAYER_IDS, DEFAULT_BAN_WORDS, MAX_UPLOAD_BYTES,
    get_user_ban_words, initialize_default_ban_words,
    save_avatar, get_avatar, set_user_ban_words,
)

router = APIRouter()


# ==========================
# AUTH HELPERS
# ==========================

def require_auth(session_token):
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception as e:
        print(f"[DM UX] Auth check failed: {e}")
        return RedirectResponse(url="/login", status_code=303)


def validate_session_ws(session_token):
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        return player
    except Exception:
        return None


def get_player_name(player_id: int) -> str:
    try:
        import auth
        db = auth.get_db()
        player = db.query(auth.Player).filter(auth.Player.id == player_id).first()
        name = player.business_name if player else "Unknown"
        db.close()
        return name
    except Exception:
        return "Unknown"


# ==========================
# SHELL (DM-specific, mirrors chat_shell)
# ==========================

def dm_shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    from ux import get_player_lien_info

    lien_info = get_player_lien_info(player_id) if player_id else {"has_lien": False, "total_owed": 0.0, "status": "ok"}
    lien_html = ""
    if lien_info["has_lien"]:
        status_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
        lien_color = status_colors.get(lien_info["status"], "#64748b")
        status_icons = {"critical": "\U0001f6a8", "warning": "\u26a0\ufe0f", "ok": "\U0001f4cb"}
        lien_icon = status_icons.get(lien_info["status"], "\U0001f4cb")
        lien_html = f'''
        <a href="/liens" style="color: {lien_color}; margin-right: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; font-size: 0.85rem;">
            <span>{lien_icon}</span>
            <span style="font-weight: 500;">LIEN: ${lien_info["total_owed"]:,.0f}</span>
        </a>
        '''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - SymCo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                height: 100vh;
                height: 100dvh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}
            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}

            .header {{
                border-bottom: 1px solid #1e293b;
                padding: 8px 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-shrink: 0;
                gap: 8px;
                background: #020617;
                z-index: 10;
            }}
            .brand {{ font-weight: bold; color: #38bdf8; font-size: 1rem; }}
            .header-left {{
                display: flex; align-items: center; gap: 10px;
            }}
            .header-right {{
                display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
            }}
            .balance {{ color: #22c55e; font-size: 0.75rem; white-space: nowrap; }}
            .hamburger {{
                display: none;
                background: none;
                border: 1px solid #334155;
                color: #94a3b8;
                font-size: 1.2rem;
                padding: 4px 8px;
                cursor: pointer;
                border-radius: 4px;
                line-height: 1;
            }}
            .hamburger:hover {{ background: #1e293b; color: #e5e7eb; }}

            .chat-layout {{
                flex: 1;
                display: flex;
                overflow: hidden;
                position: relative;
            }}

            /* SIDEBAR */
            .chat-sidebar {{
                width: 240px;
                min-width: 240px;
                background: #0a0f1e;
                border-right: 1px solid #1e293b;
                display: flex;
                flex-direction: column;
                overflow-y: auto;
                z-index: 50;
            }}
            .sidebar-section {{
                padding: 12px;
                border-bottom: 1px solid #1e293b;
            }}
            .sidebar-section h4 {{
                font-size: 0.7rem;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 8px;
            }}

            /* AVATAR SECTION */
            .avatar-section {{ text-align: center; }}
            .avatar-preview {{
                width: 56px; height: 56px;
                border-radius: 50%;
                border: 2px solid #1e293b;
                object-fit: cover;
                margin: 0 auto 8px;
                display: block;
                background: #1e293b;
            }}
            .avatar-letter {{
                width: 56px; height: 56px;
                border-radius: 50%;
                border: 2px solid #1e293b;
                background: #1e293b;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 8px;
                font-size: 1.4rem;
                font-weight: bold;
                color: #38bdf8;
            }}
            .sidebar-btn {{
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                padding: 4px 10px;
                font-size: 0.7rem;
                font-family: inherit;
                cursor: pointer;
                border-radius: 3px;
                width: 100%;
                margin-top: 4px;
            }}
            .sidebar-btn:hover {{ background: #334155; color: #e5e7eb; }}

            /* SEARCH */
            .search-input {{
                width: 100%;
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 6px 10px;
                font-family: inherit;
                font-size: 0.78rem;
                border-radius: 4px;
                outline: none;
                margin-top: 6px;
            }}
            .search-input:focus {{ border-color: #c084fc; }}
            .search-input::placeholder {{ color: #475569; }}
            .search-results {{
                max-height: 160px;
                overflow-y: auto;
                margin-top: 4px;
            }}
            .search-result-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 8px;
                cursor: pointer;
                border-radius: 4px;
                font-size: 0.78rem;
                color: #94a3b8;
                transition: background 0.15s;
            }}
            .search-result-item:hover {{ background: #1e293b; color: #e5e7eb; }}
            .search-result-letter {{
                width: 24px; height: 24px;
                border-radius: 50%;
                background: #1e293b;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.65rem;
                font-weight: bold;
                flex-shrink: 0;
            }}

            /* CONVERSATION LIST */
            .conv-btn {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 10px;
                border: none;
                background: transparent;
                color: #94a3b8;
                font-family: inherit;
                font-size: 0.78rem;
                cursor: pointer;
                width: 100%;
                text-align: left;
                border-radius: 4px;
                transition: background 0.15s;
                position: relative;
            }}
            .conv-btn:hover {{ background: #1e293b; color: #e5e7eb; }}
            .conv-btn.active {{ background: #1e293b; color: #c084fc; font-weight: bold; }}
            .conv-btn .conv-avatar {{
                width: 28px; height: 28px;
                border-radius: 50%;
                background: #1e293b;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.7rem;
                font-weight: bold;
                flex-shrink: 0;
            }}
            .conv-btn .conv-info {{ flex: 1; overflow: hidden; min-width: 0; }}
            .conv-btn .conv-name {{ display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
            .conv-btn .conv-preview {{
                display: block; font-size: 0.65rem; color: #475569;
                overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                margin-top: 1px;
            }}
            .conv-btn .unread-badge {{
                background: #c084fc;
                color: #020617;
                font-size: 0.6rem;
                padding: 1px 5px;
                border-radius: 8px;
                min-width: 16px;
                text-align: center;
                display: none;
                flex-shrink: 0;
            }}
            .conv-btn .unread-badge.show {{ display: inline-block; }}

            /* MAIN CHAT AREA */
            .chat-main {{
                flex: 1;
                display: flex;
                flex-direction: column;
                min-width: 0;
            }}
            .chat-header {{
                padding: 8px 12px;
                border-bottom: 1px solid #1e293b;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0a0f1e;
                flex-shrink: 0;
            }}
            .chat-header h3 {{
                font-size: 0.9rem;
                color: #e5e7eb;
                margin: 0;
            }}
            .chat-header .online-status {{
                font-size: 0.7rem;
                color: #64748b;
            }}
            .chat-messages {{
                flex: 1;
                overflow-y: auto;
                padding: 8px 12px;
                display: flex;
                flex-direction: column;
                gap: 2px;
                -webkit-overflow-scrolling: touch;
            }}
            .chat-msg {{
                display: flex;
                gap: 8px;
                padding: 5px 0;
            }}
            .chat-msg .msg-avatar {{
                width: 30px; height: 30px;
                border-radius: 50%;
                flex-shrink: 0;
                object-fit: cover;
                background: #1e293b;
                cursor: pointer;
            }}
            .chat-msg .msg-avatar-letter {{
                width: 30px; height: 30px;
                border-radius: 50%;
                flex-shrink: 0;
                background: #1e293b;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.7rem;
                font-weight: bold;
                color: #64748b;
                cursor: pointer;
            }}
            .chat-msg .msg-body {{ flex: 1; min-width: 0; }}
            .chat-msg .msg-header {{
                display: flex;
                align-items: baseline;
                gap: 6px;
                margin-bottom: 1px;
            }}
            .chat-msg .msg-name {{
                font-weight: bold;
                font-size: 0.78rem;
                color: #c084fc;
                cursor: pointer;
            }}
            .chat-msg .msg-name:hover {{ text-decoration: underline; }}
            .chat-msg .msg-time {{
                font-size: 0.6rem;
                color: #475569;
            }}
            .chat-msg .msg-text {{
                font-size: 0.8rem;
                color: #cbd5e1;
                word-break: break-word;
                line-height: 1.35;
            }}
            .chat-msg.system-msg {{ justify-content: center; padding: 3px 0; }}
            .chat-msg.system-msg .msg-text {{
                color: #64748b; font-size: 0.72rem; font-style: italic; text-align: center;
            }}

            .typing-indicator {{
                padding: 3px 12px 6px;
                font-size: 0.68rem;
                color: #64748b;
                font-style: italic;
                min-height: 20px;
                flex-shrink: 0;
            }}

            /* INPUT BAR */
            .chat-input-bar {{
                display: flex;
                gap: 6px;
                padding: 8px 12px;
                border-top: 1px solid #1e293b;
                background: #0a0f1e;
                align-items: flex-end;
                flex-shrink: 0;
            }}
            .chat-input-bar input[type="text"] {{
                flex: 1;
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 8px 10px;
                font-family: inherit;
                font-size: 0.85rem;
                border-radius: 4px;
                outline: none;
                min-width: 0;
            }}
            .chat-input-bar input[type="text"]:focus {{ border-color: #c084fc; }}
            .chat-input-bar button {{
                background: #c084fc;
                color: #020617;
                border: none;
                padding: 8px 14px;
                font-family: inherit;
                font-size: 0.82rem;
                cursor: pointer;
                border-radius: 4px;
                font-weight: bold;
                flex-shrink: 0;
            }}
            .chat-input-bar button:hover {{ background: #d8b4fe; }}
            .emoji-toggle {{
                background: #1e293b !important;
                color: #94a3b8 !important;
                padding: 8px 10px !important;
                font-size: 1rem !important;
            }}
            .emoji-toggle:hover {{ background: #334155 !important; color: #e5e7eb !important; }}

            /* EMOJI PICKER */
            .emoji-picker {{
                display: none;
                position: absolute;
                bottom: 56px;
                right: 12px;
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 10px;
                width: 260px;
                max-height: 200px;
                overflow-y: auto;
                z-index: 100;
                box-shadow: 0 -4px 16px rgba(0,0,0,0.5);
            }}
            .emoji-picker.show {{ display: block; }}
            .emoji-picker span {{
                display: inline-block;
                padding: 3px 4px;
                cursor: pointer;
                font-size: 1.15rem;
                border-radius: 3px;
            }}
            .emoji-picker span:hover {{ background: #1e293b; }}

            /* PLACEHOLDER */
            .dm-placeholder {{
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #475569;
                font-size: 0.9rem;
                text-align: center;
                padding: 20px;
            }}

            /* SIDEBAR OVERLAY BACKDROP */
            .sidebar-backdrop {{
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.5);
                z-index: 40;
            }}
            .sidebar-backdrop.show {{ display: block; }}

            /* RESPONSIVE - MOBILE */
            @media (max-width: 640px) {{
                .hamburger {{ display: block; }}
                .header-right a {{ font-size: 0.72rem; }}
                .balance {{ font-size: 0.68rem; }}

                .chat-sidebar {{
                    position: fixed;
                    top: 0; left: 0; bottom: 0;
                    width: 260px;
                    transform: translateX(-100%);
                    transition: transform 0.25s ease;
                    z-index: 50;
                }}
                .chat-sidebar.open {{
                    transform: translateX(0);
                }}

                .chat-messages {{ padding: 6px 8px; }}
                .chat-input-bar {{ padding: 6px 8px; }}
                .chat-input-bar input[type="text"] {{ font-size: 16px; padding: 8px; }}
                .emoji-picker {{ width: 220px; right: 8px; bottom: 52px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <button class="hamburger" id="hamburger-btn" onclick="toggleSidebar()">&#9776;</button>
                <span class="brand">SymCo</span>
                <span style="color: #c084fc; font-size: 0.8rem;">Direct Messages</span>
            </div>
            <div class="header-right">
                {lien_html}
                <span class="balance">$ {balance:,.2f}</span>
                <a href="/p2p/dashboard" style="color: #94a3b8; font-size: 0.8rem;">P2P</a>
                <a href="/chat" style="color: #c084fc; font-size: 0.8rem;">Chat</a>
                <a href="/dashboard" style="color: #94a3b8; font-size: 0.8rem;">Dashboard</a>
                <a href="/api/logout" style="color: #ef4444; font-size: 0.8rem;">Logout</a>
            </div>
        </div>
        {body}
    </body>
    </html>
    """


# ==========================
# DM PAGE ROUTE
# ==========================

@router.get("/p2p/dms", response_class=HTMLResponse)
def dm_page(session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    initialize_default_ban_words(player.id)
    ban_words = get_user_ban_words(player.id)
    avatar = get_avatar(player.id)

    conversations = get_player_conversations(player.id)

    # Resolve other player names for conversations
    conv_list = []
    for conv in conversations:
        other_id = conv["player2_id"] if conv["player1_id"] == player.id else conv["player1_id"]
        other_name = get_player_name(other_id)
        conv_list.append({
            "id": conv["id"],
            "other_id": other_id,
            "other_name": other_name,
            "last_message_at": conv["last_message_at"],
            "last_message_preview": conv["last_message_preview"],
        })

    conv_json = json.dumps(conv_list)
    ban_words_json = json.dumps(ban_words)
    avatar_json = json.dumps(avatar) if avatar else "null"
    admin_ids_json = json.dumps(list(ADMIN_PLAYER_IDS))

    emojis = "\U0001f600\U0001f602\U0001f923\U0001f60a\U0001f60e\U0001f914\U0001f622\U0001f621\U0001f92e\U0001f973\U0001f389\U0001f525\U0001f4b0\U0001f4c8\U0001f4c9\U0001f3ed\U0001f6e2\ufe0f\u26a1\U0001f3d7\ufe0f\U0001f33e\U0001f48e\U0001f91d\U0001f44d\U0001f44e\u2764\ufe0f\U0001f480\U0001f680\U0001f4ac\u26a0\ufe0f\U0001f41b\u2705\u274c\U0001f3d9\ufe0f\U0001f3db\ufe0f\U0001f4ca\u2753\U0001f3af\U0001f6e1\ufe0f\u2694\ufe0f\U0001fa99\U0001f4b8\U0001f3e6\U0001f4cb"

    body = f"""
    <!-- Sidebar backdrop for mobile -->
    <div class="sidebar-backdrop" id="sidebar-backdrop" onclick="closeSidebar()"></div>

    <div class="chat-layout">
        <!-- SIDEBAR -->
        <div class="chat-sidebar" id="chat-sidebar">
            <div class="sidebar-section avatar-section">
                <div id="avatar-display">
                    <div class="avatar-letter" id="avatar-letter">{player.business_name[0].upper()}</div>
                </div>
                <div style="font-size: 0.75rem; color: #e5e7eb; margin-bottom: 6px; word-break: break-all;">{player.business_name}</div>
                <input type="file" id="avatar-input" accept="image/*" style="display:none;">
                <button class="sidebar-btn" onclick="document.getElementById('avatar-input').click()">Upload Pic</button>
                <input type="text" class="search-input" id="player-search" placeholder="Search player to DM..." autocomplete="off">
                <div class="search-results" id="search-results"></div>
            </div>

            <div class="sidebar-section" style="flex: 1;">
                <h4>Recent Chats</h4>
                <div id="conv-list"></div>
            </div>

            <div class="sidebar-section">
                <button class="sidebar-btn" onclick="openBanModal()">Word Filter Settings</button>
            </div>
        </div>

        <!-- MAIN CHAT -->
        <div class="chat-main" style="position: relative;">
            <div class="chat-header">
                <h3 id="conv-title">Direct Messages</h3>
                <span class="online-status" id="online-status"></span>
            </div>

            <div id="dm-placeholder" class="dm-placeholder">
                Search for a player to start a conversation.
            </div>

            <div class="chat-messages" id="messages" style="display: none;"></div>
            <div class="typing-indicator" id="typing-indicator" style="display: none;"></div>

            <div id="input-section" style="display: none;">
                <div class="chat-input-bar">
                    <input type="text" id="msg-input" placeholder="Type a message..." maxlength="{MAX_DM_LENGTH}" autocomplete="off">
                    <button class="emoji-toggle" onclick="toggleEmoji()" title="Emoji">\U0001f600</button>
                    <button id="send-btn" onclick="sendMessage()">Send</button>
                </div>
            </div>

            <!-- Emoji Picker -->
            <div class="emoji-picker" id="emoji-picker">
                {"".join(f'<span onclick="insertEmoji(this.textContent)">{e}</span>' for e in emojis)}
            </div>
        </div>
    </div>

    <!-- Ban Word Modal -->
    <div class="modal-overlay" id="ban-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.7); z-index:200; justify-content:center; align-items:center;">
        <div style="background:#0f172a; border:1px solid #1e293b; border-radius:6px; padding:20px; width:90%; max-width:500px; max-height:80vh; overflow-y:auto;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3 style="margin:0; font-size:1rem; color:#e5e7eb;">Word Filter</h3>
                <span style="cursor:pointer; color:#64748b; font-size:1.2rem;" onclick="closeBanModal()">&times;</span>
            </div>
            <p style="font-size:0.75rem; color:#64748b; margin-bottom:12px;">
                Filtered words appear as "****" in messages you see.
            </p>
            <div style="display:flex; gap:6px; margin-bottom:12px;">
                <input type="text" id="ban-word-input" placeholder="Add a word..." style="flex:1; background:#020617; border:1px solid #1e293b; color:#e5e7eb; padding:6px 10px; font-family:inherit; font-size:0.85rem; border-radius:4px;">
                <button style="background:#38bdf8; color:#020617; border:none; padding:6px 14px; font-family:inherit; font-size:0.8rem; cursor:pointer; border-radius:3px;" onclick="addBanWordFromInput()">Add</button>
            </div>
            <div style="display:flex; gap:6px; margin-bottom:12px;">
                <button style="background:#334155; color:#94a3b8; border:none; padding:6px 14px; font-family:inherit; font-size:0.8rem; cursor:pointer; border-radius:3px;" onclick="resetBanWords()">Reset to Defaults</button>
                <button style="background:#ef4444; color:#fff; border:none; padding:6px 14px; font-family:inherit; font-size:0.8rem; cursor:pointer; border-radius:3px;" onclick="clearAllBanWords()">Clear All</button>
            </div>
            <div id="ban-word-list" style="max-height:300px; overflow-y:auto;"></div>
        </div>
    </div>

    <script>
    // ===== STATE =====
    const PLAYER_ID = {player.id};
    const PLAYER_NAME = {json.dumps(player.business_name)};
    let conversations = {conv_json};
    let banWords = {ban_words_json};
    const ADMIN_IDS = {admin_ids_json};
    const DEFAULT_BAN_WORDS = {json.dumps(DEFAULT_BAN_WORDS)};

    let ws = null;
    let currentConvId = null;
    let currentOtherId = null;
    let currentOtherName = null;
    let reconnectDelay = 1000;
    let reconnectTimer = null;
    let typingTimeout = null;
    let isTyping = false;
    let unreadCounts = {{}};
    let avatarCache = {{}};
    let searchDebounce = null;

    // ===== MOBILE SIDEBAR =====
    function toggleSidebar() {{
        document.getElementById('chat-sidebar').classList.toggle('open');
        document.getElementById('sidebar-backdrop').classList.toggle('show');
    }}
    function closeSidebar() {{
        document.getElementById('chat-sidebar').classList.remove('open');
        document.getElementById('sidebar-backdrop').classList.remove('show');
    }}

    // ===== WEBSOCKET =====
    function connect() {{
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(proto + '://' + location.host + '/p2p/dms/ws');

        ws.onopen = () => {{
            reconnectDelay = 1000;
            // If we had an active conversation, rejoin it
            if (currentConvId) {{
                ws.send(JSON.stringify({{type: 'join', conversation_id: currentConvId, other_id: currentOtherId}}));
            }}
        }};

        ws.onmessage = (e) => {{
            const data = JSON.parse(e.data);
            handleWSMessage(data);
        }};

        ws.onclose = () => {{
            clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(() => {{
                reconnectDelay = Math.min(reconnectDelay * 2, 30000);
                connect();
            }}, reconnectDelay);
        }};

        ws.onerror = () => {{}};
    }}

    function handleWSMessage(data) {{
        switch (data.type) {{
            case 'message':
                if (data.conversation_id === currentConvId) {{
                    appendMessage(data);
                }} else {{
                    // Unread for a different conversation
                    unreadCounts[data.conversation_id] = (unreadCounts[data.conversation_id] || 0) + 1;
                    // Update conversation list preview
                    updateConvPreview(data.conversation_id, data.content, data.sender_name, data.other_id, data.other_name);
                    buildConvList();
                }}
                break;
            case 'history':
                renderHistory(data.conversation_id, data.messages);
                break;
            case 'typing':
                showTyping(data.conversation_id, data.names);
                break;
            case 'online_status':
                if (data.player_id === currentOtherId) {{
                    document.getElementById('online-status').innerHTML = data.online
                        ? '<span style="color:#22c55e;">&#9679; Online</span>'
                        : '<span style="color:#64748b;">&#9675; Offline</span>';
                }}
                break;
            case 'avatar_update':
                avatarCache[data.player_id] = data.avatar;
                refreshAvatarsInView(data.player_id);
                break;
            case 'conv_list':
                conversations = data.conversations;
                buildConvList();
                break;
            case 'search_results':
                renderSearchResults(data.results);
                break;
            case 'error':
                appendSystemMsg(data.message);
                break;
        }}
    }}

    // ===== CONVERSATION LIST =====
    function buildConvList() {{
        const container = document.getElementById('conv-list');
        container.innerHTML = '';
        if (conversations.length === 0) {{
            container.innerHTML = '<p style="color:#475569; font-size:0.72rem; padding:4px 0;">No recent chats.</p>';
            return;
        }}
        conversations.forEach(c => {{
            const btn = document.createElement('button');
            btn.className = 'conv-btn' + (c.id === currentConvId ? ' active' : '');
            btn.onclick = () => {{ openConversation(c.id, c.other_id, c.other_name); closeSidebar(); }};
            const letter = (c.other_name || '?')[0].toUpperCase();
            const hue = (c.other_id * 137) % 360;
            const unread = unreadCounts[c.id] || 0;
            const preview = c.last_message_preview || '';
            btn.innerHTML = `
                <div class="conv-avatar" style="color: hsl(${{hue}},60%,65%);">${{letter}}</div>
                <div class="conv-info">
                    <span class="conv-name">${{escapeHtml(c.other_name)}}</span>
                    <span class="conv-preview">${{escapeHtml(preview)}}</span>
                </div>
                <span class="unread-badge ${{unread > 0 ? 'show' : ''}}" id="unread-${{c.id}}">${{unread > 99 ? '99+' : unread}}</span>
            `;
            container.appendChild(btn);
        }});
    }}

    function updateConvPreview(convId, content, senderName, otherId, otherName) {{
        let found = false;
        for (let c of conversations) {{
            if (c.id === convId) {{
                c.last_message_preview = content.substring(0, 80);
                c.last_message_at = new Date().toISOString();
                found = true;
                break;
            }}
        }}
        if (!found && otherId && otherName) {{
            conversations.unshift({{
                id: convId,
                other_id: otherId,
                other_name: otherName,
                last_message_at: new Date().toISOString(),
                last_message_preview: content.substring(0, 80),
            }});
        }}
        // Sort by most recent
        conversations.sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at));
    }}

    function openConversation(convId, otherId, otherName) {{
        currentConvId = convId;
        currentOtherId = otherId;
        currentOtherName = otherName;
        unreadCounts[convId] = 0;

        document.getElementById('conv-title').textContent = otherName;
        document.getElementById('dm-placeholder').style.display = 'none';
        document.getElementById('messages').style.display = 'flex';
        document.getElementById('messages').innerHTML = '';
        document.getElementById('typing-indicator').style.display = 'block';
        document.getElementById('typing-indicator').textContent = '';
        document.getElementById('input-section').style.display = 'block';
        document.getElementById('online-status').textContent = '';

        buildConvList();

        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{type: 'join', conversation_id: convId, other_id: otherId}}));
        }}
    }}

    // ===== PLAYER SEARCH =====
    function handleSearch() {{
        const query = document.getElementById('player-search').value.trim();
        const container = document.getElementById('search-results');
        if (query.length === 0) {{
            container.innerHTML = '';
            return;
        }}
        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{type: 'search', query: query}}));
        }}
    }}

    function renderSearchResults(results) {{
        const container = document.getElementById('search-results');
        if (!results || results.length === 0) {{
            const query = document.getElementById('player-search').value.trim();
            container.innerHTML = query.length > 0 ? '<p style="color:#475569; font-size:0.7rem; padding:4px;">No players found.</p>' : '';
            return;
        }}
        container.innerHTML = '';
        results.forEach(p => {{
            const div = document.createElement('div');
            div.className = 'search-result-item';
            const letter = (p.name || '?')[0].toUpperCase();
            const hue = (p.id * 137) % 360;
            div.innerHTML = `
                <div class="search-result-letter" style="color: hsl(${{hue}},60%,65%);">${{letter}}</div>
                <span>${{escapeHtml(p.name)}}</span>
            `;
            div.onclick = () => {{
                startConversation(p.id, p.name);
                document.getElementById('player-search').value = '';
                container.innerHTML = '';
            }};
            container.appendChild(div);
        }});
    }}

    function startConversation(otherId, otherName) {{
        // Compute conversation ID (same as server: min:max)
        const a = Math.min(PLAYER_ID, otherId);
        const b = Math.max(PLAYER_ID, otherId);
        const convId = a + ':' + b;

        // Add to list if not already there
        let found = false;
        for (let c of conversations) {{
            if (c.id === convId) {{ found = true; break; }}
        }}
        if (!found) {{
            conversations.unshift({{
                id: convId,
                other_id: otherId,
                other_name: otherName,
                last_message_at: new Date().toISOString(),
                last_message_preview: '',
            }});
        }}

        openConversation(convId, otherId, otherName);
        closeSidebar();
    }}

    // ===== MESSAGES =====
    function renderHistory(convId, messages) {{
        if (convId !== currentConvId) return;
        const container = document.getElementById('messages');
        container.innerHTML = '';
        messages.forEach(m => appendMessage(m, false));
        requestAnimationFrame(() => {{ container.scrollTop = container.scrollHeight; }});
    }}

    function appendMessage(data, doScroll = true) {{
        if (data.conversation_id !== currentConvId) return;
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = 'chat-msg';

        const avatar = avatarCache[data.sender_id];
        let avatarHtml;
        if (avatar) {{
            avatarHtml = `<img class="msg-avatar" src="${{avatar}}" data-pid="${{data.sender_id}}">`;
        }} else {{
            const letter = (data.sender_name || '?')[0].toUpperCase();
            const hue = (data.sender_id * 137) % 360;
            avatarHtml = `<div class="msg-avatar-letter" style="color: hsl(${{hue}},60%,65%);" data-pid="${{data.sender_id}}">${{letter}}</div>`;
        }}

        const ts = new Date(data.timestamp);
        const timeStr = ts.toLocaleTimeString([], {{hour: '2-digit', minute: '2-digit'}});
        const filteredContent = filterBanWords(data.content);

        const nameColor = data.sender_id === PLAYER_ID ? '#22c55e' : '#c084fc';

        div.innerHTML = `
            ${{avatarHtml}}
            <div class="msg-body">
                <div class="msg-header">
                    <span class="msg-name" style="color: ${{nameColor}}">${{escapeHtml(data.sender_name)}}</span>
                    <span class="msg-time">${{timeStr}}</span>
                </div>
                <div class="msg-text">${{escapeHtml(filteredContent)}}</div>
            </div>
        `;
        container.appendChild(div);

        if (doScroll) scrollToBottom();
    }}

    function appendSystemMsg(text) {{
        const container = document.getElementById('messages');
        if (!container) return;
        const div = document.createElement('div');
        div.className = 'chat-msg system-msg';
        div.innerHTML = `<div class="msg-body"><div class="msg-text">${{escapeHtml(text)}}</div></div>`;
        container.appendChild(div);
        scrollToBottom();
    }}

    function scrollToBottom() {{
        const el = document.getElementById('messages');
        const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
        if (isNearBottom || el.children.length <= 5) {{
            requestAnimationFrame(() => {{ el.scrollTop = el.scrollHeight; }});
        }}
    }}

    function refreshAvatarsInView(playerId) {{
        const avatar = avatarCache[playerId];
        document.querySelectorAll('[data-pid="' + playerId + '"]').forEach(el => {{
            if (avatar && el.tagName !== 'IMG') {{
                const img = document.createElement('img');
                img.className = 'msg-avatar';
                img.src = avatar;
                img.dataset.pid = playerId;
                el.replaceWith(img);
            }} else if (avatar && el.tagName === 'IMG') {{
                el.src = avatar;
            }}
        }});
    }}

    // ===== SENDING =====
    function sendMessage() {{
        const input = document.getElementById('msg-input');
        const content = input.value.trim();
        if (!content || !ws || ws.readyState !== 1 || !currentConvId) return;
        ws.send(JSON.stringify({{type: 'message', conversation_id: currentConvId, content: content}}));
        input.value = '';
        input.focus();
        clearTypingState();
    }}

    // ===== TYPING =====
    function handleTypingInput() {{
        if (!ws || ws.readyState !== 1 || !currentConvId) return;
        if (!isTyping) {{
            isTyping = true;
            ws.send(JSON.stringify({{type: 'typing', conversation_id: currentConvId}}));
        }}
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {{ clearTypingState(); }}, 2500);
    }}

    function clearTypingState() {{
        if (isTyping && ws && ws.readyState === 1 && currentConvId) {{
            ws.send(JSON.stringify({{type: 'stop_typing', conversation_id: currentConvId}}));
        }}
        isTyping = false;
        clearTimeout(typingTimeout);
    }}

    function showTyping(convId, names) {{
        if (convId !== currentConvId) return;
        const el = document.getElementById('typing-indicator');
        if (!names || names.length === 0) {{
            el.textContent = '';
        }} else {{
            el.textContent = names[0] + ' is typing...';
        }}
    }}

    // ===== BAN WORD FILTERING =====
    function filterBanWords(text) {{
        if (!banWords || banWords.length === 0) return text;
        let result = text;
        for (const word of banWords) {{
            const escaped = word.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
            const regex = new RegExp('\\\\b' + escaped + '\\\\b', 'gi');
            result = result.replace(regex, '*'.repeat(word.length));
        }}
        return result;
    }}

    // ===== BAN WORD MODAL =====
    function openBanModal() {{
        closeSidebar();
        document.getElementById('ban-modal').style.display = 'flex';
        renderBanWords();
    }}
    function closeBanModal() {{ document.getElementById('ban-modal').style.display = 'none'; }}

    function renderBanWords() {{
        const container = document.getElementById('ban-word-list');
        if (banWords.length === 0) {{
            container.innerHTML = '<p style="color:#64748b; font-size:0.8rem;">No filtered words.</p>';
            return;
        }}
        container.innerHTML = banWords.sort().map(w =>
            `<span style="display:inline-flex; align-items:center; gap:4px; background:#1e293b; padding:3px 8px; border-radius:3px; margin:2px; font-size:0.75rem; color:#94a3b8;">${{escapeHtml(w)}}<span style="cursor:pointer; color:#ef4444; font-weight:bold; margin-left:2px;" onclick="removeBanWord('${{escapeHtml(w).replace(/'/g, "\\\\'")}}')">&times;</span></span>`
        ).join('');
    }}

    function addBanWordFromInput() {{
        const input = document.getElementById('ban-word-input');
        const word = input.value.trim().toLowerCase();
        if (!word) return;
        if (banWords.includes(word)) {{ input.value = ''; return; }}
        banWords.push(word);
        input.value = '';
        renderBanWords();
        saveBanWords();
    }}

    function removeBanWord(word) {{
        banWords = banWords.filter(w => w !== word);
        renderBanWords();
        saveBanWords();
    }}

    function resetBanWords() {{
        banWords = [...DEFAULT_BAN_WORDS];
        renderBanWords();
        saveBanWords();
    }}

    function clearAllBanWords() {{
        banWords = [];
        renderBanWords();
        saveBanWords();
    }}

    function saveBanWords() {{
        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{type: 'ban_words', words: banWords}}));
        }}
    }}

    // ===== EMOJI =====
    function toggleEmoji() {{
        document.getElementById('emoji-picker').classList.toggle('show');
    }}

    function insertEmoji(emoji) {{
        const input = document.getElementById('msg-input');
        const start = input.selectionStart;
        const end = input.selectionEnd;
        input.value = input.value.substring(0, start) + emoji + input.value.substring(end);
        input.selectionStart = input.selectionEnd = start + emoji.length;
        input.focus();
        document.getElementById('emoji-picker').classList.remove('show');
    }}

    // ===== AVATAR UPLOAD =====
    document.getElementById('avatar-input').addEventListener('change', function() {{
        const file = this.files[0];
        if (!file) return;
        if (file.size > {MAX_UPLOAD_BYTES}) {{
            alert('Image too large. Max 10MB.');
            return;
        }}
        const reader = new FileReader();
        reader.onload = () => {{
            const dataUri = reader.result;
            if (ws && ws.readyState === 1) {{
                ws.send(JSON.stringify({{type: 'avatar', data: dataUri}}));
            }}
            const display = document.getElementById('avatar-display');
            display.innerHTML = '<img class="avatar-preview" src="' + dataUri + '">';
            avatarCache[PLAYER_ID] = dataUri;
            refreshAvatarsInView(PLAYER_ID);
        }};
        reader.readAsDataURL(file);
    }});

    // ===== UTILS =====
    function escapeHtml(str) {{
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }}

    // ===== INIT =====
    function init() {{
        buildConvList();

        const existingAvatar = {avatar_json};
        if (existingAvatar) {{
            document.getElementById('avatar-display').innerHTML =
                '<img class="avatar-preview" src="' + existingAvatar + '">';
            avatarCache[PLAYER_ID] = existingAvatar;
        }}

        const input = document.getElementById('msg-input');
        input.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendMessage();
            }}
        }});
        input.addEventListener('input', handleTypingInput);

        // Progressive search with debounce
        document.getElementById('player-search').addEventListener('input', () => {{
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(handleSearch, 250);
        }});

        document.addEventListener('click', (e) => {{
            const picker = document.getElementById('emoji-picker');
            if (picker.classList.contains('show') && !e.target.closest('.emoji-picker') && !e.target.closest('.emoji-toggle')) {{
                picker.classList.remove('show');
            }}
            // Close search results on outside click
            if (!e.target.closest('#player-search') && !e.target.closest('#search-results')) {{
                document.getElementById('search-results').innerHTML = '';
            }}
        }});

        document.getElementById('ban-word-input').addEventListener('keydown', (e) => {{
            if (e.key === 'Enter') {{ e.preventDefault(); addBanWordFromInput(); }}
        }});

        window.addEventListener('beforeunload', () => {{
            if (ws && ws.readyState === 1) {{
                ws.send(JSON.stringify({{type: 'leave'}}));
                ws.close();
            }}
        }});

        connect();
    }}

    init();
    </script>
    """

    return HTMLResponse(dm_shell("Direct Messages", body, player.cash_balance, player.id))


# ==========================
# SEARCH API (HTTP fallback)
# ==========================

@router.get("/p2p/dms/search")
def dm_search_api(q: str = Query(""), session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    results = search_players(q, player.id)
    return JSONResponse({"results": results})


# ==========================
# WEBSOCKET ENDPOINT
# ==========================

@router.websocket("/p2p/dms/ws")
async def dm_websocket(websocket: WebSocket):
    await websocket.accept()

    session_token = websocket.cookies.get("session_token")
    if not session_token:
        await websocket.close(code=4001, reason="Not authenticated")
        return

    player = validate_session_ws(session_token)
    if not player:
        await websocket.close(code=4001, reason="Not authenticated")
        return

    player_id = player.id
    player_name = player.business_name

    await dm_manager.connect(websocket, player_id, player_name)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "join":
                conv_id = data.get("conversation_id")
                other_id = data.get("other_id")
                if not conv_id:
                    continue

                # Verify the player is part of this conversation
                parts = conv_id.split(":")
                if len(parts) != 2:
                    continue
                try:
                    id_a, id_b = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                if player_id not in (id_a, id_b):
                    await dm_manager.send_to_user(player_id, {
                        "type": "error",
                        "message": "You don't have access to this conversation."
                    })
                    continue

                # Ensure conversation exists
                get_or_create_conversation(id_a, id_b)

                # Send history
                messages = get_dm_messages(conv_id)
                for msg in messages:
                    sid = msg["sender_id"]
                    if sid not in dm_manager.avatar_cache:
                        from chat import get_avatar
                        dm_manager.avatar_cache[sid] = get_avatar(sid)
                    if dm_manager.avatar_cache.get(sid):
                        msg["avatar"] = dm_manager.avatar_cache[sid]

                await dm_manager.send_to_user(player_id, {
                    "type": "history",
                    "conversation_id": conv_id,
                    "messages": messages,
                })

                # Send online status of other player
                if other_id:
                    try:
                        other_id_int = int(other_id)
                        await dm_manager.send_to_user(player_id, {
                            "type": "online_status",
                            "player_id": other_id_int,
                            "online": dm_manager.is_online(other_id_int),
                        })
                        # Send avatar for other player
                        if other_id_int not in dm_manager.avatar_cache:
                            from chat import get_avatar
                            dm_manager.avatar_cache[other_id_int] = get_avatar(other_id_int)
                        av = dm_manager.avatar_cache.get(other_id_int)
                        if av:
                            await dm_manager.send_to_user(player_id, {
                                "type": "avatar_update",
                                "player_id": other_id_int,
                                "avatar": av,
                            })
                    except (ValueError, TypeError):
                        pass

            elif msg_type == "message":
                conv_id = data.get("conversation_id")
                content = data.get("content", "").strip()
                if not conv_id or not content or len(content) > MAX_DM_LENGTH:
                    continue

                # Verify access
                parts = conv_id.split(":")
                if len(parts) != 2:
                    continue
                try:
                    id_a, id_b = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                if player_id not in (id_a, id_b):
                    continue

                other_id = id_b if player_id == id_a else id_a

                saved = save_dm(conv_id, player_id, player_name, content)
                if saved:
                    saved["type"] = "message"
                    saved["avatar"] = dm_manager.avatar_cache.get(player_id)

                    # Determine other player's name for conv list updates
                    other_name = dm_manager.player_names.get(other_id) or get_player_name(other_id)
                    saved["other_id"] = other_id
                    saved["other_name"] = other_name

                    # Send to sender
                    await dm_manager.send_to_user(player_id, saved)

                    # Send to recipient (with adjusted other_id/other_name)
                    recipient_msg = dict(saved)
                    recipient_msg["other_id"] = player_id
                    recipient_msg["other_name"] = player_name
                    await dm_manager.send_to_user(other_id, recipient_msg)

                dm_manager.clear_typing(conv_id, player_id)
                typing_names = dm_manager.get_typing_names(conv_id)
                # Notify other player about typing update
                await dm_manager.send_to_user(other_id, {
                    "type": "typing",
                    "conversation_id": conv_id,
                    "names": typing_names,
                })

            elif msg_type == "typing":
                conv_id = data.get("conversation_id")
                if not conv_id:
                    continue
                parts = conv_id.split(":")
                if len(parts) != 2:
                    continue
                try:
                    id_a, id_b = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                if player_id not in (id_a, id_b):
                    continue
                other_id = id_b if player_id == id_a else id_a

                dm_manager.set_typing(conv_id, player_id)
                typing_names = dm_manager.get_typing_names(conv_id, exclude_id=other_id)
                await dm_manager.send_to_user(other_id, {
                    "type": "typing",
                    "conversation_id": conv_id,
                    "names": typing_names,
                })

            elif msg_type == "stop_typing":
                conv_id = data.get("conversation_id")
                if not conv_id:
                    continue
                parts = conv_id.split(":")
                if len(parts) != 2:
                    continue
                try:
                    id_a, id_b = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                if player_id not in (id_a, id_b):
                    continue
                other_id = id_b if player_id == id_a else id_a

                dm_manager.clear_typing(conv_id, player_id)
                typing_names = dm_manager.get_typing_names(conv_id)
                await dm_manager.send_to_user(other_id, {
                    "type": "typing",
                    "conversation_id": conv_id,
                    "names": typing_names,
                })

            elif msg_type == "avatar":
                avatar_data = data.get("data", "")
                if avatar_data and len(avatar_data) <= MAX_UPLOAD_BYTES * 2:
                    success = save_avatar(player_id, avatar_data)
                    if success:
                        from chat import get_avatar
                        compressed = get_avatar(player_id)
                        if compressed:
                            dm_manager.avatar_cache[player_id] = compressed
                            # Notify connected users who might see this avatar
                            for pid in list(dm_manager.connections.keys()):
                                await dm_manager.send_to_user(pid, {
                                    "type": "avatar_update",
                                    "player_id": player_id,
                                    "avatar": compressed,
                                })

            elif msg_type == "ban_words":
                words = data.get("words", [])
                if isinstance(words, list):
                    clean = [w.strip().lower() for w in words if isinstance(w, str) and w.strip()]
                    set_user_ban_words(player_id, clean)

            elif msg_type == "search":
                query = data.get("query", "").strip()
                results = search_players(query, player_id)
                await dm_manager.send_to_user(player_id, {
                    "type": "search_results",
                    "results": results,
                })

            elif msg_type == "leave":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[DM WS] Error: {e}")
    finally:
        await dm_manager.disconnect(player_id)
