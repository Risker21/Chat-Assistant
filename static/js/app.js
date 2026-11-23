/**
 * Main application controller wiring state, API, SSE streaming, and user interactions.
 */

import * as api from './api.js';
import { enhanceMarkdownContainer, escapeHtml, renderMarkdownHtml } from './markdown.js';
import { store } from './store.js';
import * as ui from './ui.js';

const MAX_IMAGE_BYTES = 8 * 1024 * 1024; // 8MB per image
const MAX_IMAGES = 4;

// DOM refs
const chatHistory = document.getElementById('chat-history');
const messagesList = document.getElementById('messages-list');
const welcomeScreen = document.getElementById('welcome-screen');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const stopBtn = document.getElementById('stop-btn');
const scrollBottomBtn = document.getElementById('scroll-bottom-btn');
const charCountEl = document.getElementById('char-count');

const sidebar = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebar-backdrop');
const activeConvTitleEl = document.getElementById('active-conv-title');
const personaDropdownBtn = document.getElementById('persona-dropdown-btn');
const personaDropdownMenu = document.getElementById('persona-dropdown-menu');
const modelDropdownBtn = document.getElementById('model-dropdown-btn');
const modelDropdownMenu = document.getElementById('model-dropdown-menu');
const convSearchInput = document.getElementById('conv-search-input');

const webSearchToggle = document.getElementById('web-search-toggle');
const webSearchLabel = document.getElementById('web-search-label');
const imageModeToggle = document.getElementById('image-mode-toggle');
const imageModeLabel = document.getElementById('image-mode-label');

let authMode = 'login'; // 'login' | 'register'
let searchDebounceTimer = null;

// --- Utility helpers ---

function scrollToBottom(smooth = false) {
    chatHistory.scrollTo({
        top: chatHistory.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
    });
}

function isNearBottom() {
    return chatHistory.scrollHeight - chatHistory.scrollTop - chatHistory.clientHeight < 120;
}

function updateSendButtonState() {
    const hasText = messageInput.value.trim().length > 0;
    const hasImgs = store.uploadedImages.length > 0;
    sendBtn.disabled = store.isStreaming || (!hasText && !hasImgs);
    const len = messageInput.value.length;
    if (charCountEl) {
        charCountEl.textContent = len > 0 ? `${len} 字` : '';
    }
}

function setStreamingUI(streaming) {
    store.isStreaming = streaming;
    if (streaming) {
        sendBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
        messageInput.disabled = true;
    } else {
        sendBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
        messageInput.disabled = false;
        updateSendButtonState();
        messageInput.focus();
    }
}

function updateComposerModeBadges() {
    const searchMap = {
        auto: { text: '联网: 自动', active: false },
        on: { text: '联网: 开启', active: true },
        off: { text: '联网: 关闭', active: false },
    };
    const s = searchMap[store.settings.webSearchMode] || searchMap.auto;
    webSearchLabel.textContent = s.text;
    webSearchToggle.classList.toggle('bg-violet-50', s.active);
    webSearchToggle.classList.toggle('dark:bg-violet-950/40', s.active);
    webSearchToggle.classList.toggle('text-violet-600', s.active);
    webSearchToggle.classList.toggle('dark:text-violet-300', s.active);
    webSearchToggle.classList.toggle('border-violet-300', s.active);

    const imgMap = {
        auto: { text: '绘图: 自动', active: false },
        generate: { text: '绘图: 强制生图', active: true },
        off: { text: '绘图: 关闭', active: false },
    };
    const im = imgMap[store.settings.imageMode] || imgMap.auto;
    imageModeLabel.textContent = im.text;
    imageModeToggle.classList.toggle('bg-violet-50', im.active);
    imageModeToggle.classList.toggle('dark:bg-violet-950/40', im.active);
    imageModeToggle.classList.toggle('text-violet-600', im.active);
    imageModeToggle.classList.toggle('dark:text-violet-300', im.active);
    imageModeToggle.classList.toggle('border-violet-300', im.active);
}

// --- Message list rendering ---

const messageHandlers = {
    onCopy: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            ui.showToast('已复制到剪贴板');
        } catch {
            ui.showToast('复制失败', 'error');
        }
    },
    onRegenerate: async () => {
        if (store.isStreaming || !store.activeConversationId) return;
        await executeChatStream({ regenerate: true });
    },
    onEdit: async (msg) => {
        if (store.isStreaming) return;
        const edited = window.prompt('编辑消息并重新发送：', msg.content);
        if (edited === null || !edited.trim()) return;
        await executeChatStream({
            message: edited.trim(),
            edit_message_id: msg.id,
        });
    },
    onDelete: async (msg) => {
        if (store.isStreaming || !store.activeConversationId || !msg.id) return;
        try {
            await api.deleteMessage(store.activeConversationId, msg.id);
            store.messages = store.messages.filter((m) => m.id !== msg.id);
            renderMessagesFeed();
            ui.showToast('已删除该条消息', 'info');
        } catch (err) {
            ui.showToast(err.message, 'error');
        }
    },
};

function renderMessagesFeed() {
    if (!store.messages.length) {
        welcomeScreen.classList.remove('hidden');
        messagesList.innerHTML = '';
        ui.renderWelcomeScreen((promptText) => {
            messageInput.value = promptText;
            autoResizeTextarea();
            updateSendButtonState();
            messageInput.focus();
        });
        return;
    }

    welcomeScreen.classList.add('hidden');
    messagesList.innerHTML = '';

    const lastAssistantIdx = store.messages.reduce(
        (acc, m, idx) => (m.role === 'assistant' ? idx : acc),
        -1
    );

    store.messages.forEach((msg, idx) => {
        const el = ui.createMessageElement(msg, messageHandlers, {
            isLastAssistant: idx === lastAssistantIdx,
        });
        messagesList.appendChild(el);
    });
}

// --- Data loading ---

async function refreshConversations() {
    try {
        const data = await api.fetchConversations(store.searchQuery);
        store.conversations = data.conversations || [];
        ui.renderConversationSidebar({
            onSelect: async (conv) => {
                await openConversation(conv.id);
                closeMobileSidebar();
            },
            onPin: async (conv) => {
                try {
                    await api.updateConversation(conv.id, { pinned: !conv.pinned });
                    await refreshConversations();
                    ui.showToast(conv.pinned ? '已取消置顶' : '已置顶对话');
                } catch (err) {
                    ui.showToast(err.message, 'error');
                }
            },
            onRename: async (conv) => {
                const newTitle = window.prompt('请输入新的对话标题：', conv.title);
                if (!newTitle || !newTitle.trim()) return;
                try {
                    await api.updateConversation(conv.id, { title: newTitle.trim() });
                    if (store.activeConversationId === conv.id) {
                        activeConvTitleEl.textContent = newTitle.trim();
                    }
                    await refreshConversations();
                    ui.showToast('标题已更新');
                } catch (err) {
                    ui.showToast(err.message, 'error');
                }
            },
            onDelete: async (conv) => {
                if (!window.confirm(`确定删除对话「${conv.title}」吗？`)) return;
                try {
                    await api.deleteConversation(conv.id);
                    if (store.activeConversationId === conv.id) {
                        startNewChat();
                    }
                    await refreshConversations();
                    ui.showToast('对话已删除', 'info');
                } catch (err) {
                    ui.showToast(err.message, 'error');
                }
            },
        });
    } catch (err) {
        console.error('Failed to load conversations', err);
    }
}

async function openConversation(conversationId) {
    if (store.isStreaming) {
        ui.showToast('请先等待或停止当前回复', 'info');
        return;
    }
    try {
        const detail = await api.fetchConversation(conversationId);
        store.activeConversationId = detail.id;
        store.activeConversation = detail;
        store.messages = detail.messages || [];
        store.selectedModel = detail.model || store.selectedModel;
        store.selectedPersonaId = detail.persona_id || store.selectedPersonaId;
        store.settings.systemPromptOverride = detail.system_prompt_override || '';

        activeConvTitleEl.textContent = detail.title;
        renderHeaderSelectors();
        renderMessagesFeed();
        await refreshConversations();
        requestAnimationFrame(() => scrollToBottom(false));
    } catch (err) {
        ui.showToast(err.message, 'error');
    }
}

function closeHeaderDropdowns() {
    personaDropdownMenu.classList.add('hidden');
    personaDropdownBtn.setAttribute('aria-expanded', 'false');
    modelDropdownMenu.classList.add('hidden');
    modelDropdownBtn.setAttribute('aria-expanded', 'false');
}

function renderHeaderSelectors() {
    ui.renderSelectors({
        onSelectPersona: (persona) => {
            store.selectedPersonaId = persona.id;
            if (persona.default_model && store.models.some((m) => m.value === persona.default_model)) {
                store.selectedModel = persona.default_model;
            }
            closeHeaderDropdowns();
            renderHeaderSelectors();
            if (!store.messages.length) renderMessagesFeed();
            ui.showToast(`已切换角色：${persona.name}`);
        },
        onSelectModel: (model) => {
            store.selectedModel = model.value;
            closeHeaderDropdowns();
            renderHeaderSelectors();
            ui.showToast(
                `已切换模型：${model.label}${model.configured ? '' : '（未配置 API Key）'}`,
                model.configured ? 'success' : 'info'
            );
        },
    });
}

function startNewChat() {
    if (store.isStreaming) {
        if (store.abortController) store.abortController.abort();
    }
    store.activeConversationId = null;
    store.activeConversation = null;
    store.messages = [];
    store.settings.systemPromptOverride = '';
    activeConvTitleEl.textContent = '新对话';
    renderMessagesFeed();
    refreshConversations();
    messageInput.focus();
}

async function refreshPersonasAndModels() {
    const [modelsData, personasData] = await Promise.all([api.fetchModels(), api.fetchPersonas()]);
    store.models = modelsData.models || [];
    store.webSearchEnabled = Boolean(modelsData.web_search_enabled);
    store.visionEnabled = Boolean(modelsData.vision_enabled);
    store.personas = personasData.personas || [];

    // Prefer first configured model on initial boot if current default isn't configured
    const currentModel = store.models.find((m) => m.value === store.selectedModel);
    if (!currentModel || !currentModel.configured) {
        const firstReady = store.models.find((m) => m.configured);
        if (firstReady && !store.activeConversationId) {
            store.selectedModel = firstReady.value;
            store.selectedPersonaId = firstReady.default_persona_id;
        }
    }
    renderHeaderSelectors();
    ui.renderProviderDiagnostics();
}

async function bootstrap() {
    initTheme();
    updateComposerModeBadges();

    try {
        const me = await api.fetchMe();
        store.user = me;
        ui.renderUserAccountBar();
    } catch (err) {
        console.warn('Auth check fallback to guest:', err);
    }

    await refreshPersonasAndModels();
    await refreshConversations();
    renderMessagesFeed();
}

// --- Core SSE Streaming Flow ---

async function executeChatStream({ message = '', images = [], regenerate = false, edit_message_id = null } = {}) {
    if (store.isStreaming) return;

    welcomeScreen.classList.add('hidden');
    setStreamingUI(true);

    // Optimistic UI update for user message
    if (!regenerate) {
        if (edit_message_id) {
            const idx = store.messages.findIndex((m) => m.id === edit_message_id);
            if (idx !== -1) {
                store.messages = store.messages.slice(0, idx);
            }
        }
        const tempUserMsg = {
            id: null,
            role: 'user',
            content: message || (images.length ? '[图片]' : ''),
            images: [...images],
            msg_type: 'text',
        };
        store.messages.push(tempUserMsg);
        renderMessagesFeed();
        scrollToBottom(true);
    } else {
        // Remove trailing assistant messages visually
        while (store.messages.length && store.messages[store.messages.length - 1].role !== 'user') {
            store.messages.pop();
        }
        renderMessagesFeed();
        scrollToBottom(true);
    }

    // Create live assistant placeholder DOM element
    const liveMsg = {
        id: null,
        role: 'assistant',
        content: '',
        msg_type: 'text',
        model: store.selectedModel,
        sources: [],
    };
    const assistantEl = ui.createMessageElement(liveMsg, messageHandlers, {
        isLastAssistant: true,
        isStreaming: true,
    });
    messagesList.appendChild(assistantEl);
    ui.setAssistantStatus(assistantEl, 'thinking', '正在连接模型...');
    scrollToBottom(true);

    const cardBody = assistantEl.querySelector('.msg-card-body');
    const mdDiv = assistantEl.querySelector('.markdown-body');

    let renderScheduled = false;
    const scheduleMarkdownRender = () => {
        if (renderScheduled) return;
        renderScheduled = true;
        requestAnimationFrame(() => {
            renderScheduled = false;
            if (mdDiv) {
                const stickToBottom = isNearBottom();
                mdDiv.innerHTML = renderMarkdownHtml(liveMsg.content);
                if (stickToBottom) scrollToBottom(false);
            }
        });
    };

    store.abortController = new AbortController();

    try {
        await api.streamChat(
            {
                message,
                conversation_id: store.activeConversationId,
                model: store.selectedModel,
                persona_id: store.selectedPersonaId,
                images,
                web_search: store.settings.webSearchMode,
                image_mode: store.settings.imageMode,
                temperature: store.settings.temperature,
                max_history: store.settings.maxHistory,
                system_prompt_override: store.settings.systemPromptOverride || null,
                regenerate,
                edit_message_id,
            },
            {
                onMeta: (meta) => {
                    if (meta.conversation_id) {
                        store.activeConversationId = meta.conversation_id;
                    }
                    if (meta.title) {
                        activeConvTitleEl.textContent = meta.title;
                    }
                    if (meta.user_message_id) {
                        const lastUser = [...store.messages].reverse().find((m) => m.role === 'user');
                        if (lastUser && !lastUser.id) lastUser.id = meta.user_message_id;
                    }
                },
                onStatus: (st) => {
                    ui.setAssistantStatus(assistantEl, st.stage, st.message);
                    if (isNearBottom()) scrollToBottom(false);
                },
                onSources: (payload) => {
                    liveMsg.sources = payload.results || [];
                    ui.setAssistantSources(assistantEl, liveMsg.sources);
                    if (isNearBottom()) scrollToBottom(false);
                },
                onToken: (payload) => {
                    if (payload.content) {
                        ui.setAssistantStatus(assistantEl, '', '');
                        liveMsg.content += payload.content;
                        scheduleMarkdownRender();
                    }
                },
                onImage: (payload) => {
                    ui.setAssistantStatus(assistantEl, '', '');
                    liveMsg.msg_type = 'image';
                    liveMsg.image_url = payload.url;
                    liveMsg.image_prompt = payload.prompt;
                    liveMsg.content = payload.prompt || '';
                    liveMsg.model = payload.provider || store.selectedModel;
                    if (cardBody) {
                        cardBody.innerHTML = `
                            <p class="text-xs text-slate-500 dark:text-slate-400 mb-2.5 italic">“${escapeHtml(payload.prompt || '')}”</p>
                            <img src="${escapeHtml(payload.url)}" class="gen-msg-img max-w-full max-h-[420px] rounded-xl shadow-md cursor-zoom-in">
                        `;
                        const imgEl = cardBody.querySelector('.gen-msg-img');
                        if (imgEl) {
                            imgEl.addEventListener('click', () => ui.openLightbox(payload.url, payload.prompt));
                        }
                    }
                    scrollToBottom(true);
                },
                onDone: (done) => {
                    ui.setAssistantStatus(assistantEl, '', '');
                    liveMsg.id = done.message_id || null;
                    liveMsg.latency_ms = done.latency_ms || null;
                    if (done.title) activeConvTitleEl.textContent = done.title;
                    if (mdDiv) {
                        mdDiv.classList.remove('stream-cursor');
                        mdDiv.innerHTML = renderMarkdownHtml(liveMsg.content);
                        enhanceMarkdownContainer(mdDiv, ui.showToast);
                    }
                    store.messages.push(liveMsg);
                    renderMessagesFeed();
                    scrollToBottom(true);
                },
                onError: (err) => {
                    ui.setAssistantStatus(assistantEl, '', '');
                    liveMsg.msg_type = 'error';
                    liveMsg.content = err.message || '请求出错，请稍后重试。';
                    store.messages.push(liveMsg);
                    renderMessagesFeed();
                    ui.showToast(liveMsg.content, 'error');
                },
            },
            store.abortController.signal
        );
    } catch (err) {
        ui.setAssistantStatus(assistantEl, '', '');
        if (err.name === 'AbortError') {
            if (liveMsg.content) {
                store.messages.push(liveMsg);
                renderMessagesFeed();
            } else {
                assistantEl.remove();
            }
            ui.showToast('已停止生成', 'info');
        } else {
            liveMsg.msg_type = 'error';
            liveMsg.content = err.message || '连接服务器失败，请检查服务是否正常运行。';
            store.messages.push(liveMsg);
            renderMessagesFeed();
            ui.showToast(liveMsg.content, 'error');
        }
    } finally {
        store.abortController = null;
        setStreamingUI(false);
        await refreshConversations();
    }
}

// --- Image Upload (Click, Paste, Drag & Drop) ---

function handleImageFiles(files) {
    const fileList = Array.from(files || []);
    for (const file of fileList) {
        if (!file.type.startsWith('image/')) continue;
        if (store.uploadedImages.length >= MAX_IMAGES) {
            ui.showToast(`最多一次上传 ${MAX_IMAGES} 张图片`, 'info');
            break;
        }
        if (file.size > MAX_IMAGE_BYTES) {
            ui.showToast(`图片 ${file.name} 超过 8MB 限制`, 'error');
            continue;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            store.uploadedImages.push(ev.target.result);
            ui.renderImagePreviews(removeUploadedImage);
            updateSendButtonState();
        };
        reader.readAsDataURL(file);
    }
}

function removeUploadedImage(index) {
    store.uploadedImages.splice(index, 1);
    ui.renderImagePreviews(removeUploadedImage);
    updateSendButtonState();
}

// --- Textarea & Theme ---

function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 176)}px`;
}

function initTheme() {
    const html = document.documentElement;
    const stored = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = stored === 'dark' || (!stored && prefersDark);
    html.classList.toggle('dark', isDark);
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    const icon = document.querySelector('#theme-toggle i');
    if (!icon) return;
    icon.className = isDark ? 'fa-solid fa-sun text-sm text-amber-400' : 'fa-solid fa-moon text-sm';
}

// --- Sidebar mobile/desktop toggle ---

function openMobileSidebar() {
    sidebar.classList.remove('-translate-x-full');
    sidebarBackdrop.classList.remove('hidden');
}

function closeMobileSidebar() {
    sidebar.classList.add('-translate-x-full');
    sidebarBackdrop.classList.add('hidden');
}

// --- Modals ---

function toggleModal(modalId, show) {
    const el = document.getElementById(modalId);
    if (!el) return;
    el.classList.toggle('hidden', !show);
    el.classList.toggle('flex', show);
}

function setAuthTab(mode) {
    authMode = mode;
    const loginTab = document.getElementById('auth-tab-login');
    const regTab = document.getElementById('auth-tab-register');
    const displayWrap = document.getElementById('auth-display-name-wrap');
    const emailWrap = document.getElementById('auth-email-wrap');
    const submitBtn = document.getElementById('auth-submit-btn');
    const errEl = document.getElementById('auth-error');

    errEl.classList.add('hidden');
    if (mode === 'login') {
        loginTab.className = 'flex-1 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-dark-surface text-violet-600 shadow-xs transition-all';
        regTab.className = 'flex-1 py-2 text-sm font-semibold rounded-lg text-slate-500 dark:text-slate-400 transition-all';
        displayWrap.classList.add('hidden');
        emailWrap.classList.add('hidden');
        submitBtn.textContent = '立即登录';
    } else {
        regTab.className = 'flex-1 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-dark-surface text-violet-600 shadow-xs transition-all';
        loginTab.className = 'flex-1 py-2 text-sm font-semibold rounded-lg text-slate-500 dark:text-slate-400 transition-all';
        displayWrap.classList.remove('hidden');
        emailWrap.classList.remove('hidden');
        submitBtn.textContent = '创建账号并同步数据';
    }
}

function resetPersonaForm() {
    document.getElementById('persona-edit-id').value = '';
    document.getElementById('persona-name').value = '';
    document.getElementById('persona-title').value = '';
    document.getElementById('persona-desc').value = '';
    document.getElementById('persona-prompt').value = '';
    document.getElementById('persona-model').value = store.selectedModel;
    document.getElementById('persona-icon-picker').value = 'fa-sparkles';
    document.getElementById('persona-gradient-picker').value = 'bg-gradient-to-br from-violet-500 to-indigo-600';
    document.getElementById('persona-form-title').textContent = '创建自定义角色';
    document.getElementById('persona-submit-btn').textContent = '保存自定义角色';
}

function renderPersonaStudio() {
    ui.renderPersonaStudioList({
        onActivate: (p) => {
            store.selectedPersonaId = p.id;
            if (p.default_model) store.selectedModel = p.default_model;
            renderHeaderSelectors();
            if (!store.messages.length) renderMessagesFeed();
            toggleModal('persona-modal', false);
            ui.showToast(`已切换角色：${p.name}`);
        },
        onEdit: (p) => {
            document.getElementById('persona-edit-id').value = p.id;
            document.getElementById('persona-name').value = p.name;
            document.getElementById('persona-title').value = p.title;
            document.getElementById('persona-desc').value = p.description || '';
            document.getElementById('persona-prompt').value = p.system_prompt;
            document.getElementById('persona-model').value = p.default_model || 'deepseek';
            document.getElementById('persona-icon-picker').value = p.icon || 'fa-sparkles';
            document.getElementById('persona-gradient-picker').value =
                p.bg_gradient || 'bg-gradient-to-br from-violet-500 to-indigo-600';
            document.getElementById('persona-form-title').textContent = `编辑角色：${p.name}`;
            document.getElementById('persona-submit-btn').textContent = '更新角色';
        },
        onDelete: async (p) => {
            if (!window.confirm(`确定删除自定义角色「${p.name}」吗？`)) return;
            try {
                await api.deletePersona(p.id);
                if (store.selectedPersonaId === p.id) {
                    store.selectedPersonaId = 'deepseek';
                }
                await refreshPersonasAndModels();
                renderPersonaStudio();
                if (!store.messages.length) renderMessagesFeed();
                ui.showToast('自定义角色已删除', 'info');
            } catch (err) {
                ui.showToast(err.message, 'error');
            }
        },
    });
}

// --- Event Wiring ---

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    const images = [...store.uploadedImages];
    if (!message && !images.length) return;

    messageInput.value = '';
    autoResizeTextarea();
    store.uploadedImages = [];
    ui.renderImagePreviews(removeUploadedImage);
    updateSendButtonState();

    await executeChatStream({ message, images });
});

stopBtn.addEventListener('click', () => {
    if (store.abortController) {
        store.abortController.abort();
    }
});

messageInput.addEventListener('input', () => {
    autoResizeTextarea();
    updateSendButtonState();
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        if (!sendBtn.disabled) {
            chatForm.requestSubmit();
        }
    }
});

// Image upload events
document.getElementById('image-btn').addEventListener('click', () => {
    document.getElementById('image-input').click();
});
document.getElementById('image-input').addEventListener('change', (e) => {
    handleImageFiles(e.target.files);
    e.target.value = '';
});
document.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items || [];
    const files = [];
    for (const item of items) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
            const f = item.getAsFile();
            if (f) files.push(f);
        }
    }
    if (files.length) handleImageFiles(files);
});
chatForm.addEventListener('dragover', (e) => {
    e.preventDefault();
    chatForm.classList.add('dropzone-active');
});
chatForm.addEventListener('dragleave', () => {
    chatForm.classList.remove('dropzone-active');
});
chatForm.addEventListener('drop', (e) => {
    e.preventDefault();
    chatForm.classList.remove('dropzone-active');
    if (e.dataTransfer?.files?.length) {
        handleImageFiles(e.dataTransfer.files);
    }
});

// Composer toggles
webSearchToggle.addEventListener('click', () => {
    const order = ['auto', 'on', 'off'];
    const next = order[(order.indexOf(store.settings.webSearchMode) + 1) % order.length];
    store.saveSettings({ webSearchMode: next });
    updateComposerModeBadges();
});
imageModeToggle.addEventListener('click', () => {
    const order = ['auto', 'generate', 'off'];
    const next = order[(order.indexOf(store.settings.imageMode) + 1) % order.length];
    store.saveSettings({ imageMode: next });
    updateComposerModeBadges();
});

// Custom Persona & Model Dropdowns
personaDropdownBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const willOpen = personaDropdownMenu.classList.contains('hidden');
    closeHeaderDropdowns();
    if (willOpen) {
        personaDropdownMenu.classList.remove('hidden');
        personaDropdownBtn.setAttribute('aria-expanded', 'true');
    }
});

modelDropdownBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const willOpen = modelDropdownMenu.classList.contains('hidden');
    closeHeaderDropdowns();
    if (willOpen) {
        modelDropdownMenu.classList.remove('hidden');
        modelDropdownBtn.setAttribute('aria-expanded', 'true');
    }
});

document.getElementById('dropdown-open-studio-btn').addEventListener('click', () => {
    closeHeaderDropdowns();
    resetPersonaForm();
    renderPersonaStudio();
    toggleModal('persona-modal', true);
});

document.addEventListener('click', (e) => {
    if (!e.target.closest('#persona-dropdown') && !e.target.closest('#model-dropdown')) {
        closeHeaderDropdowns();
    }
});

// Scroll behavior
chatHistory.addEventListener('scroll', () => {
    const show = !isNearBottom();
    scrollBottomBtn.classList.toggle('opacity-0', !show);
    scrollBottomBtn.classList.toggle('invisible', !show);
});
scrollBottomBtn.addEventListener('click', () => scrollToBottom(true));

// Sidebar & Header buttons
document.getElementById('new-chat-btn').addEventListener('click', () => {
    startNewChat();
    closeMobileSidebar();
});
document.getElementById('sidebar-toggle-btn').addEventListener('click', () => {
    if (window.innerWidth < 1024) {
        openMobileSidebar();
    } else {
        sidebar.classList.toggle('collapsed');
    }
});
document.getElementById('sidebar-close-mobile').addEventListener('click', closeMobileSidebar);
sidebarBackdrop.addEventListener('click', closeMobileSidebar);

convSearchInput.addEventListener('input', () => {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        store.searchQuery = convSearchInput.value.trim();
        refreshConversations();
    }, 250);
});

document.getElementById('clear-all-convs-btn').addEventListener('click', async () => {
    if (!store.conversations.length) return;
    if (!window.confirm('确定要清空所有历史会话吗？此操作不可撤销。')) return;
    try {
        await api.clearAllConversations();
        startNewChat();
        await refreshConversations();
        ui.showToast('已清空所有会话', 'info');
    } catch (err) {
        ui.showToast(err.message, 'error');
    }
});

// Export buttons
async function handleExport(format) {
    if (!store.activeConversationId) {
        ui.showToast('请先选择或开始一段对话后再导出', 'info');
        return;
    }
    try {
        await api.downloadConversationExport(
            store.activeConversationId,
            format,
            activeConvTitleEl.textContent || 'conversation'
        );
        ui.showToast(`已导出 ${format.toUpperCase()} 文件`);
    } catch (err) {
        ui.showToast(err.message, 'error');
    }
}
document.getElementById('export-md-btn').addEventListener('click', () => handleExport('markdown'));
document.getElementById('export-json-btn').addEventListener('click', () => handleExport('json'));

// Theme toggle
document.getElementById('theme-toggle').addEventListener('click', () => {
    const html = document.documentElement;
    const isDark = html.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark);
});

// Auth modal events
document.getElementById('user-account-btn').addEventListener('click', () => {
    if (store.user.is_guest) {
        setAuthTab('login');
        toggleModal('auth-modal', true);
    } else {
        ui.showToast(`当前已登录：${store.user.display_name || store.user.username}`, 'info');
    }
});
document.getElementById('auth-modal-close').addEventListener('click', () => toggleModal('auth-modal', false));
document.getElementById('auth-tab-login').addEventListener('click', () => setAuthTab('login'));
document.getElementById('auth-tab-register').addEventListener('click', () => setAuthTab('register'));

document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('auth-error');
    errEl.classList.add('hidden');

    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    const display_name = document.getElementById('auth-display-name').value.trim() || null;
    const email = document.getElementById('auth-email').value.trim() || null;

    try {
        const res =
            authMode === 'login'
                ? await api.loginUser({ username, password })
                : await api.registerUser({ username, password, display_name, email });

        api.setAuthToken(res.access_token);
        store.user = res.user;
        ui.renderUserAccountBar();
        toggleModal('auth-modal', false);
        document.getElementById('auth-form').reset();

        const migratedNote =
            res.migrated_conversations > 0
                ? `（已自动迁移 ${res.migrated_conversations} 条游客对话）`
                : '';
        ui.showToast(`${authMode === 'login' ? '登录成功' : '注册成功'}${migratedNote}`);

        await refreshPersonasAndModels();
        await refreshConversations();
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
    }
});

document.getElementById('logout-btn').addEventListener('click', async () => {
    api.setAuthToken('');
    store.user = { id: 'guest', username: 'guest', display_name: '游客体验模式', is_guest: true };
    ui.renderUserAccountBar();
    startNewChat();
    await refreshPersonasAndModels();
    await refreshConversations();
    ui.showToast('已退出登录，切换回游客模式', 'info');
});

// Persona Studio modal events
document.getElementById('open-persona-studio-btn').addEventListener('click', () => {
    resetPersonaForm();
    renderPersonaStudio();
    toggleModal('persona-modal', true);
    closeMobileSidebar();
});
document.getElementById('persona-modal-close').addEventListener('click', () => toggleModal('persona-modal', false));
document.getElementById('persona-reset-btn').addEventListener('click', resetPersonaForm);

document.getElementById('persona-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const editId = document.getElementById('persona-edit-id').value.trim();
    const payload = {
        name: document.getElementById('persona-name').value.trim(),
        title: document.getElementById('persona-title').value.trim(),
        description: document.getElementById('persona-desc').value.trim(),
        system_prompt: document.getElementById('persona-prompt').value.trim(),
        default_model: document.getElementById('persona-model').value,
        icon: document.getElementById('persona-icon-picker').value,
        bg_gradient: document.getElementById('persona-gradient-picker').value,
    };

    try {
        if (editId) {
            await api.updatePersona(editId, payload);
            ui.showToast('自定义角色已更新');
        } else {
            const created = await api.createPersona(payload);
            store.selectedPersonaId = created.id;
            ui.showToast(`已创建角色：${created.name}`);
        }
        resetPersonaForm();
        await refreshPersonasAndModels();
        renderPersonaStudio();
        if (!store.messages.length) renderMessagesFeed();
    } catch (err) {
        ui.showToast(err.message, 'error');
    }
});

// Settings modal events
const tempSlider = document.getElementById('setting-temperature');
const tempVal = document.getElementById('setting-temperature-val');
const histSlider = document.getElementById('setting-max-history');
const histVal = document.getElementById('setting-max-history-val');

tempSlider.addEventListener('input', () => {
    tempVal.textContent = tempSlider.value;
});
histSlider.addEventListener('input', () => {
    histVal.textContent = histSlider.value;
});

document.getElementById('open-settings-btn').addEventListener('click', () => {
    tempSlider.value = String(store.settings.temperature);
    tempVal.textContent = String(store.settings.temperature);
    histSlider.value = String(store.settings.maxHistory);
    histVal.textContent = String(store.settings.maxHistory);
    document.getElementById('setting-system-prompt').value = store.settings.systemPromptOverride || '';
    ui.renderProviderDiagnostics();
    toggleModal('settings-modal', true);
    closeMobileSidebar();
});
document.getElementById('settings-modal-close').addEventListener('click', () => toggleModal('settings-modal', false));

document.getElementById('settings-save-btn').addEventListener('click', async () => {
    const temperature = parseFloat(tempSlider.value);
    const maxHistory = parseInt(histSlider.value, 10);
    const systemPromptOverride = document.getElementById('setting-system-prompt').value.trim();

    store.saveSettings({ temperature, maxHistory, systemPromptOverride });

    if (store.activeConversationId) {
        try {
            await api.updateConversation(store.activeConversationId, {
                temperature,
                system_prompt_override: systemPromptOverride || null,
            });
        } catch (err) {
            ui.showToast(err.message, 'error');
            return;
        }
    }
    toggleModal('settings-modal', false);
    ui.showToast('参数设置已保存');
});

// Lightbox modal events
document.getElementById('lightbox-close').addEventListener('click', ui.closeLightbox);
document.getElementById('lightbox-modal').addEventListener('click', (e) => {
    if (e.target.id === 'lightbox-modal') ui.closeLightbox();
});

// Global keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        startNewChat();
    } else if (e.key === 'Escape') {
        closeHeaderDropdowns();
        ui.closeLightbox();
        toggleModal('auth-modal', false);
        toggleModal('persona-modal', false);
        toggleModal('settings-modal', false);
        closeMobileSidebar();
    }
});

// Boot application
bootstrap();
