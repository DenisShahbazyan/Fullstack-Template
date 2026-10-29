// Свои окошки выбора даты вместо системного <input type="date"> (скилл
// frontend, «Выбор дат»). Значение — в скрытых полях формы в виде YYYY-MM-DD.
// datePicker — один день: после выбора скрытое поле шлёт change, его ловит
// hx-trigger="change" формы. rangePicker — диапазон: первый клик — начало,
// второй — конец, затем форма вокруг уходит сама. data-min / data-max —
// раньше и позже выбрать нельзя. Разметка — макросы date_field и date_range
// (templates/public/macros/date_picker.html).
document.addEventListener('alpine:init', () => {
    const MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль',
        'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
    const WEEKDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
    const GAP = 6;
    const EDGE = 8;

    const pad = (n) => String(n).padStart(2, '0');
    const parse = (value) => {
        if (!value) return null;
        const [y, m, d] = value.split('-').map(Number);
        return new Date(y, m - 1, d);
    };
    const serialize = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
    const monthOf = (d) => new Date(d.getFullYear(), d.getMonth(), 1);
    const isWeekend = (d) => d.getDay() === 0 || d.getDay() === 6;
    const mondayOf = (d) => addDays(d, -((d.getDay() + 6) % 7));
    const today = () => new Date(new Date().setHours(0, 0, 0, 0));
    const monthTitle = (view) => `${MONTHS[view.getMonth()]} ${view.getFullYear()}`;

    function dateLabel(d) {
        const year = d.getFullYear() === new Date().getFullYear() ? '' : ` ${d.getFullYear()}`;
        return `${WEEKDAYS[d.getDay()]}, ${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}${year}`;
    }

    const dayLabel = (d) => `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`;

    // Клетки месяца. Пустые до первого числа — тоже кнопки (невидимые): у x-for
    // один корневой элемент, а сдвиг сетки нужен без инлайн-стилей.
    // from..to — подсвеченный отрезок, min и max — границы выбора.
    function monthCells(view, { from, to, min, max }) {
        const lead = (view.getDay() + 6) % 7;
        const count = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
        const now = today().getTime();
        const [start, end] = [from, to].map((d) => d.getTime());
        const cells = Array.from({ length: lead }, (_, i) => ({ key: `blank-${i}`, blank: true }));
        for (let n = 1; n <= count; n++) {
            const date = new Date(view.getFullYear(), view.getMonth(), n);
            const time = date.getTime();
            cells.push({
                key: time,
                date,
                label: n,
                disabled: (min && time < min.getTime()) || (max && time > max.getTime()),
                classes: {
                    'is-today': time === now,
                    'is-weekend': isWeekend(date),
                    'is-on': time === start || time === end,
                    'is-span': time > start && time < end,
                },
            });
        }
        return cells;
    }

    // Окошко стоит fixed от кнопки: внутри прокручиваемого окна его обрезало
    // бы. Не влезает вниз — встаёт над кнопкой. Координаты — CSS-переменными.
    function placePopover(pop, field) {
        const rect = field.getBoundingClientRect();
        const width = pop.offsetWidth;
        const height = pop.offsetHeight;
        let top = rect.bottom + GAP;
        if (top + height > window.innerHeight - EDGE) top = Math.max(EDGE, rect.top - height - GAP);
        pop.style.setProperty('--pop-left', `${Math.min(Math.max(EDGE, rect.left), window.innerWidth - width - EDGE)}px`);
        pop.style.setProperty('--pop-top', `${top}px`);
    }

    // Общее у обоих окошек: открыть у кнопки, листать месяцы, границы. Только
    // поля и методы: геттер spread вычислил бы сразу, пока view ещё нет.
    const popover = () => ({
        open: false,
        view: null,
        min: null,
        max: null,

        readBounds() {
            this.min = parse(this.$root.dataset.min);
            this.max = parse(this.$root.dataset.max);
        },

        show(month) {
            this.open = true;
            this.view = monthOf(month);
            this.$nextTick(() => {
                placePopover(this.$refs.pop, this.$refs.field);
                this.$refs.pop.focus({ preventScroll: true });
            });
        },

        shiftMonth(step) { this.view = new Date(this.view.getFullYear(), this.view.getMonth() + step, 1); },

        hoverDay() {},
    });

    Alpine.data('datePicker', () => ({
        ...popover(),
        value: null,

        init() {
            this.readBounds();
            this.value = parse(this.$refs.input.value) ?? today();
        },

        get monthTitle() { return monthTitle(this.view); },
        get label() { return dateLabel(this.value); },
        get cells() { return monthCells(this.view, { from: this.value, to: this.value, min: this.min, max: this.max }); },

        toggle() { return this.open ? this.close() : this.show(this.value); },
        close() { this.open = false; },

        pickDay(day) {
            this.value = day;
            this.close();
            this.$refs.input.value = serialize(day);
            this.$refs.input.dispatchEvent(new Event('change', { bubbles: true }));
        },
    }));

    Alpine.data('rangePicker', () => ({
        ...popover(),
        start: null,
        end: null,
        // Начало выбрано, ждём конец; hover — день под курсором для подсветки.
        picking: false,
        hover: null,

        init() {
            this.readBounds();
            this.start = parse(this.$refs.start.value) ?? today();
            this.end = parse(this.$refs.end.value) ?? this.start;
        },

        get monthTitle() { return monthTitle(this.view); },

        get cells() {
            const bounds = { min: this.min, max: this.max };
            if (!this.picking) return monthCells(this.view, { from: this.start, to: this.end, ...bounds });
            const other = this.hover ?? this.start;
            const [from, to] = other < this.start ? [other, this.start] : [this.start, other];
            return monthCells(this.view, { from, to, ...bounds });
        },

        get note() {
            if (this.picking) return 'Выберите последний день';
            return this.start.getTime() === this.end.getTime()
                ? dayLabel(this.start)
                : `${dayLabel(this.start)} – ${dayLabel(this.end)}`;
        },

        // Быстрые недели — от последнего доступного дня (data-max) или от сегодня.
        get quickRanges() {
            const last = this.max ?? today();
            const monday = mondayOf(last);
            return [
                { label: 'Эта неделя', from: monday, to: last },
                { label: 'Прошлая неделя', from: addDays(monday, -7), to: addDays(monday, -1) },
            ];
        },

        toggle() { return this.open ? this.close() : this.show(this.end); },

        // Закрыли посреди выбора — остаётся прежний диапазон.
        close() {
            this.open = false;
            if (this.picking) this.init();
            this.picking = false;
            this.hover = null;
        },

        hoverDay(day) { this.hover = day; },

        pickDay(day) {
            if (!this.picking) {
                this.start = day;
                this.end = day;
                this.picking = true;
                return;
            }
            const [from, to] = day < this.start ? [day, this.start] : [this.start, day];
            this.pickRange(from, to);
        },

        pickRange(from, to) {
            this.start = from;
            this.end = to;
            this.picking = false;
            this.$refs.start.value = serialize(from);
            this.$refs.end.value = serialize(to);
            this.$root.closest('form').requestSubmit();
        },
    }));
});
