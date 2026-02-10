"""
chat_ux.py - Chat Room UI and WebSocket Endpoint
Full real-time chat with rooms, typing indicators, emoji picker,
per-user ban word filtering, and temporary profile avatars.
"""

import json
import base64
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from chat import (
    manager, STATIC_ROOMS, ADMIN_PLAYER_IDS, DEFAULT_BAN_WORDS,
    MAX_MESSAGE_LENGTH, MAX_AVATAR_BYTES,
    get_rooms_for_player, get_room_messages, save_message,
    get_user_ban_words, initialize_default_ban_words, set_user_ban_words,
    add_ban_word, remove_ban_word,
    save_avatar, get_avatar, delete_avatar,
)

router = APIRouter()


# ==========================
# AUTH HELPERS
# ==========================

def require_auth(session_token):
    """Check if user is authenticated."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        if not player:
            return RedirectResponse(url="/login", status_code=303)
        return player
    except Exception as e:
        print(f"[Chat UX] Auth check failed: {e}")
        return RedirectResponse(url="/login", status_code=303)


def validate_session_ws(session_token):
    """Validate a session token and return player or None (for WebSocket use)."""
    try:
        import auth
        db = auth.get_db()
        player = auth.get_player_from_session(db, session_token)
        db.close()
        return player
    except Exception:
        return None


# ==========================
# SHELL (chat-specific)
# ==========================

def chat_shell(title: str, body: str, balance: float = 0.0, player_id: int = None) -> str:
    """Full-page chat shell - wider layout, no ticker (covered by chat)."""
    from ux import get_player_lien_info

    lien_info = get_player_lien_info(player_id) if player_id else {"has_lien": False, "total_owed": 0.0, "status": "ok"}
    lien_html = ""
    if lien_info["has_lien"]:
        status_colors = {"critical": "#dc2626", "warning": "#f59e0b", "ok": "#64748b"}
        lien_color = status_colors.get(lien_info["status"], "#64748b")
        status_icons = {"critical": "🚨", "warning": "⚠️", "ok": "📋"}
        lien_icon = status_icons.get(lien_info["status"], "📋")
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
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #020617;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                height: 100vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}
            a {{ color: #38bdf8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}

            .header {{
                border-bottom: 1px solid #1e293b;
                padding: 8px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-shrink: 0;
                gap: 8px;
                background: #020617;
                z-index: 10;
            }}
            .brand {{ font-weight: bold; color: #38bdf8; font-size: 1rem; }}
            .header-right {{
                display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
            }}
            .balance {{ color: #22c55e; font-size: 0.75rem; white-space: nowrap; }}

            .chat-layout {{
                flex: 1;
                display: flex;
                overflow: hidden;
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
            .room-btn {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 10px;
                border: none;
                background: transparent;
                color: #94a3b8;
                font-family: inherit;
                font-size: 0.8rem;
                cursor: pointer;
                width: 100%;
                text-align: left;
                border-radius: 4px;
                transition: background 0.15s;
                position: relative;
            }}
            .room-btn:hover {{ background: #1e293b; color: #e5e7eb; }}
            .room-btn.active {{ background: #1e293b; color: #38bdf8; font-weight: bold; }}
            .room-btn .room-icon {{ font-size: 1rem; }}
            .room-btn .room-name {{ flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
            .room-btn .unread-badge {{
                background: #ef4444;
                color: #fff;
                font-size: 0.6rem;
                padding: 1px 5px;
                border-radius: 8px;
                min-width: 16px;
                text-align: center;
                display: none;
            }}
            .room-btn .unread-badge.show {{ display: inline-block; }}
            .room-btn .online-dot {{
                width: 6px; height: 6px;
                background: #22c55e;
                border-radius: 50%;
                margin-left: auto;
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
            .avatar-upload-btn {{
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                padding: 4px 10px;
                font-size: 0.7rem;
                font-family: inherit;
                cursor: pointer;
                border-radius: 3px;
            }}
            .avatar-upload-btn:hover {{ background: #334155; color: #e5e7eb; }}

            /* MAIN CHAT AREA */
            .chat-main {{
                flex: 1;
                display: flex;
                flex-direction: column;
                min-width: 0;
            }}
            .chat-header {{
                padding: 10px 16px;
                border-bottom: 1px solid #1e293b;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0a0f1e;
                flex-shrink: 0;
            }}
            .chat-header h3 {{
                font-size: 0.95rem;
                color: #e5e7eb;
                margin: 0;
            }}
            .chat-header .online-count {{
                font-size: 0.75rem;
                color: #64748b;
            }}
            .chat-messages {{
                flex: 1;
                overflow-y: auto;
                padding: 12px 16px;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            .chat-msg {{
                display: flex;
                gap: 10px;
                padding: 6px 0;
            }}
            .chat-msg .msg-avatar {{
                width: 32px;
                height: 32px;
                border-radius: 50%;
                flex-shrink: 0;
                object-fit: cover;
                background: #1e293b;
            }}
            .chat-msg .msg-avatar-letter {{
                width: 32px;
                height: 32px;
                border-radius: 50%;
                flex-shrink: 0;
                background: #1e293b;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.75rem;
                font-weight: bold;
                color: #64748b;
            }}
            .chat-msg .msg-body {{
                flex: 1;
                min-width: 0;
            }}
            .chat-msg .msg-header {{
                display: flex;
                align-items: baseline;
                gap: 8px;
                margin-bottom: 2px;
            }}
            .chat-msg .msg-name {{
                font-weight: bold;
                font-size: 0.8rem;
                color: #38bdf8;
            }}
            .chat-msg .msg-time {{
                font-size: 0.65rem;
                color: #475569;
            }}
            .chat-msg .msg-text {{
                font-size: 0.82rem;
                color: #cbd5e1;
                word-break: break-word;
                line-height: 1.4;
            }}
            .chat-msg.system-msg {{
                justify-content: center;
                padding: 4px 0;
            }}
            .chat-msg.system-msg .msg-text {{
                color: #64748b;
                font-size: 0.75rem;
                font-style: italic;
                text-align: center;
            }}

            .typing-indicator {{
                padding: 4px 16px 8px;
                font-size: 0.72rem;
                color: #64748b;
                font-style: italic;
                min-height: 24px;
                flex-shrink: 0;
            }}

            /* INPUT BAR */
            .chat-input-bar {{
                display: flex;
                gap: 8px;
                padding: 10px 16px;
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
                padding: 8px 12px;
                font-family: inherit;
                font-size: 0.85rem;
                border-radius: 4px;
                outline: none;
            }}
            .chat-input-bar input[type="text"]:focus {{
                border-color: #38bdf8;
            }}
            .chat-input-bar button {{
                background: #38bdf8;
                color: #020617;
                border: none;
                padding: 8px 16px;
                font-family: inherit;
                font-size: 0.85rem;
                cursor: pointer;
                border-radius: 4px;
                font-weight: bold;
            }}
            .chat-input-bar button:hover {{ background: #7dd3fc; }}
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
                right: 16px;
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 10px;
                width: 280px;
                max-height: 220px;
                overflow-y: auto;
                z-index: 100;
                box-shadow: 0 -4px 16px rgba(0,0,0,0.5);
            }}
            .emoji-picker.show {{ display: block; }}
            .emoji-picker span {{
                display: inline-block;
                padding: 3px 4px;
                cursor: pointer;
                font-size: 1.2rem;
                border-radius: 3px;
            }}
            .emoji-picker span:hover {{ background: #1e293b; }}

            /* BAN WORD MODAL */
            .modal-overlay {{
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.7);
                z-index: 200;
                justify-content: center;
                align-items: center;
            }}
            .modal-overlay.show {{ display: flex; }}
            .modal {{
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 20px;
                width: 90%;
                max-width: 500px;
                max-height: 80vh;
                overflow-y: auto;
            }}
            .modal h3 {{ margin-bottom: 12px; font-size: 1rem; color: #e5e7eb; }}
            .modal .ban-word-tag {{
                display: inline-flex;
                align-items: center;
                gap: 4px;
                background: #1e293b;
                padding: 3px 8px;
                border-radius: 3px;
                margin: 2px;
                font-size: 0.75rem;
                color: #94a3b8;
            }}
            .modal .ban-word-tag .remove-x {{
                cursor: pointer;
                color: #ef4444;
                font-weight: bold;
                margin-left: 2px;
            }}
            .modal .ban-word-tag .remove-x:hover {{ color: #f87171; }}
            .modal input {{
                background: #020617;
                border: 1px solid #1e293b;
                color: #e5e7eb;
                padding: 6px 10px;
                font-family: inherit;
                font-size: 0.85rem;
                border-radius: 4px;
                width: 100%;
            }}
            .modal-btn {{
                border: none;
                padding: 6px 14px;
                font-family: inherit;
                font-size: 0.8rem;
                cursor: pointer;
                border-radius: 3px;
            }}
            .modal-btn-blue {{ background: #38bdf8; color: #020617; }}
            .modal-btn-red {{ background: #ef4444; color: #fff; }}
            .modal-btn-gray {{ background: #334155; color: #94a3b8; }}

            /* READ-ONLY BANNER */
            .readonly-banner {{
                text-align: center;
                padding: 12px;
                color: #64748b;
                font-size: 0.8rem;
                border-top: 1px solid #1e293b;
                background: #0a0f1e;
            }}

            /* RESPONSIVE */
            @media (max-width: 640px) {{
                .chat-sidebar {{ width: 60px; min-width: 60px; }}
                .room-btn .room-name {{ display: none; }}
                .room-btn .room-icon {{ font-size: 1.2rem; }}
                .room-btn {{ justify-content: center; padding: 10px 4px; }}
                .sidebar-section h4 {{ display: none; }}
                .avatar-section {{ display: none; }}
                .sidebar-btn-section {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div style="display: flex; align-items: center; gap: 12px;">
                <a href="/dashboard" class="brand" style="text-decoration: none;">SymCo</a>
                <span style="color: #475569; font-size: 0.8rem;">Chat</span>
            </div>
            <div class="header-right">
                {lien_html}
                <span class="balance">$ {balance:,.2f}</span>
                <a href="/dashboard" style="color: #94a3b8; font-size: 0.8rem;">Dashboard</a>
                <a href="/api/logout" style="color: #ef4444; font-size: 0.8rem;">Logout</a>
            </div>
        </div>
        {body}
    </body>
    </html>
    """


# ==========================
# CHAT PAGE ROUTE
# ==========================

@router.get("/chat", response_class=HTMLResponse)
def chat_page(session_token: Optional[str] = Cookie(None)):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return player

    # Initialize default ban words on first visit
    initialize_default_ban_words(player.id)

    rooms = get_rooms_for_player(player.id)
    ban_words = get_user_ban_words(player.id)
    avatar = get_avatar(player.id)

    rooms_json = json.dumps(rooms)
    ban_words_json = json.dumps(ban_words)
    avatar_json = json.dumps(avatar) if avatar else "null"
    admin_ids_json = json.dumps(list(ADMIN_PLAYER_IDS))

    emojis = "😀😂🤣😊😎🤔😢😡🤮🥳🎉🔥💰📈📉🏭🛢️⚡🏗️🌾💎🤝👍👎❤️💀🚀💬⚠️🐛✅❌🏙️🏛️📊❓🎯🛡️⚔️🪙💸🏦📋"

    body = f"""
    <div class="chat-layout">
        <!-- SIDEBAR -->
        <div class="chat-sidebar">
            <div class="sidebar-section avatar-section">
                <div id="avatar-display">
                    <div class="avatar-letter" id="avatar-letter">{player.business_name[0].upper()}</div>
                </div>
                <div style="font-size: 0.75rem; color: #e5e7eb; margin-bottom: 6px; word-break: break-all;">{player.business_name}</div>
                <input type="file" id="avatar-input" accept="image/*" style="display:none;">
                <button class="avatar-upload-btn" onclick="document.getElementById('avatar-input').click()">Upload Pic</button>
            </div>

            <div class="sidebar-section" style="flex: 1;">
                <h4>Rooms</h4>
                <div id="room-list"></div>
            </div>

            <div class="sidebar-section sidebar-btn-section">
                <button class="avatar-upload-btn" style="width: 100%; margin-bottom: 6px;" onclick="openBanModal()">
                    Word Filter
                </button>
            </div>
        </div>

        <!-- MAIN CHAT -->
        <div class="chat-main" style="position: relative;">
            <div class="chat-header">
                <h3 id="room-title">Global Chat</h3>
                <span class="online-count" id="online-count"></span>
            </div>
            <div class="chat-messages" id="messages"></div>
            <div class="typing-indicator" id="typing-indicator"></div>

            <div id="input-section">
                <div class="chat-input-bar">
                    <input type="text" id="msg-input" placeholder="Type a message..." maxlength="{MAX_MESSAGE_LENGTH}" autocomplete="off">
                    <button class="emoji-toggle" onclick="toggleEmoji()" title="Emoji">😀</button>
                    <button id="send-btn" onclick="sendMessage()">Send</button>
                </div>
            </div>

            <div id="readonly-section" class="readonly-banner" style="display:none;">
                This channel is read-only.
            </div>

            <!-- Emoji Picker -->
            <div class="emoji-picker" id="emoji-picker">
                {"".join(f'<span onclick="insertEmoji(this.textContent)">{e}</span>' for e in emojis)}
            </div>
        </div>
    </div>

    <!-- Ban Word Modal -->
    <div class="modal-overlay" id="ban-modal">
        <div class="modal">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0;">Word Filter</h3>
                <span style="cursor: pointer; color: #64748b; font-size: 1.2rem;" onclick="closeBanModal()">&times;</span>
            </div>
            <p style="font-size: 0.75rem; color: #64748b; margin-bottom: 12px;">
                Filtered words appear as "****" in messages you see. Other players have their own lists.
            </p>
            <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                <input type="text" id="ban-word-input" placeholder="Add a word..." style="flex: 1;">
                <button class="modal-btn modal-btn-blue" onclick="addBanWordFromInput()">Add</button>
            </div>
            <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                <button class="modal-btn modal-btn-gray" onclick="resetBanWords()">Reset to Defaults</button>
                <button class="modal-btn modal-btn-red" onclick="clearAllBanWords()">Clear All</button>
            </div>
            <div id="ban-word-list" style="max-height: 300px; overflow-y: auto;"></div>
        </div>
    </div>

    <script>
    // ===== STATE =====
    const PLAYER_ID = {player.id};
    const PLAYER_NAME = {json.dumps(player.business_name)};
    const ROOMS = {rooms_json};
    let banWords = {ban_words_json};
    const ADMIN_IDS = {admin_ids_json};
    const DEFAULT_BAN_WORDS = {json.dumps(DEFAULT_BAN_WORDS)};

    let ws = null;
    let currentRoom = 'global';
    let reconnectDelay = 1000;
    let reconnectTimer = null;
    let typingTimeout = null;
    let isTyping = false;
    let unreadCounts = {{}};
    let avatarCache = {{}};  // player_id -> data URI

    // ===== WEBSOCKET =====
    function connect() {{
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(proto + '://' + location.host + '/chat/ws');

        ws.onopen = () => {{
            reconnectDelay = 1000;
            // Request current room history
            ws.send(JSON.stringify({{type: 'join', room: currentRoom}}));
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
                appendMessage(data);
                if (data.room !== currentRoom) {{
                    unreadCounts[data.room] = (unreadCounts[data.room] || 0) + 1;
                    updateRoomList();
                }}
                break;
            case 'history':
                renderHistory(data.room, data.messages);
                break;
            case 'typing':
                showTyping(data.room, data.names);
                break;
            case 'online':
                document.getElementById('online-count').textContent = data.count + ' online';
                break;
            case 'avatar_update':
                avatarCache[data.player_id] = data.avatar;
                refreshAvatarsInView(data.player_id);
                break;
            case 'error':
                appendSystemMsg(data.message);
                break;
        }}
    }}

    // ===== ROOMS =====
    function buildRoomList() {{
        const container = document.getElementById('room-list');
        container.innerHTML = '';
        ROOMS.forEach(r => {{
            const btn = document.createElement('button');
            btn.className = 'room-btn' + (r.id === currentRoom ? ' active' : '');
            btn.onclick = () => switchRoom(r.id);
            btn.innerHTML = `
                <span class="room-icon">${{r.icon}}</span>
                <span class="room-name">${{r.name}}</span>
                <span class="unread-badge ${{(unreadCounts[r.id] || 0) > 0 ? 'show' : ''}}" id="unread-${{r.id}}">${{unreadCounts[r.id] || ''}}</span>
            `;
            container.appendChild(btn);
        }});
    }}

    function updateRoomList() {{
        ROOMS.forEach(r => {{
            const badge = document.getElementById('unread-' + r.id);
            if (badge) {{
                const count = unreadCounts[r.id] || 0;
                badge.textContent = count > 99 ? '99+' : count;
                badge.classList.toggle('show', count > 0);
            }}
        }});
        // Update active state
        document.querySelectorAll('.room-btn').forEach((btn, i) => {{
            btn.classList.toggle('active', ROOMS[i].id === currentRoom);
        }});
    }}

    function switchRoom(roomId) {{
        currentRoom = roomId;
        unreadCounts[roomId] = 0;
        updateRoomList();

        const room = ROOMS.find(r => r.id === roomId);
        document.getElementById('room-title').textContent = room ? room.name : roomId;
        document.getElementById('messages').innerHTML = '';
        document.getElementById('typing-indicator').textContent = '';

        // Show/hide input based on read_only
        const isReadOnly = room && room.read_only && !ADMIN_IDS.includes(PLAYER_ID);
        document.getElementById('input-section').style.display = isReadOnly ? 'none' : '';
        document.getElementById('readonly-section').style.display = isReadOnly ? '' : 'none';

        if (ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{type: 'join', room: roomId}}));
        }}
    }}

    // ===== MESSAGES =====
    function renderHistory(room, messages) {{
        if (room !== currentRoom) return;
        const container = document.getElementById('messages');
        container.innerHTML = '';
        messages.forEach(m => appendMessage(m, false));
        scrollToBottom();
    }}

    function appendMessage(data, doScroll = true) {{
        if (data.room !== currentRoom) return;
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

        const nameColor = data.sender_id === PLAYER_ID ? '#22c55e' : (ADMIN_IDS.includes(data.sender_id) ? '#f59e0b' : '#38bdf8');

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
        const div = document.createElement('div');
        div.className = 'chat-msg system-msg';
        div.innerHTML = `<div class="msg-body"><div class="msg-text">${{escapeHtml(text)}}</div></div>`;
        container.appendChild(div);
        scrollToBottom();
    }}

    function scrollToBottom() {{
        const el = document.getElementById('messages');
        // Only auto-scroll if near bottom
        const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
        if (isNearBottom || el.children.length <= 5) {{
            requestAnimationFrame(() => {{ el.scrollTop = el.scrollHeight; }});
        }}
    }}

    function refreshAvatarsInView(playerId) {{
        const avatar = avatarCache[playerId];
        document.querySelectorAll('[data-pid="' + playerId + '"]').forEach(el => {{
            if (avatar && el.tagName !== 'IMG') {{
                // Replace letter div with img
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
        if (!content || !ws || ws.readyState !== 1) return;
        ws.send(JSON.stringify({{type: 'message', room: currentRoom, content: content}}));
        input.value = '';
        input.focus();
        clearTypingState();
    }}

    // ===== TYPING =====
    function handleTypingInput() {{
        if (!ws || ws.readyState !== 1) return;
        if (!isTyping) {{
            isTyping = true;
            ws.send(JSON.stringify({{type: 'typing', room: currentRoom}}));
        }}
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {{
            clearTypingState();
        }}, 2500);
    }}

    function clearTypingState() {{
        if (isTyping && ws && ws.readyState === 1) {{
            ws.send(JSON.stringify({{type: 'stop_typing', room: currentRoom}}));
        }}
        isTyping = false;
        clearTimeout(typingTimeout);
    }}

    function showTyping(room, names) {{
        if (room !== currentRoom) return;
        const el = document.getElementById('typing-indicator');
        if (!names || names.length === 0) {{
            el.textContent = '';
        }} else if (names.length === 1) {{
            el.textContent = names[0] + ' is typing...';
        }} else if (names.length === 2) {{
            el.textContent = names[0] + ' and ' + names[1] + ' are typing...';
        }} else {{
            el.textContent = names.length + ' people are typing...';
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
        document.getElementById('ban-modal').classList.add('show');
        renderBanWords();
    }}

    function closeBanModal() {{
        document.getElementById('ban-modal').classList.remove('show');
    }}

    function renderBanWords() {{
        const container = document.getElementById('ban-word-list');
        if (banWords.length === 0) {{
            container.innerHTML = '<p style="color: #64748b; font-size: 0.8rem;">No filtered words. Messages will be shown unfiltered.</p>';
            return;
        }}
        container.innerHTML = banWords.sort().map(w =>
            `<span class="ban-word-tag">${{escapeHtml(w)}}<span class="remove-x" onclick="removeBanWord('${{escapeHtml(w).replace(/'/g, "\\\\'")}}')">&times;</span></span>`
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
        if (file.size > {MAX_AVATAR_BYTES}) {{
            alert('Image too large. Max 150KB.');
            return;
        }}
        const reader = new FileReader();
        reader.onload = () => {{
            const dataUri = reader.result;
            // Send via WebSocket
            if (ws && ws.readyState === 1) {{
                ws.send(JSON.stringify({{type: 'avatar', data: dataUri}}));
            }}
            // Update local display
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
        buildRoomList();

        // Set up existing avatar
        const existingAvatar = {avatar_json};
        if (existingAvatar) {{
            document.getElementById('avatar-display').innerHTML =
                '<img class="avatar-preview" src="' + existingAvatar + '">';
            avatarCache[PLAYER_ID] = existingAvatar;
        }}

        // Enter key sends message
        const input = document.getElementById('msg-input');
        input.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendMessage();
            }}
        }});
        input.addEventListener('input', handleTypingInput);

        // Close emoji picker on outside click
        document.addEventListener('click', (e) => {{
            const picker = document.getElementById('emoji-picker');
            if (picker.classList.contains('show') && !e.target.closest('.emoji-picker') && !e.target.closest('.emoji-toggle')) {{
                picker.classList.remove('show');
            }}
        }});

        // Ban word input enter key
        document.getElementById('ban-word-input').addEventListener('keydown', (e) => {{
            if (e.key === 'Enter') {{ e.preventDefault(); addBanWordFromInput(); }}
        }});

        // Cleanup on page unload
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

    return HTMLResponse(chat_shell("Chat", body, player.cash_balance, player.id))


# ==========================
# AVATAR UPLOAD (HTTP fallback)
# ==========================

@router.post("/chat/avatar")
def upload_avatar_http(
    session_token: Optional[str] = Cookie(None),
    avatar: UploadFile = File(...),
):
    player = require_auth(session_token)
    if isinstance(player, RedirectResponse):
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    data = avatar.file.read()
    if len(data) > MAX_AVATAR_BYTES:
        return JSONResponse({"error": "Image too large"}, status_code=400)

    b64 = base64.b64encode(data).decode()
    content_type = avatar.content_type or "image/png"
    data_uri = f"data:{content_type};base64,{b64}"
    save_avatar(player.id, data_uri)
    return JSONResponse({"ok": True, "avatar": data_uri})


# ==========================
# WEBSOCKET ENDPOINT
# ==========================

@router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()

    # Authenticate from cookie
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
    rooms = get_rooms_for_player(player_id)

    await manager.connect(websocket, player_id, player_name, rooms)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "join":
                room_id = data.get("room", "global")
                # Verify player has access to this room
                room_ids = set(r["id"] for r in rooms)
                if room_id not in room_ids:
                    await manager.send_to_user(player_id, {
                        "type": "error",
                        "message": "You don't have access to this room."
                    })
                    continue

                # Send history
                messages = get_room_messages(room_id)
                # Attach avatars
                for msg in messages:
                    sid = msg["sender_id"]
                    if sid not in manager.avatar_cache:
                        manager.avatar_cache[sid] = get_avatar(sid)
                    if manager.avatar_cache.get(sid):
                        msg["avatar"] = manager.avatar_cache[sid]

                await manager.send_to_user(player_id, {
                    "type": "history",
                    "room": room_id,
                    "messages": messages,
                })

                # Send online count
                count = manager.get_online_count(room_id)
                await manager.send_to_user(player_id, {
                    "type": "online",
                    "room": room_id,
                    "count": count,
                })

                # Send cached avatars for this room's users
                for pid in list(manager.connections.keys()):
                    av = manager.avatar_cache.get(pid)
                    if av:
                        await manager.send_to_user(player_id, {
                            "type": "avatar_update",
                            "player_id": pid,
                            "avatar": av,
                        })

            elif msg_type == "message":
                room_id = data.get("room", "global")
                content = data.get("content", "").strip()
                if not content or len(content) > MAX_MESSAGE_LENGTH:
                    continue

                # Check room access
                room_ids = set(r["id"] for r in rooms)
                if room_id not in room_ids:
                    continue

                # Check read-only (news)
                room_info = next((r for r in STATIC_ROOMS if r["id"] == room_id), None)
                if room_info and room_info.get("read_only") and player_id not in ADMIN_PLAYER_IDS:
                    await manager.send_to_user(player_id, {
                        "type": "error",
                        "message": "This channel is read-only."
                    })
                    continue

                # Save and broadcast
                saved = save_message(room_id, player_id, player_name, content)
                if saved:
                    saved["type"] = "message"
                    saved["avatar"] = manager.avatar_cache.get(player_id)
                    await manager.broadcast_to_room(room_id, saved)

                # Clear typing
                manager.clear_typing(room_id, player_id)
                typing_names = manager.get_typing_names(room_id)
                await manager.broadcast_to_room(room_id, {
                    "type": "typing",
                    "room": room_id,
                    "names": typing_names,
                })

            elif msg_type == "typing":
                room_id = data.get("room", "global")
                manager.set_typing(room_id, player_id)
                typing_names = manager.get_typing_names(room_id, exclude_id=None)
                # Send to everyone except the typer
                for pid in list(manager.connections.keys()):
                    if pid != player_id and room_id in manager.player_rooms.get(pid, set()):
                        names_for_user = [n for n in typing_names if n != manager.player_names.get(pid)]
                        await manager.send_to_user(pid, {
                            "type": "typing",
                            "room": room_id,
                            "names": names_for_user,
                        })

            elif msg_type == "stop_typing":
                room_id = data.get("room", "global")
                manager.clear_typing(room_id, player_id)
                typing_names = manager.get_typing_names(room_id)
                for pid in list(manager.connections.keys()):
                    if pid != player_id and room_id in manager.player_rooms.get(pid, set()):
                        await manager.send_to_user(pid, {
                            "type": "typing",
                            "room": room_id,
                            "names": typing_names,
                        })

            elif msg_type == "avatar":
                avatar_data = data.get("data", "")
                if avatar_data and len(avatar_data) <= MAX_AVATAR_BYTES:
                    save_avatar(player_id, avatar_data)
                    manager.avatar_cache[player_id] = avatar_data
                    # Broadcast avatar update to all connected users
                    for pid in list(manager.connections.keys()):
                        await manager.send_to_user(pid, {
                            "type": "avatar_update",
                            "player_id": player_id,
                            "avatar": avatar_data,
                        })

            elif msg_type == "ban_words":
                words = data.get("words", [])
                if isinstance(words, list):
                    clean = [w.strip().lower() for w in words if isinstance(w, str) and w.strip()]
                    set_user_ban_words(player_id, clean)

            elif msg_type == "leave":
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(player_id)
