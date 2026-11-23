/**
 * Centralized client state and user preference persistence.
 */

const SETTINGS_KEY = 'chat_assistant_settings';

function loadSettings() {
    const defaults = {
        temperature: 0.7,
        maxHistory: 20,
        webSearchMode: 'auto', // 'auto' | 'on' | 'off'
        imageMode: 'auto', // 'auto' | 'generate' | 'off'
        systemPromptOverride: '',
    };
    try {
        const raw = localStorage.getItem(SETTINGS_KEY);
        if (!raw) return defaults;
        return { ...defaults, ...JSON.parse(raw) };
    } catch {
        return defaults;
    }
}

export const store = {
    user: {
        id: 'guest',
        username: 'guest',
        display_name: '游客体验模式',
        is_guest: true,
    },
    models: [],
    personas: [],
    webSearchEnabled: false,
    visionEnabled: false,

    conversations: [],
    activeConversationId: null,
    activeConversation: null,
    messages: [],

    selectedModel: 'deepseek',
    selectedPersonaId: 'deepseek',
    uploadedImages: [],

    isStreaming: false,
    abortController: null,
    searchQuery: '',

    settings: loadSettings(),

    saveSettings(partial = {}) {
        this.settings = { ...this.settings, ...partial };
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings));
    },

    getActivePersona() {
        return (
            this.personas.find((p) => p.id === this.selectedPersonaId) ||
            this.personas[0] || {
                id: 'deepseek',
                name: 'Zoe',
                title: '暖心搭子',
                description: '你的智能 AI 助手',
                greeting: '你好，我是你的 AI 智能助手！',
                icon: 'fa-robot',
                bg_gradient: 'bg-gradient-to-br from-violet-500 to-indigo-600',
                default_model: 'deepseek',
                starters: [],
            }
        );
    },

    getModelInfo(modelId) {
        return (
            this.models.find((m) => m.value === modelId) || {
                value: modelId || 'deepseek',
                label: modelId || 'DeepSeek',
                configured: false,
            }
        );
    },
};
