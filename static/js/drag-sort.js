// Порядок перетаскиванием — мышью или пальцем: плитки галереи, строки списка.
// Общий файл каркаса: одинаков во всех проектах (скилл uploads, «Галерея»).
//
// Разметка: data-drag-sort на списке, data-drag-id на каждом элементе,
// data-drag-ghost внутри него — что едет за пальцем. Формы внутри элемента
// и места с data-drag-skip — свои действия, за них элемент не берут. Кнопка
// просмотра вокруг фото — не такое место: за фото как раз и тянут.
//
// data-drag-sort="<url>" — новый порядок сразу уходит на сервер (поле order —
// id всех элементов по порядку), ответ заменяет список целиком. Пустой
// data-drag-sort — порядок живёт только на странице (черновик формы: поля
// внутри элементов уходят с формой по порядку) и список получает событие
// drag-sort:changed.
//
// Pointer Events, а не HTML5 drag-and-drop: тот на телефоне не работает. На
// телефоне элемент берут долгим нажатием — короткое касание открывает его,
// а движение пальца листает страницу.
(() => {
    const MOUSE_THRESHOLD_PX = 6;
    const LONG_PRESS_MS = 350;
    const TOUCH_SLOP_PX = 8;
    // У края экрана страница едет сама: палец занят плиткой, листать нечем.
    const EDGE_ZONE_PX = 72;
    const EDGE_STEP_PX = 12;
    const SKIP = 'form, [data-drag-skip]';

    let press = null;
    let drag = null;
    let suppressClick = false;

    function itemsOf(list) {
        // Только свои элементы: во вложенном списке — свои data-drag-id.
        return Array.from(list.querySelectorAll('[data-drag-id]'))
            .filter((item) => item.closest('[data-drag-sort]') === list);
    }

    function orderOf(list) {
        return itemsOf(list).map((item) => item.dataset.dragId);
    }

    // Ответ, заменяющий список, встаёт в порядке экрана: сервер рисует
    // обложку первой, а плитки под рукой прыгать не должны. Новые элементы —
    // после известных, в порядке сервера.
    function keepOrder(list, html) {
        if (!html || !list?.matches?.('[data-drag-sort]')) return html;
        const template = document.createElement('template');
        template.innerHTML = html;
        const fresh = list.id
            ? template.content.getElementById(list.id)
            : template.content.querySelector('[data-drag-sort]');
        if (!fresh?.hasAttribute('data-drag-sort')) return html;
        const rank = new Map(orderOf(list).map((id, index) => [id, index]));
        const items = itemsOf(fresh);
        const position = (item) => rank.get(item.dataset.dragId) ?? rank.size;
        const sorted = [...items].sort((a, b) => position(a) - position(b));
        const slots = items.map((item) => {
            const slot = document.createComment('');
            item.replaceWith(slot);
            return slot;
        });
        slots.forEach((slot, index) => slot.replaceWith(sorted[index]));
        return template.innerHTML;
    }

    window.dragSort = { keepOrder };

    document.addEventListener('htmx:beforeSwap', (event) => {
        const { detail } = event;
        detail.serverResponse = keepOrder(detail.target, detail.serverResponse);
    });

    // Призрак — копия одного помеченного куска, а не всего элемента: в нём
    // Alpine-формы, и их копия в body ожила бы второй раз.
    function makeGhost(item, rect) {
        const ghost = document.createElement('div');
        ghost.className = 'drag-ghost';
        ghost.style.width = `${rect.width}px`;
        ghost.style.height = `${rect.height}px`;
        const content = item.querySelector('[data-drag-ghost]');
        if (content) ghost.appendChild(content.cloneNode(true));
        document.body.appendChild(ghost);
        return ghost;
    }

    function start() {
        clearTimeout(press.timer);
        const { item, list, lastX, lastY } = press;
        press = null;
        const rect = item.getBoundingClientRect();
        drag = {
            item,
            list,
            ghost: makeGhost(item, rect),
            offsetX: lastX - rect.left,
            offsetY: lastY - rect.top,
            before: orderOf(list).join(),
        };
        item.classList.add('is-dragging');
        document.documentElement.classList.add('is-drag-sorting');
        navigator.vibrate?.(10);
        follow(lastX, lastY);
    }

    // Элемент встаёт на место того, над которым палец: после него, если шёл
    // вперёд, и перед ним, если назад. Сдвинувшись, тот оказывается под
    // пальцем сам, и место не скачет туда-обратно.
    function follow(x, y) {
        const { item, list, ghost } = drag;
        ghost.style.transform = `translate(${x - drag.offsetX}px, ${y - drag.offsetY}px)`;
        const over = document.elementFromPoint(x, y)?.closest('[data-drag-id]');
        if (over && over !== item && over.closest('[data-drag-sort]') === list) {
            const items = itemsOf(list);
            if (items.indexOf(item) < items.indexOf(over)) over.after(item);
            else over.before(item);
        }
        if (y < EDGE_ZONE_PX) window.scrollBy(0, -EDGE_STEP_PX);
        else if (y > window.innerHeight - EDGE_ZONE_PX) window.scrollBy(0, EDGE_STEP_PX);
    }

    function finish() {
        const { item, list, ghost, before } = drag;
        drag = null;
        ghost.remove();
        item.classList.remove('is-dragging');
        document.documentElement.classList.remove('is-drag-sorting');
        // Отпускание мыши даёт ещё и click — он открыл бы просмотр.
        suppressClick = true;
        setTimeout(() => { suppressClick = false; }, 0);
        const order = orderOf(list);
        if (order.join() === before) return;
        const url = list.dataset.dragSort;
        if (url) htmx.ajax('POST', url, { target: list, swap: 'outerHTML', values: { order } });
        else list.dispatchEvent(new CustomEvent('drag-sort:changed', { bubbles: true, detail: { order } }));
    }

    document.addEventListener('pointerdown', (event) => {
        if (event.button !== 0 || drag) return;
        const item = event.target.closest('[data-drag-id]');
        // Форма вокруг всего списка (черновик в форме записи) не мешает.
        const skip = event.target.closest(SKIP);
        if (!item || (skip && item.contains(skip))) return;
        press = {
            item,
            list: item.closest('[data-drag-sort]'),
            pointerId: event.pointerId,
            touch: event.pointerType !== 'mouse',
            startX: event.clientX,
            startY: event.clientY,
            lastX: event.clientX,
            lastY: event.clientY,
        };
        if (!press.list) press = null;
        else if (press.touch) press.timer = setTimeout(start, LONG_PRESS_MS);
    });

    document.addEventListener('pointermove', (event) => {
        if (drag) {
            follow(event.clientX, event.clientY);
            return;
        }
        if (!press || event.pointerId !== press.pointerId) return;
        press.lastX = event.clientX;
        press.lastY = event.clientY;
        const distance = Math.hypot(event.clientX - press.startX, event.clientY - press.startY);
        if (press.touch && distance > TOUCH_SLOP_PX) {
            clearTimeout(press.timer);
            press = null;
        } else if (!press.touch && distance > MOUSE_THRESHOLD_PX) {
            start();
        }
    });

    function release() {
        if (press) {
            clearTimeout(press.timer);
            press = null;
        }
        if (drag) finish();
    }

    document.addEventListener('pointerup', release);
    document.addEventListener('pointercancel', release);

    // Пока плитку тянут пальцем, страница не должна листаться под ним.
    document.addEventListener('touchmove', (event) => {
        if (drag) event.preventDefault();
    }, { passive: false });

    // Долгое нажатие на картинку открывает меню «сохранить изображение».
    document.addEventListener('contextmenu', (event) => {
        if ((press || drag) && event.target.closest('[data-drag-id]')) event.preventDefault();
    });

    document.addEventListener('dragstart', (event) => {
        if (event.target.closest?.('[data-drag-id]')) event.preventDefault();
    });

    document.addEventListener('click', (event) => {
        if (suppressClick && event.target.closest('[data-drag-id]')) {
            event.preventDefault();
            event.stopPropagation();
        }
    }, true);
})();
