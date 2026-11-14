/* Shared Cockpit theme, keyboard navigation and accessible dialogs. */
(() => {
    'use strict';
    const preference = window.matchMedia('(prefers-color-scheme: dark)');
    let style;
    try { style = localStorage.getItem('shell:style') || 'auto'; } catch { style = 'auto'; }
    function applyTheme(value = style) {
        style = ['light', 'dark', 'auto'].includes(value) ? value : 'auto';
        document.documentElement.classList.toggle('pf-v6-theme-dark', style === 'dark' || (style === 'auto' && preference.matches));
    }
    applyTheme();
    preference.addEventListener('change', () => applyTheme());
    window.addEventListener('storage', event => {
        if (event.key === 'shell:style') applyTheme(event.newValue);
    });
    window.addEventListener('cockpit-style', event => applyTheme(event.detail?.style));

    const nav = document.getElementById('nav');
    if (nav) {
        nav.setAttribute('role', 'tablist');
        nav.setAttribute('aria-label', document.title + ' vaated');
        const tabs = [...nav.querySelectorAll('[data-view]')];
        const content = document.getElementById('content');
        content.setAttribute('role', 'tabpanel');
        function syncTabs() {
            tabs.forEach(tab => {
                const active = tab.classList.contains('active');
                tab.id = 'tab-' + tab.dataset.view;
                tab.setAttribute('role', 'tab');
                tab.setAttribute('aria-selected', String(active));
                tab.setAttribute('aria-controls', 'content');
                tab.tabIndex = active ? 0 : -1;
                if (active) content.setAttribute('aria-labelledby', tab.id);
            });
        }
        syncTabs();
        new MutationObserver(syncTabs).observe(nav, {subtree: true, attributes: true, attributeFilter: ['class']});
        nav.addEventListener('keydown', event => {
            const index = tabs.indexOf(event.target);
            if (index < 0 || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
            tabs[next].focus();
            tabs[next].click();
            tabs[next].scrollIntoView({block: 'nearest', inline: 'nearest'});
        });
    }
    document.querySelectorAll('dialog').forEach(dialog => {
        const heading = dialog.querySelector('h2');
        if (heading) {
            heading.id ||= dialog.id + '-heading';
            dialog.setAttribute('aria-labelledby', heading.id);
        }
        dialog.querySelectorAll('button').forEach(button => {
            if (button.textContent.trim() === '×') button.setAttribute('aria-label', 'Sulge dialoog');
        });
    });
    document.querySelectorAll('.switch input').forEach(input => {
        input.setAttribute('role', 'switch');
    });
    const notification = document.getElementById('toast') || document.getElementById('message');
    if (notification) {
        new MutationObserver(() => {
            if (!notification.classList.contains('error') || notification.querySelector('[data-dismiss]')) return;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'dismiss-notice';
            button.dataset.dismiss = '';
            button.setAttribute('aria-label', 'Sulge teade');
            button.textContent = '×';
            button.onclick = () => notification.classList.add('hidden');
            notification.append(button);
        }).observe(notification, {childList: true});
    }
})();
