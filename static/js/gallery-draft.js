// Черновик галереи — фото записи, которой ещё нет в базе. Файлы уже во
// временной папке (gallery-upload.js), а порядок, обложка и удаление живут
// только в форме, пока её не сохранят: поля внутри плиток уходят по порядку
// плиток, обложка — полем [data-draft-cover]. Без выбора обложка — первое
// фото. Галерея без поля обложки — просто набор фото. Общий файл каркаса.
(() => {
    function tilesOf(draft) {
        return Array.from(draft.querySelectorAll('[data-draft-key]'));
    }

    function sync(draft) {
        const input = draft.querySelector('[data-draft-cover]');
        if (!input) return;
        const tiles = tilesOf(draft);
        const keys = tiles.map((tile) => tile.dataset.draftKey);
        if (!keys.includes(input.value)) input.value = keys[0] ?? '';
        tiles.forEach((tile) => tile.classList.toggle('is-cover', tile.dataset.draftKey === input.value));
    }

    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-draft-make-cover], [data-draft-remove]');
        const draft = button?.closest('[data-gallery-draft]');
        if (!draft) return;
        const tile = button.closest('[data-draft-key]');
        if (button.hasAttribute('data-draft-remove')) tile.remove();
        else draft.querySelector('[data-draft-cover]').value = tile.dataset.draftKey;
        sync(draft);
    });

    document.addEventListener('gallery-upload:placed', (event) => {
        const draft = event.target.closest('[data-gallery-draft]');
        if (draft) sync(draft);
    });

    htmx.onLoad((element) => {
        const drafts = element.matches?.('[data-gallery-draft]') ? [element] : [];
        drafts.push(...(element.querySelectorAll?.('[data-gallery-draft]') ?? []));
        drafts.forEach(sync);
    });
})();
