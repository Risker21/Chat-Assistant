/**
 * UI rendering helpers: toasts, sidebar groups, welcome screen, message bubbles, citations, modals.
 */

import { enhanceMarkdownContainer, escapeHtml, renderMarkdownHtml } from './markdown.js';
import { store } from './store.js';

export function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const iconMap = {
        success: 'fa-circle-check text-emerald-500',
        error: 'fa-circle-exclamation text-rose-500',
        info: 'fa-circle-info text-violet-500',
    };
    const toast = document.createElement('div');
    toast.className =
        'pointer-events-auto bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border shadow-xl rounded-xl px-4 py-2.5 flex items-center gap-2.5 animate-fade-in-up text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-100';
    toast.innerHTML = `<i class="fa-solid ${iconMap[type] || iconMap.info}"></i><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'transition-opacity', 'duration-300');
        setTimeout(() => toast.remove(), 300);
    }, 2400);
}

export function openLightbox(imageUrl, caption = '') {
    const modal = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    const cap = document.getElementById('lightbox-caption');
    const dl = document.getElementById('lightbox-download');
    if (!modal || !img) return;

    img.src = imageUrl;
    cap.textContent = caption || '';
    dl.href = imageUrl;
    dl.download = `image-${Date.now()}.png`;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

export function closeLightbox() {
    const modal = document.getElementById('lightbox-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

export function renderSelectors(handlers = {}) {
    const personaBtnBadge = document.getElementById('persona-btn-badge');
    const personaBtnIcon = document.getElementById('persona-btn-icon');
    const personaBtnLabel = document.getElementById('persona-btn-label');
    const personaListEl = document.getElementById('persona-dropdown-list');

    const modelBtnLabel = document.getElementById('model-btn-label');
    const modelListEl = document.getElementById('model-dropdown-list');
    const personaFormModel = document.getElementById('persona-model');

    const activePersona = store.getActivePersona();
    if (personaBtnBadge) {
        personaBtnBadge.className = `w-5 h-5 rounded-md ${activePersona.bg_gradient || 'bg-gradient-to-br from-violet-500 to-indigo-600'} text-white flex items-center justify-center text-[10px] shrink-0`;
    }
    if (personaBtnIcon) {
        personaBtnIcon.className = `fa-solid ${activePersona.icon || 'fa-sparkles'}`;
    }
    if (personaBtnLabel) {
        personaBtnLabel.textContent = `${activePersona.name} · ${activePersona.title}`;
    }

    if (personaListEl) {
        personaListEl.innerHTML = '';
        store.personas.forEach((p) => {
            const isSelected = p.id === store.selectedPersonaId;
            const item = document.createElement('button');
            item.type = 'button';
            item.className = `w-full text-left flex items-center gap-2.5 px-2.5 py-2 rounded-xl transition-colors ${
                isSelected
                    ? 'bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300'
                    : 'hover:bg-slate-100 dark:hover:bg-dark-card text-slate-700 dark:text-slate-200'
            }`;
            item.innerHTML = `
                <span class="w-8 h-8 rounded-lg ${escapeHtml(p.bg_gradient)} text-white flex items-center justify-center text-xs shrink-0">
                    <i class="fa-solid ${escapeHtml(p.icon || 'fa-sparkles')}"></i>
                </span>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-1.5">
                        <span class="text-xs font-semibold truncate">${escapeHtml(p.name)}</span>
                        <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-200/70 dark:bg-dark-card text-slate-500 dark:text-slate-400 shrink-0">${escapeHtml(p.title)}</span>
                    </div>
                    <p class="text-[11px] text-slate-400 dark:text-slate-500 truncate mt-0.5">${escapeHtml(p.description || p.system_prompt)}</p>
                </div>
                ${isSelected ? '<i class="fa-solid fa-check text-violet-600 dark:text-violet-400 text-xs shrink-0"></i>' : ''}
            `;
            item.addEventListener('click', () => {
                if (typeof handlers.onSelectPersona === 'function') {
                    handlers.onSelectPersona(p);
                }
            });
            personaListEl.appendChild(item);
        });
    }

    const activeModel = store.getModelInfo(store.selectedModel);
    if (modelBtnLabel) {
        modelBtnLabel.textContent = activeModel.label || store.selectedModel;
    }

    if (modelListEl) {
        modelListEl.innerHTML = '';
        store.models.forEach((m) => {
            const isSelected = m.value === store.selectedModel;
            const item = document.createElement('button');
            item.type = 'button';
            item.className = `w-full text-left flex items-center gap-2.5 px-2.5 py-2 rounded-xl transition-colors ${
                isSelected
                    ? 'bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300'
                    : 'hover:bg-slate-100 dark:hover:bg-dark-card text-slate-700 dark:text-slate-200'
            }`;
            item.innerHTML = `
                <span class="w-2 h-2 rounded-full ${m.configured ? 'bg-emerald-400' : 'bg-amber-400'} shrink-0"></span>
                <div class="flex-1 min-w-0">
                    <div class="text-xs font-semibold truncate">${escapeHtml(m.label)}</div>
                    <div class="text-[10px] text-slate-400 truncate">${escapeHtml(m.model_name)}</div>
                </div>
                <span class="text-[10px] px-1.5 py-0.5 rounded-md shrink-0 ${
                    m.configured
                        ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400'
                        : 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400'
                }">${m.configured ? '已就绪' : '未配置'}</span>
                ${isSelected ? '<i class="fa-solid fa-check text-violet-600 dark:text-violet-400 text-xs shrink-0"></i>' : ''}
            `;
            item.addEventListener('click', () => {
                if (typeof handlers.onSelectModel === 'function') {
                    handlers.onSelectModel(m);
                }
            });
            modelListEl.appendChild(item);
        });
    }

    if (personaFormModel) {
        personaFormModel.innerHTML = store.models
            .map(
                (m) =>
                    `<option value="${escapeHtml(m.value)}" class="text-slate-900">${escapeHtml(m.label)}${m.configured ? '' : ' (未配置Key)'}</option>`
            )
            .join('');
    }

    updateModelStatusDot();
}

export function updateModelStatusDot() {
    const dot = document.getElementById('model-status-dot');
    if (!dot) return;
    const info = store.getModelInfo(store.selectedModel);
    if (info.configured) {
        dot.className = 'w-2 h-2 rounded-full bg-emerald-400 shrink-0';
        dot.title = `${info.label} (${info.model_name}) 已就绪`;
    } else {
        dot.className = 'w-2 h-2 rounded-full bg-amber-400 shrink-0';
        dot.title = `${info.label} 尚未配置 API Key`;
    }
}

export function renderWelcomeScreen(onStarterClick) {
    const persona = store.getActivePersona();
    const avatar = document.getElementById('welcome-avatar');
    const icon = document.getElementById('welcome-icon');
    const title = document.getElementById('welcome-title');
    const greeting = document.getElementById('welcome-greeting');
    const startersEl = document.getElementById('welcome-starters');

    if (avatar) {
        avatar.className = `w-20 h-20 rounded-3xl ${persona.bg_gradient || 'bg-gradient-to-br from-violet-500 to-indigo-600'} flex items-center justify-center shadow-xl shadow-violet-500/20 mb-5`;
    }
    if (icon) {
        icon.className = `fa-solid ${persona.icon || 'fa-sparkles'} text-white text-3xl`;
    }
    if (title) {
        title.textContent = `${persona.name} · ${persona.title}`;
    }
    if (greeting) {
        greeting.textContent = persona.greeting || persona.description || '有什么我可以帮你的？';
    }

    const starters =
        persona.starters && persona.starters.length > 0
            ? persona.starters
            : [
                  { title: '高效写作', prompt: '帮我写一段简洁有感染力的项目介绍', icon: 'fa-pen-nib', color: 'violet' },
                  { title: '代码助手', prompt: '用 Python 写一个支持重试和超时的异步 HTTP 请求工具函数', icon: 'fa-code', color: 'blue' },
                  { title: '概念讲解', prompt: '用通俗易懂的例子解释 Transformer 中的自注意力机制', icon: 'fa-brain', color: 'emerald' },
                  { title: '联网查询', prompt: '帮我查一下今天北京的天气怎么样', icon: 'fa-globe', color: 'amber' },
              ];

    const colorMap = {
        amber: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
        blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
        emerald: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
        pink: 'bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400',
        rose: 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400',
        indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
        violet: 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400',
    };

    if (startersEl) {
        startersEl.innerHTML = '';
        starters.forEach((item) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className =
                'group text-left p-4 rounded-2xl bg-white dark:bg-dark-card border border-slate-200/80 dark:border-dark-border hover:border-violet-400 dark:hover:border-violet-500 shadow-xs hover:shadow-md transition-all duration-200 hover:-translate-y-0.5';
            btn.innerHTML = `
                <div class="flex items-center gap-2.5 mb-1.5">
                    <div class="w-8 h-8 rounded-lg ${colorMap[item.color] || colorMap.violet} flex items-center justify-center shrink-0">
                        <i class="fa-solid ${escapeHtml(item.icon || 'fa-sparkles')} text-xs"></i>
                    </div>
                    <span class="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-violet-600 dark:group-hover:text-violet-400 transition-colors">${escapeHtml(item.title)}</span>
                </div>
                <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 pl-10">${escapeHtml(item.prompt)}</p>
            `;
            btn.addEventListener('click', () => onStarterClick(item.prompt));
            startersEl.appendChild(btn);
        });
    }
}

export function renderUserAccountBar() {
    const avatar = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-display-name');
    const statusEl = document.getElementById('user-status-label');
    const logoutBtn = document.getElementById('logout-btn');

    if (store.user.is_guest) {
        if (avatar) {
            avatar.className = 'w-8 h-8 rounded-lg bg-gradient-to-br from-slate-400 to-slate-500 text-white flex items-center justify-center text-xs font-bold shrink-0';
            avatar.innerHTML = '<i class="fa-solid fa-user"></i>';
        }
        if (nameEl) nameEl.textContent = '游客体验模式';
        if (statusEl) statusEl.textContent = '点击登录同步历史';
        if (logoutBtn) logoutBtn.classList.add('hidden');
    } else {
        const display = store.user.display_name || store.user.username;
        if (avatar) {
            avatar.className = 'w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 text-white flex items-center justify-center text-xs font-bold shrink-0';
            avatar.textContent = display.slice(0, 1).toUpperCase();
        }
        if (nameEl) nameEl.textContent = display;
        if (statusEl) statusEl.textContent = `@${store.user.username}`;
        if (logoutBtn) logoutBtn.classList.remove('hidden');
    }
}

function classifyConversationGroup(conv) {
    if (conv.pinned) return '置顶';
    const updated = new Date(conv.updated_at);
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfYesterday = new Date(startOfToday.getTime() - 86400000);
    if (updated >= startOfToday) return '今天';
    if (updated >= startOfYesterday) return '昨天';
    return '更早';
}

export function renderConversationSidebar(handlers) {
    const listEl = document.getElementById('conversation-list');
    if (!listEl) return;

    if (!store.conversations.length) {
        listEl.innerHTML = `
            <div class="text-center py-10 px-4 text-xs text-slate-400 dark:text-slate-500">
                <i class="fa-regular fa-comments text-2xl mb-2 block opacity-50"></i>
                ${store.searchQuery ? '没有匹配的对话记录' : '暂无历史对话，发送消息开始聊天'}
            </div>
        `;
        return;
    }

    const groups = { 置顶: [], 今天: [], 昨天: [], 更早: [] };
    store.conversations.forEach((c) => {
        const group = classifyConversationGroup(c);
        groups[group].push(c);
    });

    listEl.innerHTML = '';
    ['置顶', '今天', '昨天', '更早'].forEach((groupName) => {
        const items = groups[groupName];
        if (!items.length) return;

        const section = document.createElement('div');
        section.innerHTML = `<div class="px-2.5 mb-1 text-[11px] font-semibold text-slate-400 dark:text-slate-500">${groupName}</div>`;

        const stack = document.createElement('div');
        stack.className = 'space-y-0.5';

        items.forEach((conv) => {
            const isActive = conv.id === store.activeConversationId;
            const row = document.createElement('div');
            row.className = `group flex items-center gap-2 px-2.5 py-2 rounded-xl cursor-pointer transition-colors ${
                isActive
                    ? 'bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300 font-medium'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100/80 dark:hover:bg-dark-card'
            }`;

            const pinIcon = conv.pinned ? '<i class="fa-solid fa-thumbtack text-[10px] text-violet-500 shrink-0"></i>' : '<i class="fa-regular fa-message text-[11px] opacity-60 shrink-0"></i>';

            row.innerHTML = `
                ${pinIcon}
                <span class="text-xs truncate flex-1">${escapeHtml(conv.title)}</span>
                <div class="hidden group-hover:flex items-center gap-0.5 shrink-0">
                    <button type="button" data-action="pin" class="w-6 h-6 rounded-md hover:bg-white dark:hover:bg-dark-surface flex items-center justify-center text-[11px] text-slate-400 hover:text-violet-500" title="${conv.pinned ? '取消置顶' : '置顶'}">
                        <i class="fa-solid fa-thumbtack"></i>
                    </button>
                    <button type="button" data-action="rename" class="w-6 h-6 rounded-md hover:bg-white dark:hover:bg-dark-surface flex items-center justify-center text-[11px] text-slate-400 hover:text-blue-500" title="重命名">
                        <i class="fa-regular fa-pen-to-square"></i>
                    </button>
                    <button type="button" data-action="delete" class="w-6 h-6 rounded-md hover:bg-white dark:hover:bg-dark-surface flex items-center justify-center text-[11px] text-slate-400 hover:text-rose-500" title="删除">
                        <i class="fa-regular fa-trash-can"></i>
                    </button>
                </div>
            `;

            row.addEventListener('click', (e) => {
                const actionBtn = e.target.closest('button[data-action]');
                if (actionBtn) {
                    e.stopPropagation();
                    const action = actionBtn.getAttribute('data-action');
                    if (action === 'pin') handlers.onPin(conv);
                    if (action === 'rename') handlers.onRename(conv);
                    if (action === 'delete') handlers.onDelete(conv);
                    return;
                }
                handlers.onSelect(conv);
            });

            stack.appendChild(row);
        });

        section.appendChild(stack);
        listEl.appendChild(section);
    });
}

function buildSourcesHtml(sources) {
    if (!sources || !sources.length) return '';
    const chips = sources
        .map((src, idx) => {
            let domain = '';
            try {
                domain = src.url ? new URL(src.url).hostname.replace(/^www\./, '') : '';
            } catch {
                domain = '';
            }
            return `
                <a href="${escapeHtml(src.url || '#')}" target="_blank" rel="noopener noreferrer"
                   class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-dark-surface hover:bg-violet-50 dark:hover:bg-violet-950/40 border border-slate-200/80 dark:border-dark-border text-[11px] text-slate-600 dark:text-slate-300 hover:text-violet-600 dark:hover:text-violet-300 transition-colors max-w-[230px]">
                    <span class="w-4 h-4 rounded bg-violet-100 dark:bg-violet-900/50 text-violet-600 dark:text-violet-300 flex items-center justify-center text-[10px] font-bold shrink-0">${idx + 1}</span>
                    <span class="truncate">${escapeHtml(src.title || domain || '来源')}</span>
                </a>
            `;
        })
        .join('');

    return `
        <details class="mb-3 rounded-xl bg-slate-50/90 dark:bg-dark-surface/70 border border-slate-200/70 dark:border-dark-border px-3 py-2" open>
            <summary class="text-xs font-medium text-slate-500 dark:text-slate-400 cursor-pointer flex items-center gap-1.5 select-none">
                <i class="fa-solid fa-globe text-violet-500"></i>
                <span>已参考 ${sources.length} 条联网来源</span>
            </summary>
            <div class="flex flex-wrap gap-1.5 mt-2">${chips}</div>
        </details>
    `;
}

export function createMessageElement(msg, handlers, { isLastAssistant = false, isStreaming = false } = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex w-full animate-fade-in-up group';
    if (msg.id) wrapper.dataset.messageId = msg.id;

    if (msg.role === 'user') {
        const imagesHtml =
            msg.images && msg.images.length
                ? `<div class="flex flex-wrap gap-2 mb-2 justify-end">
                    ${msg.images
                        .map(
                            (img) =>
                                `<img src="${escapeHtml(img)}" class="user-msg-img w-32 h-32 object-cover rounded-xl border border-slate-200 dark:border-dark-border shadow-xs cursor-zoom-in hover:opacity-90 transition-opacity">`
                        )
                        .join('')}
                   </div>`
                : '';

        wrapper.innerHTML = `
            <div class="flex max-w-full w-full justify-end">
                <div class="max-w-[85%] sm:max-w-[78%] flex flex-col items-end">
                    ${imagesHtml}
                    <div class="bg-gradient-to-br from-violet-600 to-indigo-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-sm text-sm sm:text-[15px] leading-relaxed whitespace-pre-wrap break-words">${escapeHtml(msg.content)}</div>
                    <div class="flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button type="button" data-action="copy" class="px-2 py-1 rounded-md text-[11px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-dark-card" title="复制"><i class="fa-regular fa-copy"></i></button>
                        ${msg.id ? `<button type="button" data-action="edit" class="px-2 py-1 rounded-md text-[11px] text-slate-400 hover:text-violet-600 hover:bg-slate-100 dark:hover:bg-dark-card" title="编辑并重新发送"><i class="fa-regular fa-pen-to-square"></i></button>` : ''}
                        ${msg.id ? `<button type="button" data-action="delete" class="px-2 py-1 rounded-md text-[11px] text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-dark-card" title="删除"><i class="fa-regular fa-trash-can"></i></button>` : ''}
                    </div>
                </div>
            </div>
        `;

        wrapper.querySelectorAll('.user-msg-img').forEach((imgEl) => {
            imgEl.addEventListener('click', () => openLightbox(imgEl.src, '上传的图片'));
        });

        wrapper.querySelectorAll('button[data-action]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const action = btn.getAttribute('data-action');
                if (action === 'copy') handlers.onCopy(msg.content);
                if (action === 'edit') handlers.onEdit(msg);
                if (action === 'delete') handlers.onDelete(msg);
            });
        });

        return wrapper;
    }

    // Assistant message
    const persona = store.getActivePersona();
    const isError = msg.msg_type === 'error';
    const avatarBg = isError ? 'bg-gradient-to-br from-rose-500 to-red-600' : persona.bg_gradient;
    const avatarIcon = isError ? 'fa-triangle-exclamation' : persona.icon || 'fa-sparkles';
    const modelLabel = msg.model ? store.getModelInfo(msg.model).label : '';
    const latencyBadge = msg.latency_ms ? `<span class="text-[10px] text-slate-400">${(msg.latency_ms / 1000).toFixed(1)}s</span>` : '';

    let bodyHtml = '';
    if (msg.msg_type === 'image' && msg.image_url) {
        bodyHtml = `
            <p class="text-xs text-slate-500 dark:text-slate-400 mb-2.5 italic">“${escapeHtml(msg.image_prompt || msg.content)}”</p>
            <div class="relative inline-block group/img">
                <img src="${escapeHtml(msg.image_url)}" alt="AI 生成图片" class="gen-msg-img max-w-full max-h-[420px] rounded-xl shadow-md cursor-zoom-in">
            </div>
        `;
    } else {
        bodyHtml = `<div class="markdown-body text-slate-800 dark:text-slate-100 ${isStreaming ? 'stream-cursor' : ''}">${renderMarkdownHtml(msg.content)}</div>`;
    }

    wrapper.innerHTML = `
        <div class="flex gap-3 w-full">
            <div class="w-9 h-9 ${avatarBg} rounded-xl flex items-center justify-center text-white shadow-sm shrink-0 mt-0.5">
                <i class="fa-solid ${avatarIcon} text-xs"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1.5">
                    <span class="text-xs font-semibold text-slate-700 dark:text-slate-200">${escapeHtml(persona.name)}</span>
                    ${modelLabel ? `<span class="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-dark-card text-slate-500 dark:text-slate-400">${escapeHtml(modelLabel)}</span>` : ''}
                    ${latencyBadge}
                </div>
                <div class="msg-status-slot"></div>
                <div class="msg-sources-slot">${buildSourcesHtml(msg.sources)}</div>
                <div class="bg-white dark:bg-dark-card rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-xs border border-slate-200/70 dark:border-dark-border msg-card-body">
                    ${bodyHtml}
                </div>
                <div class="msg-actions flex items-center gap-1 mt-1.5 ${isStreaming ? 'hidden' : 'opacity-0 group-hover:opacity-100'} transition-opacity">
                    <button type="button" data-action="copy" class="px-2 py-1 rounded-md text-[11px] text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-dark-card flex items-center gap-1" title="复制 Markdown">
                        <i class="fa-regular fa-copy"></i><span>复制</span>
                    </button>
                    ${isLastAssistant ? `<button type="button" data-action="regenerate" class="px-2 py-1 rounded-md text-[11px] text-slate-400 hover:text-violet-600 hover:bg-slate-100 dark:hover:bg-dark-card flex items-center gap-1" title="重新生成"><i class="fa-solid fa-rotate-right"></i><span>重试</span></button>` : ''}
                    ${msg.id ? `<button type="button" data-action="delete" class="px-2 py-1 rounded-md text-[11px] text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-dark-card" title="删除消息"><i class="fa-regular fa-trash-can"></i></button>` : ''}
                </div>
            </div>
        </div>
    `;

    const mdContainer = wrapper.querySelector('.markdown-body');
    if (mdContainer && !isStreaming) {
        enhanceMarkdownContainer(mdContainer, showToast);
    }

    const genImg = wrapper.querySelector('.gen-msg-img');
    if (genImg) {
        genImg.addEventListener('click', () => openLightbox(msg.image_url, msg.image_prompt || msg.content));
    }

    wrapper.querySelectorAll('button[data-action]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-action');
            if (action === 'copy') handlers.onCopy(msg.content || msg.image_url || '');
            if (action === 'regenerate') handlers.onRegenerate();
            if (action === 'delete') handlers.onDelete(msg);
        });
    });

    return wrapper;
}

export function setAssistantStatus(wrapper, stage, text) {
    const slot = wrapper.querySelector('.msg-status-slot');
    if (!slot) return;
    if (!text) {
        slot.innerHTML = '';
        return;
    }
    const icons = {
        searching: 'fa-globe fa-spin text-blue-500',
        generating_image: 'fa-wand-magic-sparkles fa-beat text-violet-500',
        analyzing_image: 'fa-eye fa-pulse text-emerald-500',
        thinking: 'fa-brain fa-pulse text-violet-500',
    };
    slot.innerHTML = `
        <div class="mb-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-violet-50/90 dark:bg-violet-950/30 border border-violet-200/60 dark:border-violet-800/40 text-xs text-violet-700 dark:text-violet-300">
            <i class="fa-solid ${icons[stage] || icons.thinking}"></i>
            <span>${escapeHtml(text)}</span>
        </div>
    `;
}

export function setAssistantSources(wrapper, sources) {
    const slot = wrapper.querySelector('.msg-sources-slot');
    if (!slot) return;
    slot.innerHTML = buildSourcesHtml(sources);
}

export function renderImagePreviews(onRemove) {
    const container = document.getElementById('image-preview-container');
    const list = document.getElementById('image-preview-list');
    if (!container || !list) return;

    if (!store.uploadedImages.length) {
        container.classList.add('hidden');
        list.innerHTML = '';
        return;
    }

    container.classList.remove('hidden');
    list.innerHTML = '';
    store.uploadedImages.forEach((img, index) => {
        const item = document.createElement('div');
        item.className = 'relative group';
        item.innerHTML = `
            <img src="${escapeHtml(img)}" class="w-16 h-16 object-cover rounded-xl border border-slate-200 dark:border-dark-border shadow-xs">
            <button type="button" class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-rose-500 text-white text-[10px] flex items-center justify-center shadow-sm hover:scale-110 transition-transform">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;
        item.querySelector('button').addEventListener('click', () => onRemove(index));
        list.appendChild(item);
    });
}

export function renderPersonaStudioList(handlers) {
    const listEl = document.getElementById('persona-list');
    if (!listEl) return;

    listEl.innerHTML = '';
    store.personas.forEach((p) => {
        const isSelected = p.id === store.selectedPersonaId;
        const card = document.createElement('div');
        card.className = `p-3 rounded-xl border transition-all cursor-pointer ${
            isSelected
                ? 'border-violet-500 bg-violet-50/70 dark:bg-violet-950/30'
                : 'border-slate-200 dark:border-dark-border hover:border-violet-300 bg-slate-50/60 dark:bg-dark-card/70'
        }`;

        card.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="w-10 h-10 rounded-xl ${escapeHtml(p.bg_gradient)} flex items-center justify-center text-white shrink-0">
                    <i class="fa-solid ${escapeHtml(p.icon)}"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-1.5 min-w-0">
                            <span class="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">${escapeHtml(p.name)}</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-200/80 dark:bg-dark-surface text-slate-600 dark:text-slate-300 shrink-0">${escapeHtml(p.title)}</span>
                            ${p.is_builtin ? '' : '<span class="text-[10px] text-violet-500 font-medium">自定义</span>'}
                        </div>
                        ${
                            p.is_builtin
                                ? ''
                                : `<div class="flex items-center gap-1 shrink-0">
                                    <button type="button" data-action="edit" class="w-6 h-6 rounded hover:bg-white dark:hover:bg-dark-surface text-slate-400 hover:text-blue-500"><i class="fa-regular fa-pen-to-square text-xs"></i></button>
                                    <button type="button" data-action="delete" class="w-6 h-6 rounded hover:bg-white dark:hover:bg-dark-surface text-slate-400 hover:text-rose-500"><i class="fa-regular fa-trash-can text-xs"></i></button>
                                   </div>`
                        }
                    </div>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">${escapeHtml(p.description || p.system_prompt)}</p>
                </div>
            </div>
        `;

        card.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (btn) {
                e.stopPropagation();
                if (btn.dataset.action === 'edit') handlers.onEdit(p);
                if (btn.dataset.action === 'delete') handlers.onDelete(p);
                return;
            }
            handlers.onActivate(p);
        });
        listEl.appendChild(card);
    });
}

export function renderProviderDiagnostics() {
    const container = document.getElementById('provider-diagnostics');
    if (!container) return;

    const items = store.models.map((m) => ({
        name: `${m.label} (${m.model_name})`,
        ok: m.configured,
    }));
    items.push({ name: '多模态视觉 (Qwen-VL)', ok: store.visionEnabled });
    items.push({ name: '联网搜索 (Tavily)', ok: store.webSearchEnabled });

    container.innerHTML = items
        .map(
            (item) => `
            <div class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-slate-50 dark:bg-dark-card border border-slate-200/70 dark:border-dark-border">
                <span class="truncate text-slate-600 dark:text-slate-300" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
                <span class="shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded-md ${
                    item.ok
                        ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400'
                        : 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400'
                }">${item.ok ? '已配置' : '未配置'}</span>
            </div>
        `
        )
        .join('');
}
