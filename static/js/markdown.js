/**
 * Safe Markdown + KaTeX LaTeX math + Highlight.js code blocks with copy button.
 */

export function escapeHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

if (window.marked) {
    window.marked.setOptions({
        breaks: true,
        gfm: true,
    });
}

function renderLatexToHtml(tex, displayMode) {
    if (!window.katex) {
        return escapeHtml(displayMode ? `$$${tex}$$` : `$${tex}$`);
    }
    try {
        return window.katex.renderToString(tex.trim(), {
            displayMode,
            throwOnError: false,
            strict: false,
        });
    } catch {
        return escapeHtml(tex);
    }
}

/**
 * Extract math expressions before marked runs so underscores/backslashes aren't mangled.
 */
function preprocessMath(markdown) {
    const placeholders = [];
    const codeSpans = [];

    // Preserve fenced code blocks and inline code so `$VAR` inside code isn't treated as math
    let text = markdown.replace(/```[\s\S]*?```|`[^`\n]+`/g, (match) => {
        const idx = codeSpans.push(match) - 1;
        return `@@CODESPAN_${idx}@@`;
    });

    // Display math: $$...$$ and \[...\]
    text = text.replace(/\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g, (_, a, b) => {
        const idx = placeholders.push(renderLatexToHtml(a ?? b, true)) - 1;
        return `@@MATHBLOCK_${idx}@@`;
    });

    // Inline math: $...$ (single line, non-empty, not preceded by digit/escape) and \(...\)
    text = text.replace(/\\\((.+?)\\\)|(?<![\\$])\$([^\s$][^$\n]*?[^\s$]|[^\s$])\$(?!\d)/g, (_, a, b) => {
        const idx = placeholders.push(renderLatexToHtml(a ?? b, false)) - 1;
        return `@@MATHBLOCK_${idx}@@`;
    });

    // Restore code spans
    text = text.replace(/@@CODESPAN_(\d+)@@/g, (_, idx) => codeSpans[Number(idx)]);

    return { text, placeholders };
}

export function renderMarkdownHtml(rawText) {
    const source = String(rawText ?? '');
    if (!source) return '';

    const { text, placeholders } = preprocessMath(source);
    const parsed = window.marked ? window.marked.parse(text) : escapeHtml(text).replace(/\n/g, '<br>');

    let sanitized = window.DOMPurify
        ? window.DOMPurify.sanitize(parsed, {
              ADD_TAGS: ['span', 'math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'msqrt', 'annotation'],
              ADD_ATTR: ['class', 'style', 'aria-hidden', 'encoding', 'target', 'rel'],
          })
        : parsed;

    sanitized = sanitized.replace(/@@MATHBLOCK_(\d+)@@/g, (_, idx) => placeholders[Number(idx)] || '');
    return sanitized;
}

/**
 * Enhance rendered markdown container: syntax highlight, safe external links, code copy headers.
 */
export function enhanceMarkdownContainer(container, onCopyFeedback) {
    if (!container) return;

    // Make external links open in a new tab safely
    container.querySelectorAll('a').forEach((link) => {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener noreferrer');
    });

    // Wrap <pre><code> with header + language badge + copy button
    container.querySelectorAll('pre').forEach((pre) => {
        if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) {
            return;
        }
        const codeEl = pre.querySelector('code');
        if (!codeEl) return;

        let lang = 'code';
        const langMatch = (codeEl.className || '').match(/language-([a-zA-Z0-9_+-]+)/);
        if (langMatch) {
            lang = langMatch[1];
        }

        if (window.hljs) {
            try {
                window.hljs.highlightElement(codeEl);
            } catch {
                // ignore highlight failure
            }
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';

        const header = document.createElement('div');
        header.className = 'code-block-header';

        const langSpan = document.createElement('span');
        langSpan.className = 'font-mono uppercase tracking-wider text-[11px] text-gray-400';
        langSpan.textContent = lang;

        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'code-copy-btn';
        copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i><span>复制代码</span>';
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(codeEl.innerText);
                copyBtn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i><span>已复制</span>';
                if (typeof onCopyFeedback === 'function') onCopyFeedback('代码已复制');
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i><span>复制代码</span>';
                }, 1800);
            } catch {
                if (typeof onCopyFeedback === 'function') onCopyFeedback('复制失败', 'error');
            }
        });

        header.appendChild(langSpan);
        header.appendChild(copyBtn);

        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(header);
        wrapper.appendChild(pre);
    });
}
