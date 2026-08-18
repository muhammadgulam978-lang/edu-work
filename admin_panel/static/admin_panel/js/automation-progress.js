(() => {
    const root = document.querySelector('[data-automation-progress]');
    if (!root) return;

    const query = (selector) => root.querySelector(selector);
    const urlTemplate = root.dataset.progressUrlTemplate;
    let timer = null;
    let currentRunId = root.dataset.progressRun;

    const statusText = (value) => (value || 'Pending').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
    const durationText = (seconds) => {
        if (seconds === null || seconds === undefined) return 'Calculating ETA';
        if (seconds < 60) return `About ${seconds}s left`;
        const minutes = Math.ceil(seconds / 60);
        return `About ${minutes} min left`;
    };
    const setText = (selector, value) => { const element = query(selector); if (element) element.textContent = value; };
    const formatTime = (value) => value ? new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value)) : '';

    function renderEvents(events) {
        const feed = query('[data-progress-feed]');
        feed.replaceChildren();
        if (!events.length) {
            const empty = document.createElement('li');
            empty.className = 'automation-progress__empty';
            empty.textContent = 'Waiting for activity…';
            feed.append(empty);
            return;
        }
        events.forEach((event) => {
            const row = document.createElement('li');
            const primary = document.createElement('div');
            const name = document.createElement('div');
            name.className = 'automation-progress__feed-name';
            name.textContent = event.name;
            const meta = document.createElement('div');
            meta.className = 'automation-progress__feed-meta';
            meta.textContent = [event.identifier, event.channel, formatTime(event.occurred_at), event.message].filter(Boolean).join(' · ');
            primary.append(name, meta);
            const state = document.createElement('div');
            state.className = `automation-progress__feed-status ${event.status === 'FAILED' ? 'is-failed' : event.status === 'SKIPPED' ? 'is-skipped' : ''}`;
            state.textContent = statusText(event.status);
            row.append(primary, state);
            feed.append(row);
        });
    }

    function render(data) {
        root.hidden = false;
        setText('[data-progress-label]', data.label);
        setText('[data-progress-status]', statusText(data.status));
        setText('[data-progress-percent]', `${data.percentage}%`);
        setText('[data-progress-eta]', ['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'].includes(data.status) ? 'Job finished' : durationText(data.eta_seconds));
        query('[data-progress-bar]').style.width = `${Math.max(0, Math.min(100, data.percentage))}%`;
        setText('[data-progress-total]', data.total_items);
        setText('[data-progress-processed]', data.processed_items);
        setText('[data-progress-remaining]', data.remaining_items);
        setText('[data-progress-success]', data.successful_items);
        setText('[data-progress-failed]', data.failed_items);
        setText('[data-progress-skipped]', data.skipped_items);
        setText('[data-progress-current-name]', data.current.name || 'Waiting for the next record');
        setText('[data-progress-current-meta]', [data.current.identifier, data.current.channel].filter(Boolean).join(' · ') || '—');
        setText('[data-progress-current-status]', statusText(data.current.status));
        const error = query('[data-progress-error]');
        error.hidden = !data.error_message;
        error.textContent = data.error_message || '';
        renderEvents(data.events || []);

        if (['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'].includes(data.status) && timer) {
            window.clearInterval(timer);
            timer = null;
        }
    }

    async function refresh() {
        if (!currentRunId) return;
        try {
            const url = urlTemplate.replace('/0/', `/${currentRunId}/`);
            const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
            if (!response.ok) throw new Error('Unable to load automation progress.');
            render(await response.json());
        } catch (error) {
            root.hidden = false;
            const message = query('[data-progress-error]');
            message.hidden = false;
            message.textContent = error.message;
        }
    }

    function watch(runId) {
        currentRunId = String(runId);
        root.dataset.progressRun = currentRunId;
        const url = new URL(window.location.href);
        url.searchParams.set('run', currentRunId);
        window.history.replaceState({}, '', url);
        if (timer) window.clearInterval(timer);
        refresh();
        timer = window.setInterval(refresh, 1500);
    }

    document.querySelectorAll('form.js-start-automation').forEach((form) => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const button = form.querySelector('button[type="submit"]');
            const original = button ? button.innerHTML : '';
            if (button) { button.disabled = true; button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Starting…'; }
            try {
                const response = await fetch(form.action || window.location.href, {
                    method: 'POST',
                    body: new FormData(form),
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
                });
                if (!response.ok) throw new Error('The automation job could not be started.');
                const data = await response.json();
                watch(data.run_id);
            } catch (error) {
                form.submit();
            } finally {
                if (button) { button.disabled = false; button.innerHTML = original; }
            }
        });
    });

    if (currentRunId) watch(currentRunId);
})();
