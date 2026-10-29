// Маска мобильного для input[data-phone]: всегда «+7 9XX XXX-XX-XX».
// «8» и «+7» в начале становятся «+7 », первой цифрой после кода может быть
// только 9. Слушатели на document — поля из HTMX-ответов работают без
// повторной привязки.
(() => {
    const PREFIX = '+7 ';

    // Цифры номера без кода страны: «8 930…», «+7 930…», «930…» → «930…».
    // Мобильный начинается с 9, так что все 7 и 8 перед ним — код, в том
    // числе «+7 » маски плюс вставленный поверх «8 930…».
    function nationalDigits(value) {
        const digits = value.replace(/\D/g, '').replace(/^[78]+/, '');
        return digits.startsWith('9') ? digits.slice(0, 10) : '';
    }

    function format(national) {
        const parts = [national.slice(0, 3), national.slice(3, 6), national.slice(6, 8), national.slice(8, 10)];
        let text = PREFIX + parts[0];
        if (parts[1]) text += ` ${parts[1]}`;
        if (parts[2]) text += `-${parts[2]}`;
        if (parts[3]) text += `-${parts[3]}`;
        return text;
    }

    // Каретка встаёт после того же числа цифр, что было до неё: правка
    // в середине номера не отбрасывает курсор в конец.
    function caretAfterDigits(text, count) {
        let seen = 0;
        for (let i = PREFIX.length; i < text.length; i++) {
            if (/\d/.test(text[i]) && ++seen === count) return i + 1;
        }
        return text.length;
    }

    function apply(input, isDeleting = false) {
        const caret = input.selectionStart ?? input.value.length;
        const before = nationalDigits(input.value.slice(0, caret)).length;
        const national = nationalDigits(input.value);
        if (!national && isDeleting) {
            input.value = '';
            return;
        }
        input.value = format(national);
        if (document.activeElement === input) {
            const position = Math.max(caretAfterDigits(input.value, before), PREFIX.length);
            input.setSelectionRange(position, position);
        }
    }

    document.addEventListener('input', (event) => {
        if (!event.target.matches('input[data-phone]')) return;
        apply(event.target, event.inputType?.startsWith('delete'));
    });
    document.addEventListener('focusin', (event) => {
        if (event.target.matches('input[data-phone]') && !event.target.value) {
            event.target.value = PREFIX;
        }
    });
    document.addEventListener('focusout', (event) => {
        if (event.target.matches('input[data-phone]') && event.target.value.trim() === '+7') {
            event.target.value = '';
        }
    });
    // Значение от сервера («+79301112233» или введённое с ошибкой) — сразу в маске.
    htmx.onLoad((root) => {
        root.querySelectorAll('input[data-phone]').forEach((input) => {
            const national = nationalDigits(input.value);
            if (national) input.value = format(national);
        });
    });
})();
