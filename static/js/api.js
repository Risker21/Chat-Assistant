/**
 * API client with automatic Guest ID, JWT Bearer injection, and true SSE streaming parser.
 */

const TOKEN_STORAGE_KEY = 'chat_assistant_token';
const GUEST_ID_STORAGE_KEY = 'chat_assistant_guest_id';

function generateGuestId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
        return `g_${window.crypto.randomUUID().replace(/-/g, '')}`;
    }
    return `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

export function getGuestId() {
    let guestId = localStorage.getItem(GUEST_ID_STORAGE_KEY);
    if (!guestId || guestId.length < 8) {
        guestId = generateGuestId();
        localStorage.setItem(GUEST_ID_STORAGE_KEY, guestId);
    }
    return guestId;
}

export function getAuthToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || '';
}

export function setAuthToken(token) {
    if (token) {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
}

export function buildHeaders(extra = {}) {
    const headers = {
        'X-Guest-ID': getGuestId(),
        ...extra,
    };
    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

async function requestJson(url, options = {}) {
    const { headers = {}, ...rest } = options;
    const response = await fetch(url, {
        ...rest,
        headers: buildHeaders({
            'Content-Type': 'application/json',
            ...headers,
        }),
    });

    if (response.status === 204) {
        return null;
    }

    let data = null;
    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        const message = (data && (data.detail || data.message)) || `请求失败 (${response.status})`;
        const err = new Error(message);
        err.status = response.status;
        err.payload = data;
        throw err;
    }
    return data;
}

// System & Models
export const fetchHealth = () => requestJson('/api/health');
export const fetchModels = () => requestJson('/api/v1/models');

// Auth
export const fetchMe = () => requestJson('/api/v1/auth/me');
export const registerUser = (payload) =>
    requestJson('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(payload) });
export const loginUser = (payload) =>
    requestJson('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) });

// Personas
export const fetchPersonas = () => requestJson('/api/v1/personas');
export const createPersona = (payload) =>
    requestJson('/api/v1/personas', { method: 'POST', body: JSON.stringify(payload) });
export const updatePersona = (id, payload) =>
    requestJson(`/api/v1/personas/${encodeURIComponent(id)}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
    });
export const deletePersona = (id) =>
    requestJson(`/api/v1/personas/${encodeURIComponent(id)}`, { method: 'DELETE' });

// Conversations
export const fetchConversations = (q = '') => {
    const query = q ? `?q=${encodeURIComponent(q)}` : '';
    return requestJson(`/api/v1/conversations${query}`);
};
export const createConversation = (payload) =>
    requestJson('/api/v1/conversations', { method: 'POST', body: JSON.stringify(payload) });
export const fetchConversation = (id) =>
    requestJson(`/api/v1/conversations/${encodeURIComponent(id)}`);
export const updateConversation = (id, payload) =>
    requestJson(`/api/v1/conversations/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
    });
export const deleteConversation = (id) =>
    requestJson(`/api/v1/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
export const clearAllConversations = () =>
    requestJson('/api/v1/conversations', { method: 'DELETE' });
export const deleteMessage = (convId, msgId) =>
    requestJson(
        `/api/v1/conversations/${encodeURIComponent(convId)}/messages/${encodeURIComponent(msgId)}`,
        { method: 'DELETE' }
    );

export async function downloadConversationExport(convId, format = 'markdown', fallbackTitle = 'conversation') {
    const response = await fetch(
        `/api/v1/conversations/${encodeURIComponent(convId)}/export?format=${encodeURIComponent(format)}`,
        { headers: buildHeaders() }
    );
    if (!response.ok) {
        throw new Error('导出失败，请稍后重试');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ext = format === 'json' ? 'json' : 'md';
    a.download = `${fallbackTitle.replace(/[\\/:*?"<>|]/g, '_')}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Stream chat via POST /api/v1/chat/stream and dispatch parsed SSE events.
 */
export async function streamChat(payload, handlers = {}, signal = undefined) {
    const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
        signal,
    });

    if (!response.ok) {
        let errMsg = `请求失败 (${response.status})`;
        try {
            const errJson = await response.json();
            errMsg = errJson.detail || errJson.message || errMsg;
        } catch {
            // ignore
        }
        throw new Error(errMsg);
    }

    if (!response.body) {
        throw new Error('当前浏览器不支持流式响应');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    const dispatchFrame = (rawFrame) => {
        if (!rawFrame.trim()) return;
        let eventName = 'message';
        const dataLines = [];

        for (const line of rawFrame.split(/\r?\n/)) {
            if (line.startsWith('event:')) {
                eventName = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
                dataLines.push(line.slice(5).trimStart());
            }
        }
        if (dataLines.length === 0) return;

        let parsed;
        try {
            parsed = JSON.parse(dataLines.join('\n'));
        } catch {
            parsed = { raw: dataLines.join('\n') };
        }

        const map = {
            meta: handlers.onMeta,
            status: handlers.onStatus,
            sources: handlers.onSources,
            token: handlers.onToken,
            image: handlers.onImage,
            done: handlers.onDone,
            error: handlers.onError,
        };
        if (typeof map[eventName] === 'function') {
            map[eventName](parsed);
        }
    };

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            if (buffer.trim()) {
                dispatchFrame(buffer);
            }
            break;
        }

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() || '';
        for (const frame of frames) {
            dispatchFrame(frame);
        }
    }
}
