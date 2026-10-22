// Всплывающие сообщения в правом нижнем углу.
//
// Один контейнер на страницу, сообщения приходят тремя путями:
//   1. window.toast('текст') — из своего кода;
//   2. событие HX-Trigger от сервера — ответ HTMX кладёт его в заголовок,
//      так итог действия доезжает без перезагрузки страницы;
//   3. data-toast на элементе в разметке — для обычных ответов с редиректом,
//      где заголовку взяться неоткуда.
(() => {
    const AUTOHIDE_MS = 6000;
    let container = null;

    function mount() {
        if (container) return container;
        container = document.createElement('div');
        container.className = 'toast-stack';
        // Ошибки читаются вслух сразу, обычные сообщения — когда освободится.
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
        return container;
    }

    function show(message, kind = 'error') {
        if (!message) return;

        const toast = document.createElement('div');
        toast.className = `toast toast--${kind}`;
        toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');

        const mark = document.createElement('span');
        mark.className = 'toast__mark';
        mark.setAttribute('aria-hidden', 'true');

        const text = document.createElement('span');
        text.className = 'toast__text';
        text.textContent = message;

        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'toast__close';
        close.setAttribute('aria-label', 'Закрыть сообщение');
        close.textContent = '×';

        toast.append(mark, text, close);
        mount().appendChild(toast);

        // Таймер живёт на самом тосте: наведение мыши его останавливает,
        // иначе длинное сообщение исчезло бы недочитанным.
        let timer = setTimeout(() => dismiss(toast), AUTOHIDE_MS);
        toast.addEventListener('mouseenter', () => clearTimeout(timer));
        toast.addEventListener('mouseleave', () => {
            timer = setTimeout(() => dismiss(toast), AUTOHIDE_MS);
        });
        close.addEventListener('click', () => {
            clearTimeout(timer);
            dismiss(toast);
        });
    }

    function dismiss(toast) {
        toast.classList.add('is-leaving');
        // Ждём анимацию ухода, но не полагаемся на неё: если анимации нет
        // (prefers-reduced-motion), transitionend не придёт вовсе.
        setTimeout(() => toast.remove(), 200);
    }

    window.toast = show;

    // Сервер просит показать сообщение: HX-Trigger с полезной нагрузкой.
    document.body.addEventListener('app:toast', (event) => {
        const data = event.detail || {};
        show(data.message || data.value, data.kind || 'error');
    });

    // Разметка страницы принесла сообщение с собой.
    function drainMarkup(root) {
        root.querySelectorAll('[data-toast]').forEach((node) => {
            show(node.dataset.toast, node.dataset.toastKind || 'error');
            node.remove();
        });
    }

    document.addEventListener('DOMContentLoaded', () => drainMarkup(document));
    document.body.addEventListener('htmx:afterSwap', (event) => drainMarkup(event.detail.target));
})();
