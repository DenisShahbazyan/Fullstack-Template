// Загрузка файлов в галерею: у каждого файла своя плитка в сетке галереи —
// превью из самого файла, полоса и проценты, крестик отмены. Общий файл
// каркаса: одинаков во всех проектах (скилл uploads, «Галерея»).
//
// Разметка (макросы templates/public/macros/gallery_upload.html):
//   data-gallery-upload на обёртке, внутри неё — input[type=file], сетка
//   и в ней [data-upload-queue], куда встают плитки загрузки;
//   data-upload-url — куда слать файл: POST, поле file, по файлу на запрос;
//   data-upload-target, data-upload-swap — куда и как вставить ответ
//   (outerHTML — перерисованная галерея, beforeend — плитка черновика);
//   data-accept — MIME через запятую, data-max-size — байты.
//
// Файл идёт XHR, а не hx-post: htmx не даёт прогресс по каждому файлу. Ответ
// — HTML, как у любого HTMX-роута, и вставляет его htmx.swap: с oob-блоками и
// обработкой атрибутов. Ошибка приходит, как и всем HTMX-запросам, — 200 с
// пустым телом и тостом в HX-Trigger; её текст встаёт на плитку.
//
// Свой загрузчик для типа, которого сервер формой не примет (видео частями в
// S3), регистрирует проект: galleryUpload.register({ accepts, problem,
// upload }). upload({ root, file, type, tile, signal }) завершается, когда
// файл уже в галерее.
(() => {
    // Фото с телефона весит 5–20 МБ, а сервер всё равно ужмёт его до
    // S3__IMAGE_MAX_SIDE: ужимаем до отправки, чтобы не гнать лишние мегабайты
    // по медленной связи. Canvas заодно не переносит EXIF с геометкой. Фото
    // меньше порога и так быстро дойдёт — второй раз его не пережимаем.
    const PHOTO_MAX_SIDE = 2560;
    const PHOTO_QUALITY = 0.85;
    const PHOTO_KEEP_BYTES = 2 * 1024 ** 2;
    // GIF не трогаем: canvas оставил бы от анимации первый кадр.
    const SHRINKABLE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
    // HEIC с iPhone сервер не принимает, а Safari его читает: такое фото
    // перекодируется здесь в любом случае. Браузер, который HEIC не читает,
    // покажет на плитке, что формат не подходит.
    const HEIC_TYPES = ['image/heic', 'image/heif'];
    // Браузер не всегда знает тип файла — тогда берём его по расширению.
    const EXTENSION_TYPES = {
        jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp',
        gif: 'image/gif', pdf: 'application/pdf', heic: 'image/heic', heif: 'image/heif',
        mp4: 'video/mp4', webm: 'video/webm', mov: 'video/quicktime',
    };
    const FAILED = 'Не удалось загрузить файл';

    const uploaders = [];
    // Файлы идут по одному: так плитки встают в галерею в порядке выбора.
    let queue = Promise.resolve();
    let pending = 0;

    window.addEventListener('beforeunload', (event) => {
        if (pending > 0) event.preventDefault();
    });

    function config(root) {
        const d = root.dataset;
        return {
            root,
            url: d.uploadUrl,
            target: d.uploadTarget,
            swap: d.uploadSwap || 'outerHTML',
            types: (d.accept || '').split(',').filter(Boolean),
            maxSize: Number(d.maxSize) || Infinity,
            list: root.querySelector('[data-upload-queue]'),
        };
    }

    function contentType(file) {
        if (file.type) return file.type;
        const extension = file.name.split('.').pop().toLowerCase();
        return EXTENSION_TYPES[extension] || '';
    }

    function formatSize(bytes) {
        const gb = 1024 ** 3;
        return bytes >= gb ? `${bytes / gb} ГБ` : `${Math.round(bytes / 1024 ** 2)} МБ`;
    }

    function problemWith(c, file, type, uploader) {
        if (file.size === 0) return 'Файл пустой';
        if (uploader) return uploader.problem?.(file, type, c.root) ?? null;
        const isConvertible = HEIC_TYPES.includes(type) && c.types.includes('image/jpeg');
        if (!c.types.includes(type) && !isConvertible) return 'Такой формат не подходит';
        if (file.size > c.maxSize) return `Файл больше ${formatSize(c.maxSize)}`;
        return null;
    }

    // Источник — декодированное фото (ImageBitmap) или видео на нужном кадре.
    function scaled(source, maxSide) {
        const width = source.videoWidth ?? source.width;
        const height = source.videoHeight ?? source.height;
        const scale = Math.min(1, maxSide / Math.max(width, height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(width * scale);
        canvas.height = Math.round(height * scale);
        canvas.getContext('2d').drawImage(source, 0, 0, canvas.width, canvas.height);
        return canvas;
    }

    // Safari не кодирует WebP и молча отдаёт PNG — тогда JPEG. Но не для
    // PNG: у JPEG нет прозрачности, фон стал бы чёрным.
    async function encode(canvas, sourceType, quality) {
        const targets = sourceType === 'image/png' ? ['image/webp', 'image/png'] : ['image/webp', 'image/jpeg'];
        for (const target of targets) {
            const blob = await new Promise((resolve) => canvas.toBlob(resolve, target, quality));
            if (blob && blob.type === target) return blob;
        }
        return null;
    }

    // Что не вышло ужать (браузер не прочитал формат), уходит как есть:
    // сервер разберёт файл по содержимому и сам скажет, если он не подходит.
    async function shrunk(file, type) {
        const isHeic = HEIC_TYPES.includes(type);
        if (!isHeic && !SHRINKABLE_TYPES.includes(type)) return file;
        let bitmap;
        try {
            bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
        } catch {
            if (isHeic) throw new Error('Такой формат не подходит — сохраните фото как JPEG');
            return file;
        }
        try {
            const isLarge = Math.max(bitmap.width, bitmap.height) > PHOTO_MAX_SIDE;
            if (!isHeic && !isLarge && file.size <= PHOTO_KEEP_BYTES) return file;
            const blob = await encode(scaled(bitmap, PHOTO_MAX_SIDE), type, PHOTO_QUALITY);
            if (isHeic) return blob ?? file;
            return blob && blob.size < file.size ? blob : file;
        } finally {
            bitmap.close();
        }
    }

    function csrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    function detailOf(text) {
        try {
            const data = JSON.parse(text);
            if (typeof data.detail === 'string') return data.detail;
        } catch {
            // Тело не JSON — например, страница ошибки или ответ прокси.
        }
        return null;
    }

    // Тост-ошибка в HX-Trigger: имя события у проектов своё, ищем по виду.
    function toastError(xhr) {
        const header = xhr.getResponseHeader('HX-Trigger');
        if (!header) return null;
        try {
            const events = Object.values(JSON.parse(header));
            const error = events.find((event) => event?.message && (event.kind ?? 'error') === 'error');
            return error ? error.message : null;
        } catch {
            return null;
        }
    }

    function statusMessage(status) {
        if (status === 413) return 'Файл слишком большой';
        if (status === 429) return 'Слишком много загрузок — подождите несколько минут';
        return FAILED;
    }

    // Форма на наш сервер через XHR, а не fetch: fetch не сообщает, сколько
    // байт уже ушло. Отдаёт тело ответа — HTML для галереи.
    function sendForm(url, form, onProgress, signal) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            xhr.setRequestHeader('HX-Request', 'true');
            xhr.setRequestHeader('X-CSRF-Token', csrfToken());
            if (onProgress) xhr.upload.onprogress = (event) => onProgress(event.loaded / event.total);
            xhr.onload = () => {
                const failed = xhr.status < 200 || xhr.status >= 300;
                const message = failed ? detailOf(xhr.responseText) || statusMessage(xhr.status) : toastError(xhr);
                if (message) reject(new Error(message));
                else resolve(xhr.responseText);
            };
            xhr.onerror = () => reject(new Error('Связь оборвалась — попробуйте ещё раз'));
            xhr.onabort = () => reject(new DOMException('Загрузка отменена', 'AbortError'));
            signal.addEventListener('abort', () => xhr.abort(), { once: true });
            xhr.send(form);
        });
    }

    // Превью из самого файла: видно не только что грузится, но и что именно.
    // У документа превью нет — на плитке его имя.
    function previewOf(file, type) {
        if (!type.startsWith('image/') && !type.startsWith('video/')) {
            const name = document.createElement('span');
            name.className = 'gallery-file-name';
            name.textContent = file.name;
            return { media: name, release: () => {} };
        }
        const url = URL.createObjectURL(file);
        let media;
        if (type.startsWith('image/')) {
            media = document.createElement('img');
            media.alt = '';
            media.src = url;
        } else {
            media = document.createElement('video');
            media.muted = true;
            media.playsInline = true;
            media.preload = 'metadata';
            media.src = `${url}#t=0.1`;
        }
        media.className = 'gallery-img';
        return { media, release: () => URL.revokeObjectURL(url) };
    }

    function addTile(c, file, type) {
        const tile = document.createElement('div');
        tile.className = 'gallery-cell upload-tile';
        const preview = previewOf(file, type);
        const overlay = document.createElement('div');
        overlay.className = 'upload-overlay';
        const status = document.createElement('span');
        status.className = 'upload-status';
        status.textContent = 'В очереди';
        const bar = document.createElement('progress');
        bar.className = 'upload-bar';
        bar.max = 1;
        bar.value = 0;
        overlay.append(status, bar);
        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'upload-cancel';
        cancel.setAttribute('aria-label', `Отменить загрузку ${file.name}`);
        cancel.title = file.name;
        cancel.textContent = '✕';
        tile.append(preview.media, overlay, cancel);
        c.list.appendChild(tile);
        // В ленте, которая листается вбок, новая плитка уходит за край.
        tile.scrollIntoView({ block: 'nearest', inline: 'nearest' });

        let finished = false;
        const remove = () => {
            preview.release();
            tile.remove();
        };
        return {
            // Пока файл идёт, крестик отменяет загрузку, после ошибки — убирает плитку.
            onCancel: (handler) => cancel.addEventListener('click', () => (finished ? remove() : handler())),
            status: (text) => { status.textContent = text; },
            progress: (fraction) => {
                bar.value = fraction;
                status.textContent = fraction < 1 ? `${Math.floor(fraction * 100)}%` : 'Сохраняем…';
            },
            done() {
                finished = true;
                remove();
            },
            fail(message) {
                finished = true;
                tile.classList.add('is-failed');
                cancel.setAttribute('aria-label', 'Убрать');
                status.textContent = message;
            },
        };
    }

    // Плитка загрузки уходит, когда файл уже встал в галерею, — иначе на миг
    // он пропадал бы со страницы совсем.
    function place(c, html) {
        const target = document.querySelector(c.target);
        // eventInfo — detail событий htmx:afterSwap: без него обработчики
        // страницы (Alpine.initTree, тосты) получат пустой detail.target.
        const eventInfo = { target, elt: target };
        // htmx.swap не шлёт htmx:beforeSwap: порядок экрана держим сами.
        const kept = window.dragSort ? dragSort.keepOrder(target, html) : html;
        if (kept && target) htmx.swap(target, kept, { swapStyle: c.swap }, { eventInfo });
        c.root.dispatchEvent(new CustomEvent('gallery-upload:placed', { bubbles: true }));
    }

    async function uploadForm(c, file, type, tile, signal) {
        const form = new FormData();
        form.append('file', await shrunk(file, type), file.name);
        place(c, await sendForm(c.url, form, (fraction) => tile.progress(fraction), signal));
    }

    async function upload(c, file, type, tile, controller) {
        const uploader = uploaders.find((candidate) => candidate.accepts(type, c.root));
        const problem = problemWith(c, file, type, uploader);
        if (problem) return tile.fail(problem);
        if (controller.signal.aborted) return tile.fail('Отменено');

        try {
            tile.status('Подготовка…');
            if (uploader) await uploader.upload({ root: c.root, file, type, tile, signal: controller.signal });
            else await uploadForm(c, file, type, tile, controller.signal);
            tile.done();
        } catch (error) {
            controller.abort();
            tile.fail(error.name === 'AbortError' ? 'Отменено' : error.message || FAILED);
        }
    }

    // data-uploading на обёртке, пока её файлы не дошли: форма черновика
    // по нему не уходит раньше времени (gallery-draft.js).
    function track(root, delta) {
        const count = Number(root.dataset.uploading || 0) + delta;
        if (count > 0) root.dataset.uploading = count;
        else delete root.dataset.uploading;
    }

    function enqueue(root, files) {
        const c = config(root);
        Array.from(files).forEach((file) => {
            const type = contentType(file);
            const tile = addTile(c, file, type);
            const controller = new AbortController();
            tile.onCancel(() => controller.abort());
            pending++;
            track(root, 1);
            queue = queue
                .then(() => upload(c, file, type, tile, controller))
                .finally(() => {
                    pending--;
                    track(root, -1);
                });
        });
    }

    window.galleryUpload = {
        register: (uploader) => uploaders.push(uploader),
        sendForm,
    };

    document.addEventListener('change', (event) => {
        const input = event.target;
        const root = input.closest?.('[data-gallery-upload]');
        if (!root || input.type !== 'file') return;
        enqueue(root, input.files);
        input.value = '';
    });

    function fileDragRoot(event) {
        if (!event.dataTransfer?.types.includes('Files')) return null;
        return event.target.closest?.('[data-gallery-upload]') ?? null;
    }

    document.addEventListener('dragover', (event) => {
        const root = fileDragRoot(event);
        if (!root) return;
        event.preventDefault();
        root.classList.add('is-dropping');
    });

    document.addEventListener('dragleave', (event) => {
        const root = fileDragRoot(event);
        if (root && !root.contains(event.relatedTarget)) root.classList.remove('is-dropping');
    });

    document.addEventListener('drop', (event) => {
        const root = fileDragRoot(event);
        if (!root) return;
        event.preventDefault();
        root.classList.remove('is-dropping');
        enqueue(root, event.dataTransfer.files);
    });
})();
