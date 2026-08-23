/*
 * Note: Initial code structure and UI boilerplate generated with AI assistance
 * (e.g., Gemini/ChatGPT) as a productivity tool, then fully refactored, customized,
 * and integrated into the RedPatch architecture.
 */

const currentScript = document.currentScript || document.getElementById('main-script');

const currentModule = currentScript.dataset.module
const currentSubmodule = currentScript.dataset.submodule
const currentMode = currentScript.dataset.mode
const proxyPrefix = `/proxy/${currentModule}/${currentSubmodule}`;
const targetProxyUrl = proxyPrefix;
const launchUrl = `/api/labs/${encodeURIComponent(currentModule)}/${encodeURIComponent(currentSubmodule)}/launch`;
const resetUrl = `/api/labs/${encodeURIComponent(currentModule)}/${encodeURIComponent(currentSubmodule)}/reset`;

const rawFilesData = JSON.parse(document.getElementById('files-data').textContent || '{}') || {};

const vulnerablesData = rawFilesData.vulnerables || {};
const solutionsData = rawFilesData.solutions || {};
const hintsData = rawFilesData.hints || {};

let monacoEditor = null;
let fileModels = {};
let activeFilename = null;

function getInitialActiveFilename() {
    const keys = Object.keys(vulnerablesData || {});
    return keys.length ? keys[0] : null;
}

function renderTabs() {
    const tabs = document.getElementById('file-tabs');
    if (!tabs) return;
    tabs.innerHTML = '';
    const filenames = Object.keys(fileModels);
    if (!filenames.length) {
        tabs.innerHTML = '<span class="text-slate-500 px-3 py-1">No source files available</span>';
        return;
    }

    filenames.forEach((filename) => {
        const btn = document.createElement('button');
        btn.className = 'tab-btn px-3 py-1.5 rounded-t border-t border-x border-transparent hover:text-white flex items-center gap-2 transition-all';
        if (filename === activeFilename) {
            btn.classList.add('bg-cardBg/80', 'text-patchRed', 'border-borderBg', 'font-semibold', 'active-tab');
        } else {
            btn.classList.add('text-slate-400', 'bg-slate-900/40');
        }
        btn.innerHTML = '<i class="fa-regular fa-file-code"></i><span>' + filename + '</span>';
        btn.onclick = (evt) => switchTab(filename, { currentTarget: btn });
        tabs.appendChild(btn);
    });
}

function getLanguageByExtension(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
        'html': 'html', 'htm': 'html', 'css': 'css', 'php': 'php',
        'c': 'c', 'cpp': 'cpp', 'cs': 'csharp', 'go': 'go',
        'sh': 'shell', 'bash': 'shell', 'sql': 'sql', 'json': 'json',
        'xml': 'xml', 'yaml': 'yaml', 'yml': 'yaml', 'md': 'markdown'
    };
    return map[ext] || null;
}

function autoDetectLanguage(code) {
    if (!code || !code.trim()) return 'plaintext';
    const sample = code.trim();

    if (sample.startsWith('<?php') || sample.includes('<?php')) return 'php';
    if (sample.startsWith('<!DOCTYPE html') || sample.startsWith('<html') || (sample.startsWith('<') && sample.endsWith('>'))) return 'html';
    if (sample.includes('import ') && sample.includes('def ') && sample.includes(':')) return 'python';
    if (sample.includes('function') || sample.includes('const ') || sample.includes('let ') || sample.includes('=>')) return 'javascript';
    if (sample.includes('SELECT ') || sample.includes('INSERT INTO') || sample.includes('UPDATE ')) return 'sql';
    if (sample.startsWith('{') || sample.startsWith('[')) {
        try { JSON.parse(sample); return 'json'; } catch(e) {}
    }
    if (sample.includes('package main') || sample.includes('func main()')) return 'go';
    if (sample.includes('#include <')) return 'c';
    if (sample.includes('using System;')) return 'csharp';

    return 'plaintext';
}

function resolveLanguage(filename, content) {
    return getLanguageByExtension(filename) || autoDetectLanguage(content);
}

if (currentMode !== 'pentester') {
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });

    require(['vs/editor/editor.main'], function () {
        Object.keys(vulnerablesData || {}).forEach(filename => {
            const content = vulnerablesData[filename] || '';
            const lang = resolveLanguage(filename, content);
            fileModels[filename] = {
                model: monaco.editor.createModel(content, lang),
                language: lang
            };
        });

        activeFilename = getInitialActiveFilename();

        const container = document.getElementById('monaco-editor-container');
        const initialFile = activeFilename && fileModels[activeFilename];

        if (container) {
            monacoEditor = monaco.editor.create(container, {
                model: initialFile ? initialFile.model : null,
                theme: 'vs-dark',
                automaticLayout: true,
                fontSize: 13,
                fontFamily: "'Fira Code', 'Courier New', Courier, monospace",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                roundedSelection: true,
                cursorBlinking: 'smooth',
                padding: { top: 12, bottom: 12 }
            });
        }

        renderTabs();
        if (activeFilename) updateUIHeader(activeFilename);
    });
}

window.__solutionsMap = Object.assign({}, solutionsData || {});
window.__hintsMap = Object.assign({}, hintsData || {});

(async () => {
    if (!Object.keys(rawFilesData || {}).length && currentMode !== 'pentester') {
        const files = await fetchWorkspaceFiles();
        if (files) await reloadEditorFiles(files);
    }
})();

async function fetchWorkspaceFiles() {
    try {
        const res = await fetch(`/api/${encodeURIComponent(currentModule)}/${encodeURIComponent(currentSubmodule)}/lab-data`);
        if (!res.ok) return null;
        const jsonRes = await res.json();
        return jsonRes.data || null;
    } catch (e) {
        return null;
    }
}

async function reloadEditorFiles(newFiles) {
    if (!newFiles) return;
    const vuln = newFiles.vulnerables || {};
    const sols = newFiles.solutions || {};

    if (currentMode !== 'pentester') {
        Object.keys(vuln).forEach(filename => {
            const content = vuln[filename] || '';
            if (fileModels[filename]) {
                const model = fileModels[filename].model;
                if (model.getValue() !== content) model.setValue(content);
            } else {
                const lang = resolveLanguage(filename, content);
                fileModels[filename] = { model: monaco.editor.createModel(content, lang), language: lang };
            }
        });
    }

    window.__solutionsMap = Object.assign({}, sols || {});
    window.__hintsMap = Object.assign({}, newFiles.hints || {});

    if (!activeFilename && currentMode !== 'pentester') activeFilename = Object.keys(fileModels)[0] || null;

    if (activeFilename && monacoEditor && fileModels[activeFilename] && monacoEditor.getModel() !== fileModels[activeFilename].model) {
        monacoEditor.setModel(fileModels[activeFilename].model);
    }

    if (currentMode !== 'pentester') {
        renderTabs();
        if (activeFilename) updateUIHeader(activeFilename);
    }
}

function showSolutionPopup() {
    const modal = document.getElementById('solution-modal');
    const contentEl = document.getElementById('solution-content');
    const titleEl = document.getElementById('solution-title');

    const sols = window.__solutionsMap || {};
    let sol = null;

    if (currentMode === "pentester") {
        sol = sols["pentester"] || sols["poc"] || sols["exploit"];
    } else {
        if (activeFilename) {
            sol = sols[activeFilename];
            if (!sol && activeFilename.includes('target')) {
                const mappedName = activeFilename.replace('target', 'solution');
                sol = sols[mappedName];
            }
        }
    }

    if (!sol && Object.keys(sols).length > 0) {
        sol = Object.values(sols)[0];
    }

    contentEl.innerText = sol || 'No solution or PoC available for this lab.';
    titleEl.innerText = currentMode === 'pentester' ? 'Exploit Solution / PoC' : `Solution: ${activeFilename || 'Lab'}`;
    modal.classList.remove('hidden');
}

function closeSolutionPopup() {
    document.getElementById('solution-modal').classList.add('hidden');
}

function showHintsPopup() {
    const modal = document.getElementById('solution-modal');
    const contentEl = document.getElementById('solution-content');
    const titleEl = document.getElementById('solution-title');

    const hints = window.__hintsMap || {};
    let list = null;

    if (currentMode === "pentester") {
        list = hints["pentester"] || hints["general"];
    } else if (activeFilename) {
        list = hints[activeFilename];
    }

    if (!list && Object.keys(hints).length > 0) {
        list = Object.values(hints)[0];
    }

    if (!list || !list.length) {
        contentEl.innerText = 'No hints available for this lab.';
    } else if (Array.isArray(list)) {
        contentEl.innerText = list.map((h, i) => `${i+1}. ${h}`).join('\n\n');
    } else {
        contentEl.innerText = list;
    }

    titleEl.innerText = currentMode === 'pentester' ? 'Pentest Hints' : `Hints: ${activeFilename || 'Lab'}`;
    modal.classList.remove('hidden');
}

function updateUIHeader(filename) {
    const displayEl = document.getElementById('active-filename-display');
    const langEl = document.getElementById('active-language-display');
    if (displayEl) displayEl.innerText = filename;
    if (langEl) {
        const lang = fileModels[filename] ? fileModels[filename].language : 'plaintext';
        langEl.innerText = lang.toUpperCase();
    }
}

function switchTab(filename, evt) {
    if (!monacoEditor || !fileModels[filename]) return;

    activeFilename = filename;
    monacoEditor.setModel(fileModels[filename].model);
    updateUIHeader(filename);

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-cardBg/80', 'text-patchRed', 'border-borderBg', 'font-semibold', 'active-tab');
        btn.classList.add('text-slate-400', 'bg-slate-900/40');
    });

    if (evt && evt.currentTarget) {
        evt.currentTarget.classList.add('bg-cardBg/80', 'text-patchRed', 'border-borderBg', 'font-semibold', 'active-tab');
        evt.currentTarget.classList.remove('text-slate-400', 'bg-slate-900/40');
    }
}

async function startContainer() {
    const startBtn = document.getElementById('start-btn');
    const spinner = document.getElementById('loading-spinner');
    const overlay = document.getElementById('canvas-overlay');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const loadingMessage = document.getElementById('loading-message');

    startBtn.classList.add('hidden');
    spinner.classList.remove('hidden');
    spinner.classList.add('flex');

    try {
        loadingMessage.innerText = 'Downloading...';
        const launchRequest = fetch(launchUrl, { method: 'POST' });
        setTimeout(() => { loadingMessage.innerText = 'Preparing... Loading the Docker image.'; }, 700);
        const launchResponse = await launchRequest;
        const launchData = await launchResponse.json();
        if (!launchResponse.ok) throw new Error(launchData.detail || 'Lab could not be prepared.');
        loadingMessage.innerText = 'Preparing... Starting the container.';
    } catch (error) {
        spinner.classList.remove('flex');
        spinner.classList.add('hidden');
        startBtn.classList.remove('hidden');
        alert(error.message || 'The lab could not be started.');
        return;
    }

    let attempts = 0;
    const maxAttempts = 15;

    const pollServer = async () => {
        try {
            const res = await fetch(targetProxyUrl, { method: 'GET' });
            const containerStatus = res.headers.get('X-Container-Status');
            if (res.ok && containerStatus !== 'starting') {
                setIframeSrc('/');
                overlay.classList.add('hidden');
                statusIndicator.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse";
                statusText.innerText = "CONTAINER ACTIVE";

                await refreshDatas()

                if (currentMode !== 'pentester') {
                    const files = await fetchWorkspaceFiles();
                    if (files) await reloadEditorFiles(files);
                }
                return;
            }
        } catch (e) {}

        attempts++;
        if (attempts < maxAttempts) {
            setTimeout(pollServer, 1500);
        } else {
            spinner.classList.remove('flex');
            spinner.classList.add('hidden');
            startBtn.classList.remove('hidden');
            alert("Container failed to respond. Please click Start again.");
        }
    };

    pollServer();
}

function handleUrlBarKey(event) {
    if (event.key === 'Enter' || event.keyCode === 13) {
        event.preventDefault();
        navigateIframeFromInput();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const urlInput = document.getElementById('browser-url-bar');
    if (urlInput) {
        urlInput.addEventListener('keydown', handleUrlBarKey);
    }

    const iframe = document.getElementById('target-canvas');
    if (iframe) {
        iframe.addEventListener('load', () => {
            try {
                const currentHref = iframe.contentWindow.location.href;
                if (currentHref && currentHref !== 'about:blank') {
                    const internalPath = proxyToInternalUrl(currentHref);
                    updateUrlBarDisplay(internalPath);
                }
            } catch (e) {
                if (iframe.src) {
                    const internalPath = proxyToInternalUrl(iframe.src);
                    updateUrlBarDisplay(internalPath);
                }
            }
        });
    }
});

function internalToProxyUrl(userPath) {
    if (!userPath || userPath === 'about:blank') return 'about:blank';

    let rawPath = String(userPath).trim().replace(/\\/g, '/');

    try {
        const dummyBase = "http://localhost";
        const parsed = new URL(rawPath, dummyBase);

        let normalizedPath = parsed.pathname;

        const segments = normalizedPath.split('/').filter(Boolean);
        const safeSegments = [];

        for (const segment of segments) {
            if (segment === '..') {
                if (safeSegments.length > 0) safeSegments.pop();
            } else if (segment !== '.') {
                safeSegments.push(segment);
            }
        }

        let cleanPath = '/' + safeSegments.join('/');
        if (normalizedPath.endsWith('/') && cleanPath !== '/') {
            cleanPath += '/';
        }

        return proxyPrefix + cleanPath + parsed.search + parsed.hash;
    } catch (e) {
        return proxyPrefix + '/';
    }
}

function proxyToInternalUrl(fullUrl) {
    if (!fullUrl || fullUrl === 'about:blank') return '/';
    try {
        const parsed = new URL(fullUrl, window.location.origin);
        let pathname = parsed.pathname;

        if (pathname.startsWith(proxyPrefix)) {
            pathname = pathname.substring(proxyPrefix.length);
        }

        const segments = pathname.split('/').filter(Boolean);
        const safeSegments = [];
        for (const segment of segments) {
            if (segment === '..') {
                if (safeSegments.length > 0) safeSegments.pop();
            } else if (segment !== '.') {
                safeSegments.push(segment);
            }
        }

        let cleanPath = '/' + safeSegments.join('/');
        if (pathname.endsWith('/') && cleanPath !== '/') {
            cleanPath += '/';
        }

        return cleanPath + parsed.search + parsed.hash;
    } catch (e) {
        return '/';
    }
}

function setIframeSrc(userPath) {
    const iframe = document.getElementById('target-canvas');
    if (!iframe) return;

    if (userPath === 'about:blank') {
        iframe.src = 'about:blank';
        updateUrlBarDisplay('about:blank');
        return;
    }

    const proxyUrl = internalToProxyUrl(userPath);
    iframe.src = proxyUrl;

    const internalDisplay = proxyToInternalUrl(proxyUrl);
    updateUrlBarDisplay(internalDisplay);
}

function updateUrlBarDisplay(displayPath) {
    const input = document.getElementById('browser-url-bar');
    const externalLink = document.getElementById('external-link');
    if (!input) return;

    if (displayPath === 'about:blank') {
        input.value = 'about:blank';
        if (externalLink) externalLink.href = proxyPrefix;
        return;
    }

    let formatted = displayPath;
    if (!formatted.startsWith('/')) formatted = '/' + formatted;

    input.value = formatted;
    if (externalLink) externalLink.href = internalToProxyUrl(formatted);
}

function navigateIframeFromInput() {
    const input = document.getElementById('browser-url-bar');
    if (!input) return;

    let targetPath = input.value.trim();
    if (!targetPath) targetPath = '/';

    setIframeSrc(targetPath);
}

function goBackIframe() {
    try {
        const iframe = document.getElementById('target-canvas');
        iframe.contentWindow.history.back();
    } catch (e) {}
}

function goForwardIframe() {
    try {
        const iframe = document.getElementById('target-canvas');
        iframe.contentWindow.history.forward();
    } catch (e) {}
}

function reloadIframe() {
    const iframe = document.getElementById('target-canvas');
    if (iframe && iframe.src && iframe.src !== "about:blank") {
        iframe.src = iframe.src;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const iframe = document.getElementById('target-canvas');
    if (iframe) {
        iframe.addEventListener('load', () => {
            try {
                const currentHref = iframe.contentWindow.location.href;
                if (currentHref && currentHref !== 'about:blank') {
                    const internalPath = proxyToInternalUrl(currentHref);
                    updateUrlBarDisplay(internalPath);
                }
            } catch (e) {
                if (iframe.src) {
                    const internalPath = proxyToInternalUrl(iframe.src);
                    updateUrlBarDisplay(internalPath);
                }
            }
        });
    }
});

let aiDecorations = [];

async function runAI() {
    if (!activeFilename || !monacoEditor) {
        alert("File not selected or editor not initialized.");
        return;
    }

    const currentCode = monacoEditor.getValue();
    const btn = document.querySelector("button[onclick='runAI()']");
    const originalBtnText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Analyzing...</span>`;

    try {
        const response = await fetch('/api/workspace/ai-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                module: currentModule,
                submodule: currentSubmodule,
                code: currentCode
            })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Analysis error: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success' && data.vulnerability_analysis) {
            displayAIAnalysisResult(data.vulnerability_analysis);
        } else {
            alert("AI analysis could not be performed.");
        }
    } catch (error) {
        console.error("AI Analysis error:", error);
        alert("AI analysis failed: " + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalBtnText;
    }
}

function displayAIAnalysisResult(analysis) {
    const modal = document.getElementById('ai-modal');
    const content = document.getElementById('ai-modal-content');
    if (!modal || !content) return;

    if (analysis.target_line && analysis.target_line > 0 && analysis.vulnerability_found) {
        const startLine = Math.max(1, analysis.target_line - 1);
        const endLine = analysis.target_line + 1;
        aiDecorations = monacoEditor.deltaDecorations(aiDecorations, [
            {
                range: new monaco.Range(startLine, 1, endLine, 1),
                options: {
                    isWholeLine: true,
                    className: 'bg-red-900/30 border-l-4 border-red-500',
                    glyphMarginClassName: 'fa-solid fa-bug text-red-500'
                }
            }
        ]);
        monacoEditor.revealLineInCenter(analysis.target_line);
    }

    const statusBadge = analysis.vulnerability_found
        ? `<span class="bg-red-900/60 text-red-400 border border-red-700 px-2.5 py-1 rounded text-xs font-semibold">Vulnerability Found</span>`
        : `<span class="bg-emerald-900/60 text-emerald-400 border border-emerald-700 px-2.5 py-1 rounded text-xs font-semibold">Secure / No Vulnerability Found</span>`;

    content.innerHTML = `
        <div class="space-y-4">
            <div class="flex items-center justify-between border-b border-slate-700 pb-3">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-robot text-indigo-400 text-xl"></i>
                    <h3 class="font-bold text-slate-100">AI Security Analysis Report</h3>
                </div>
                ${statusBadge}
            </div>
            ${analysis.vulnerability_found ? `
                ${analysis.target_line ? `
                    <div class="text-xs text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-700 font-mono">
                        <strong class="text-red-400">Target Line:</strong> Line ${analysis.target_line}
                    </div>
                ` : ''}
            ` : ''}

            <div class="bg-slate-900/80 p-3 rounded border border-slate-700 text-sm">
                <h4 class="text-xs font-semibold uppercase text-slate-400 mb-1">Explanation & Tip</h4>
                <p class="text-slate-300 whitespace-pre-wrap">${escapeHtml(analysis.explanation || 'No explanation available.')}</p>
            </div>
            ${analysis.vulnerability_found ? `
            ${analysis.exploit_request ? `
                <div class="bg-slate-900/80 p-3 rounded border border-slate-700 text-sm font-mono">
                    <h4 class="text-xs font-semibold uppercase text-amber-400 mb-1">Example Request / Exploit Payload</h4>
                    <pre class="text-amber-200 text-xs overflow-x-auto p-2 bg-slate-950 rounded border border-slate-800">${escapeHtml(JSON.stringify(analysis.exploit_request, null, 2))}</pre>

                        <button id="fire-exploit-btn" class="mt-3 bg-red-600 hover:bg-red-500 text-white text-xs px-3 py-2 rounded font-medium transition-colors">
                            <i class="fa-solid fa-bolt mr-1"></i> Fire Payload in Canvas
                        </button>
                </div>
                ` : ''}
            ` : ''}
        </div>
    `;

    const fireButton = document.getElementById('fire-exploit-btn');
    if (fireButton) {
        fireButton.addEventListener('click', () => {
            try {
                executeExploitInIframe(analysis.exploit_request);
                closeAIModal();
            } catch (error) {
                console.error('Iframe exploit execution error:', error);
                alert(`Payload could not be sent to the canvas: ${error.message}`);
            }
        });
    }

    modal.classList.remove('hidden');
}

function closeAIModal() {
    const modal = document.getElementById('ai-modal');
    if (modal) modal.classList.add('hidden');
}

function executeExploitInIframe(exploitRequest) {
    if (!exploitRequest || !exploitRequest.path) {
        throw new Error('The AI response does not include an exploit request.');
    }

    const iframe = document.getElementById('target-canvas');
    iframe.name = 'target-canvas';
    const method = (exploitRequest.method || 'GET').toUpperCase();
    if (!['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        throw new Error(`Unsupported HTTP method: ${method}`);
    }

    const rawPath = String(exploitRequest.path);
    if (rawPath.includes('://')) {
        throw new Error('Exploit request paths must be relative to the current lab.');
    }

    const [pathOnly, pathQuery = ''] = rawPath.split('?', 2);
    const relativePath = pathOnly.replace(/^\/+/, '');
    const targetUrl = new URL(
        `${targetProxyUrl}/${relativePath}`.replace(/\/$/, relativePath ? '' : '/'),
        window.location.origin
    );

    function safeParseField(fieldValue) {
        if (!fieldValue || fieldValue === 'null') return {};
        if (typeof fieldValue === 'object') return fieldValue;
        if (typeof fieldValue === 'string') {
            try {
                const parsed = JSON.parse(fieldValue);
                return typeof parsed === 'object' && parsed !== null ? parsed : {};
            } catch (e) {
                return {};
            }
        }
        return {};
    }

    const reqHeaders = safeParseField(exploitRequest.headers);
    const reqParams = safeParseField(exploitRequest.params);
    const reqData = safeParseField(exploitRequest.data);
    const reqJsonBody = safeParseField(exploitRequest.json_body);

    const queryParams = new URLSearchParams(pathQuery);
    Object.entries(reqParams).forEach(([key, value]) => {
        queryParams.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
    });
    targetUrl.search = queryParams.toString();

    if (method === 'GET') {
        const internalPath = proxyToInternalUrl(targetUrl.toString());
        setIframeSrc(internalPath);
        return;
    }

    if (method !== 'POST') {
        targetUrl.searchParams.set('_redpatch_method', method);
    }

    if (Object.keys(reqHeaders).length) {
        targetUrl.searchParams.set('_redpatch_headers', encodeProxyMetadata(reqHeaders));
    }

    const usesJsonBody = Object.keys(reqData).length === 0 && Object.keys(reqJsonBody).length > 0;
    if (usesJsonBody) {
        targetUrl.searchParams.set('_redpatch_json_body', encodeProxyMetadata(reqJsonBody));
    }

    updateUrlBarDisplay(proxyToInternalUrl(targetUrl.toString()));

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = targetUrl.toString();
    form.target = iframe.name;
    form.enctype = 'application/x-www-form-urlencoded';
    form.style.display = 'none';

    const payloadData = Object.keys(reqData).length > 0 ? reqData : reqJsonBody;
    Object.entries(payloadData).forEach(([key, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = typeof value === 'object' ? JSON.stringify(value) : String(value);
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
    form.remove();
}

function encodeProxyMetadata(value) {
    return btoa(unescape(encodeURIComponent(JSON.stringify(value))));
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function applyPatch() {
    if (!activeFilename || !monacoEditor || !fileModels[activeFilename]) return;

    const codeContent = fileModels[activeFilename].model.getValue();
    const statusText = document.getElementById('patch-status');

    statusText.innerText = `Patching ${activeFilename}...`;
    statusText.className = "text-xs font-mono text-amber-400";

    try {
        const response = await fetch('/api/workspace/patch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                module: currentModule,
                submodule: currentSubmodule,
                filename: activeFilename,
                code: codeContent
            })
        });

        const result = await response.json();

        if (response.ok) {
            statusText.innerText = "Patch applied successfully!";
            statusText.className = "text-xs font-mono text-emerald-400";
            setTimeout(reloadIframe, 800);
        } else {
            statusText.innerText = "Error: " + (result.detail || "Failed to apply patch.");
            statusText.className = "text-xs font-mono text-rose-400";
        }
    } catch (err) {
        statusText.innerText = "Server connection failed.";
        statusText.className = "text-xs font-mono text-rose-400";
    }
}

async function resetLab() {
    if (!confirm("Are you sure you want to reset this lab session? Unsaved changes will be lost.")) return;

    try {
        const res = await fetch(resetUrl, { method: 'POST' });
        const contentType = res.headers.get("content-type");

        if (contentType && contentType.includes("application/json")) {
            const data = await res.json();

            if (res.ok && data.status === "success") {
                setIframeSrc('about:blank');
                document.getElementById('canvas-overlay').classList.remove('hidden');
                document.getElementById('start-btn').classList.remove('hidden');
                document.getElementById('loading-spinner').classList.add('hidden');
                document.getElementById('loading-spinner').classList.remove('flex');
                document.getElementById('status-indicator').className = "w-2.5 h-2.5 rounded-full bg-amber-500";
                document.getElementById('status-text').innerText = "CONTAINER INACTIVE";
            } else {
                alert("Failed to reset lab: " + (data.detail || data.message || "Unknown error"));
            }
        } else {
            const errorText = await res.text();
            showErrorPage(`Server Error (${res.status} ${res.statusText})`, errorText);
        }
    } catch (e) {
        alert("Network or script error while resetting lab: " + e.message);
    }
    window.location.reload();
}

async function submitFlag() {
    const input = document.getElementById('flag-input');
    if (!input) return;

    const flagValue = input.value.trim();
    if (!flagValue) {
        showFlagModal(false, "Please enter a flag value.");
        return;
    }

    try {
        const endpoint = `/api/check_flag/${encodeURIComponent(currentModule)}/${encodeURIComponent(currentSubmodule)}/${encodeURIComponent(flagValue)}`;
        const response = await fetch(endpoint);

        if (!response.ok) {
            showFlagModal(false, "Flag verification request failed.");
            return;
        }

        const data = await response.json();

        if (data.is_correct) {
            showFlagModal(true, "Congratulations! Correct flag, you successfully exploited the vulnerability.");
            input.classList.remove("border-red-500");
            input.classList.add("border-emerald-500", "text-emerald-400");
        } else {
            showFlagModal(false, "Incorrect flag! Check the hints and try again.");
        }
    } catch (error) {
        showFlagModal(false, "An error occurred while communicating with the server.");
    }
}

function showFlagModal(isCorrect, message) {
    const modal = document.getElementById('flag-modal');
    const icon = document.getElementById('flag-modal-icon');
    const title = document.getElementById('flag-modal-title');
    const msg = document.getElementById('flag-modal-message');

    if (!modal) {
        console.error("Target #flag-modal element not found in DOM.");
        return;
    }

    if (isCorrect) {
        setLabStatusSolved()
        icon.className = "w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-xl bg-emerald-900/50 text-emerald-400 border border-emerald-500/50";
        icon.innerHTML = '<i class="fa-solid fa-trophy"></i>';
        title.innerText = "Congratulations!";
        title.className = "text-base font-bold mb-1 text-emerald-400";
    } else {
        icon.className = "w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 text-xl bg-rose-900/50 text-rose-400 border border-rose-500/50";
        icon.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        title.innerText = "Incorrect Flag";
        title.className = "text-base font-bold mb-1 text-rose-400";
    }

    msg.innerText = message;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeFlagModal() {
    const modal = document.getElementById('flag-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function setLabStatusSolved() {
    const badge = document.getElementById('lab-status-badge');
    const dot = document.getElementById('lab-status-dot');
    const text = document.getElementById('lab-status-text');

    if (!badge || !dot || !text) return;

    text.textContent = 'SOLVED';

    badge.className = 'inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-mono font-semibold text-emerald-400 border border-emerald-500/20';
    dot.className = 'h-1.5 w-1.5 rounded-full bg-emerald-400';
}

async function refreshDatas() {
    try {
        const filesData = await fetchWorkspaceFiles();
        if (filesData) {
            await reloadEditorFiles(filesData);
            return true;
        }
        return false;
    } catch (e) {
        console.error("Error refreshing lab data:", e);
        return false;
    }
}

function showErrorPage(title, htmlContent) {
    const errorWindow = window.open("", "_blank");
    if (errorWindow) {
        errorWindow.document.write(htmlContent);
        errorWindow.document.close();
    } else {
        document.body.innerHTML = `
            <div style="padding: 20px; background: #0f172a; color: #ef4444; font-family: monospace;">
                <h2>${title}</h2>
                <hr style="border-color: #334155; margin: 10px 0;"/>
                <div>${htmlContent}</div>
            </div>
        `;
    }
}
