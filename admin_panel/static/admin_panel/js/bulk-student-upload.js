(function () {
  const root = document.querySelector('.bulk-student-page');
  if (!root) return;

  const input = root.querySelector('[data-file-input]');
  const zone = root.querySelector('[data-dropzone]');
  const output = root.querySelector('[data-file-output]');
  const overlay = document.querySelector('[data-progress-overlay]');
  const closeButton = overlay && overlay.querySelector('[data-progress-close]');
  let progressTimer = null;
  let elapsedTimer = null;
  let startedAt = 0;
  let estimatedSeconds = 5;
  let currentProgress = 0;
  let requestFailed = false;

  function showFile() {
    const file = input && input.files[0];
    if (output) output.textContent = file ? `${file.name} - ${(file.size / 1048576).toFixed(2)} MB` : 'No file selected';
  }

  if (input) input.addEventListener('change', showFile);
  if (zone) {
    ['dragenter', 'dragover'].forEach((name) => zone.addEventListener(name, (event) => {
      event.preventDefault();
      zone.classList.add('is-dragging');
    }));
    ['dragleave', 'drop'].forEach((name) => zone.addEventListener(name, (event) => {
      event.preventDefault();
      zone.classList.remove('is-dragging');
    }));
    zone.addEventListener('drop', (event) => {
      if (event.dataTransfer.files.length) {
        input.files = event.dataTransfer.files;
        showFile();
      }
    });
  }

  function escapeHtml(value) {
    const element = document.createElement('span');
    element.textContent = value == null ? '' : String(value);
    return element.innerHTML;
  }

  function updateCounter(selector, value) {
    const element = root.querySelector(selector);
    if (element && value !== undefined && value !== null) element.textContent = value;
  }

  function updateDeliveryReport(result) {
    if (!result) return;
    updateCounter('[data-report-login-ready]', result.login_ready);
    updateCounter('[data-report-emails-sent]', result.emails_sent);
    updateCounter('[data-report-emails-pending]', result.emails_pending);
    updateCounter('[data-report-emails-failed]', result.emails_failed);
    updateCounter('[data-report-messages-sent]', result.messages_sent);
    updateCounter('[data-report-messages-pending]', result.messages_pending);
    updateCounter('[data-report-messages-failed]', result.messages_failed);
  }

  async function refreshActivity() {
    try {
      const response = await fetch(root.dataset.activityUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!response.ok) return;
      const data = await response.json();
      updateCounter('[data-student-count]', data.student_count);
      updateCounter('[data-parent-count]', data.parent_count);
      updateCounter('[data-live-updated]', data.updated_at);
      updateDeliveryReport(data.result);

      const students = root.querySelector('[data-student-activity]');
      if (students) students.innerHTML = data.students.length ? data.students.map((student) => `
        <a class="bulk-activity-row" href="${escapeHtml(student.url)}">
          <span class="bulk-avatar"><i class="fa fa-user-graduate"></i></span>
          <span><b>${escapeHtml(student.name)}</b><small>${escapeHtml(student.student_id)} - ${escapeHtml(student.class_name)}${student.section ? ` - ${escapeHtml(student.section)}` : ''}</small></span>
          <i class="fa fa-chevron-right"></i>
        </a>`).join('') : '<p class="bulk-empty">No students imported yet.</p>';

      const parents = root.querySelector('[data-parent-activity]');
      if (parents) parents.innerHTML = data.parents.length ? data.parents.map((parent) => `
        <div class="bulk-activity-row">
          <span class="bulk-avatar"><i class="fa fa-users"></i></span>
          <span><b>${escapeHtml(parent.name)}</b><small>${escapeHtml(parent.email)} - ${parent.children} linked child${parent.children === 1 ? '' : 'ren'}</small></span>
        </div>`).join('') : '<p class="bulk-empty">No parents linked yet.</p>';
    } catch (error) {
      // Retain server-rendered values if live polling is unavailable.
    }
  }

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds < 1) return '< 1s';
    const rounded = Math.ceil(seconds);
    if (rounded < 60) return `${rounded}s`;
    const minutes = Math.floor(rounded / 60);
    const remaining = rounded % 60;
    return remaining ? `${minutes}m ${remaining}s` : `${minutes}m`;
  }

  function setProgress(value, copy) {
    if (!overlay) return;
    currentProgress = Math.max(0, Math.min(100, Math.round(value)));
    overlay.querySelector('[data-progress-ring]').style.setProperty('--progress', `${currentProgress * 3.6}deg`);
    overlay.querySelector('[data-progress-bar]').style.width = `${currentProgress}%`;
    overlay.querySelector('[data-progress-percent]').textContent = `${currentProgress}%`;
    if (copy && copy.stage) overlay.querySelector('[data-progress-stage]').textContent = copy.stage;
    if (copy && copy.title) overlay.querySelector('[data-progress-title]').textContent = copy.title;
    if (copy && copy.detail) overlay.querySelector('[data-progress-detail]').textContent = copy.detail;
  }

  function updateTimes() {
    if (!overlay || !startedAt) return;
    const elapsed = (Date.now() - startedAt) / 1000;
    overlay.querySelector('[data-progress-elapsed]').textContent = formatDuration(elapsed);
    overlay.querySelector('[data-progress-remaining]').textContent = currentProgress >= 100 ? 'Complete' : formatDuration(Math.max(0, estimatedSeconds - elapsed));
  }

  function stopTimers() {
    window.clearInterval(progressTimer);
    window.clearInterval(elapsedTimer);
    progressTimer = null;
    elapsedTimer = null;
  }

  function beginProcessing(mode) {
    window.clearInterval(progressTimer);
    setProgress(Math.max(currentProgress, mode === 'validate' ? 38 : 12), {
      stage: mode === 'validate' ? 'Checking spreadsheet' : 'Creating live records',
      title: mode === 'validate' ? 'Validating student and parent data' : 'Importing students and portal accounts',
      detail: mode === 'validate'
        ? 'Checking columns, duplicates, class placement and account readiness.'
        : 'Creating students, parents, login accounts, fee links and delivery queues.',
    });
    progressTimer = window.setInterval(() => {
      const elapsed = (Date.now() - startedAt) / 1000;
      const target = 38 + (Math.min(0.96, elapsed / Math.max(estimatedSeconds, 1)) * 56);
      if (currentProgress < 94) setProgress(Math.min(94, Math.max(currentProgress + 1, target)));
    }, 450);
  }

  function showProgress(form) {
    if (!overlay) return;
    const mode = form.dataset.progressMode || 'validate';
    const rows = Number(form.dataset.totalRows || 0);
    const file = input && input.files[0];
    const megabytes = file ? file.size / 1048576 : 0;
    estimatedSeconds = mode === 'import' ? Math.max(5, 3 + (rows * 0.22)) : Math.max(4, 2.5 + (megabytes * 1.7));
    startedAt = Date.now();
    currentProgress = 0;
    requestFailed = false;
    overlay.hidden = false;
    document.body.classList.add('bulk-progress-open');
    closeButton.hidden = true;
    setProgress(2, {
      stage: mode === 'validate' ? 'Uploading spreadsheet' : 'Starting import',
      title: mode === 'validate' ? 'Preparing student data' : `Importing ${rows} validated row${rows === 1 ? '' : 's'}`,
      detail: 'Keep this page open. Progress reaches 100% only after EduPilot confirms completion.',
    });
    elapsedTimer = window.setInterval(updateTimes, 250);
    updateTimes();
  }

  function showFailure(message) {
    requestFailed = true;
    stopTimers();
    setProgress(currentProgress, { stage: 'Import interrupted', title: 'EduPilot could not complete this request', detail: message });
    overlay.querySelector('[data-progress-remaining]').textContent = 'Stopped';
    closeButton.hidden = false;
  }

  function getCookie(name) {
    const prefix = `${name}=`;
    return document.cookie.split(';').map((value) => value.trim()).find((value) => value.startsWith(prefix))?.slice(prefix.length) || '';
  }

  function submitWithProgress(form, csrfToken) {
    const button = form.querySelector('[type="submit"]');
    if (button && button.disabled) return;
    const mode = form.dataset.progressMode || 'validate';
    showProgress(form);
    if (button) button.disabled = true;

    const request = new XMLHttpRequest();
    // A hidden field named "action" shadows HTMLFormElement.action, so read the
    // attribute directly to avoid posting to "[object HTMLInputElement]".
    const requestUrl = form.getAttribute('action') || window.location.pathname;
    request.open((form.method || 'POST').toUpperCase(), requestUrl, true);
    request.withCredentials = true;
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    request.setRequestHeader('X-CSRFToken', csrfToken);
    request.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable || mode !== 'validate') return;
      setProgress(3 + ((event.loaded / event.total) * 32), { stage: 'Uploading spreadsheet', title: `Uploading ${input.files[0].name}` });
    });
    request.upload.addEventListener('load', () => beginProcessing(mode));
    request.addEventListener('load', () => {
      if (request.status >= 200 && request.status < 400) {
        stopTimers();
        setProgress(100, {
          stage: 'Completed',
          title: mode === 'validate' ? 'Validation report is ready' : 'Student import completed',
          detail: mode === 'validate' ? 'Opening the validation preview.' : 'Opening the complete import and delivery report.',
        });
        updateTimes();
        window.setTimeout(() => {
          document.open();
          document.write(request.responseText);
          document.close();
        }, 450);
      } else {
        showFailure(`The server returned status ${request.status}. Completion was not confirmed.`);
        if (button) button.disabled = false;
      }
    });
    request.addEventListener('error', () => {
      showFailure('The server could not be reached. The import was not confirmed.');
      if (button) button.disabled = false;
    });
    request.addEventListener('timeout', () => {
      showFailure('The request timed out before completion was confirmed.');
      if (button) button.disabled = false;
    });
    request.send(new FormData(form));
  }

  root.querySelectorAll('[data-progress-form]').forEach((form) => form.addEventListener('submit', (event) => {
    if (!form.reportValidity()) {
      event.preventDefault();
      return;
    }

    event.preventDefault();
    const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput?.value || getCookie('csrftoken');
    if (!csrfToken) {
      showProgress(form);
      showFailure('Your secure session token is unavailable. Reload this page and try again. No data was submitted.');
      return;
    }
    submitWithProgress(form, csrfToken);
  }));

  if (closeButton) closeButton.addEventListener('click', () => {
    if (!requestFailed) return;
    overlay.hidden = true;
    document.body.classList.remove('bulk-progress-open');
  });

  window.setInterval(refreshActivity, 15000);
})();
