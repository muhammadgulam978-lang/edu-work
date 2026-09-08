(function () {
  const root = document.querySelector('.bulk-student-page');
  if (!root) return;
  const isTeacher = root.dataset.entity === 'teacher';

  const input = root.querySelector('[data-file-input]');
  const zone = root.querySelector('[data-dropzone]');
  const output = root.querySelector('[data-file-output]');
  const overlay = document.querySelector('[data-progress-overlay]');
  const closeButton = overlay && overlay.querySelector('[data-progress-close]');
  let elapsedTimer = null;
  let startedAt = 0;
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
      if (isTeacher) {
        updateCounter('[data-teacher-count]', data.teacher_count);
        updateCounter('[data-login-count]', data.login_count);
        updateCounter('[data-live-updated]', data.updated_at);
        const activity = root.querySelector('[data-teacher-activity]');
        if (activity) activity.innerHTML = data.teachers.length ? data.teachers.map((teacher) =>
          `<a class="bulk-activity-row" href="${escapeHtml(teacher.url)}"><span class="bulk-avatar"><i class="fa fa-chalkboard-teacher"></i></span><span><b>${escapeHtml(teacher.name)}</b><small>${escapeHtml(teacher.email)} · ${escapeHtml(teacher.department)}</small></span><i class="fa fa-chevron-right"></i></a>`
        ).join('') : '<p class="bulk-empty">No teachers imported yet.</p>';
        return;
      }
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
      // Keep server-rendered values when live polling is unavailable.
    }
  }

  function formatDuration(seconds) {
    if (seconds === null || seconds === undefined || !Number.isFinite(Number(seconds))) return 'Calculating';
    if (Number(seconds) < 1) return '< 1s';
    const rounded = Math.ceil(Number(seconds));
    if (rounded < 60) return `${rounded}s`;
    const minutes = Math.floor(rounded / 60);
    const remaining = rounded % 60;
    return remaining ? `${minutes}m ${remaining}s` : `${minutes}m`;
  }

  function setProgress(value, copy) {
    if (!overlay) return;
    if (isTeacher && copy) {
      copy = { ...copy };
      for (const key of ['stage', 'title', 'detail']) {
        if (copy[key]) copy[key] = copy[key]
          .replace('student and parent data', 'teacher profile and login data')
          .replace('student data, duplicates, placement, parent links and fee readiness', 'teacher data, duplicate accounts, subjects and faculty groups')
          .replace('students, parents, portal accounts, fee links and delivery queues', 'teachers, portal accounts and subject assignments')
          .replace('import and delivery report', 'teacher import report')
          .replace(/Student/g, 'Teacher').replace(/student/g, 'teacher');
      }
    }
    currentProgress = Math.max(0, Math.min(100, Math.round(value)));
    overlay.querySelector('[data-progress-ring]').style.setProperty('--progress', `${currentProgress * 3.6}deg`);
    overlay.querySelector('[data-progress-bar]').style.width = `${currentProgress}%`;
    overlay.querySelector('[data-progress-percent]').textContent = `${currentProgress}%`;
    if (copy && copy.stage) overlay.querySelector('[data-progress-stage]').textContent = copy.stage;
    if (copy && copy.title) overlay.querySelector('[data-progress-title]').textContent = copy.title;
    if (copy && copy.detail) overlay.querySelector('[data-progress-detail]').textContent = copy.detail;
    if (copy && Object.prototype.hasOwnProperty.call(copy, 'elapsed')) {
      overlay.querySelector('[data-progress-elapsed]').textContent = formatDuration(copy.elapsed);
    }
    if (copy && Object.prototype.hasOwnProperty.call(copy, 'remaining')) {
      overlay.querySelector('[data-progress-remaining]').textContent = copy.remaining === 0 ? 'Complete' : formatDuration(copy.remaining);
    }
  }

  function updateElapsed() {
    if (!overlay || !startedAt) return;
    overlay.querySelector('[data-progress-elapsed]').textContent = formatDuration((Date.now() - startedAt) / 1000);
  }

  function stopTimer() {
    window.clearInterval(elapsedTimer);
    elapsedTimer = null;
  }

  function showProgress(form) {
    if (!overlay) return;
    const mode = form.dataset.progressMode || 'validate';
    const rows = Number(form.dataset.totalRows || 0);
    startedAt = Date.now();
    currentProgress = 0;
    requestFailed = false;
    overlay.hidden = false;
    document.body.classList.add('bulk-progress-open');
    closeButton.hidden = true;
    const activation = mode === 'activation';
    const estimate = root.querySelector('[data-progress-estimate]');
    setProgress(0, {
      stage: activation ? 'Preparing portal access' : (mode === 'validate' ? 'Uploading spreadsheet' : 'Starting validated import'),
      title: activation ? `Activating ${rows} student login${rows === 1 ? '' : 's'}` : (mode === 'validate' ? 'Preparing student data' : `Importing ${rows} validated row${rows === 1 ? '' : 's'}`),
      detail: activation ? 'Secure passwords will be created in small server-confirmed batches.' : 'Keep this page open. Progress is confirmed from the server.',
      elapsed: 0,
      remaining: null,
    });
    if (estimate) {
      estimate.textContent = activation
        ? 'Login activation progress, elapsed time and remaining time are based on accounts completed by the server.'
        : 'Upload progress uses transferred bytes. Import progress, elapsed time and remaining time use rows committed by the server.';
    }
    elapsedTimer = window.setInterval(updateElapsed, 250);
  }

  function showFailure(message) {
    requestFailed = true;
    stopTimer();
    setProgress(currentProgress, {
      stage: 'Import interrupted',
      title: 'EduPilot could not complete this request',
      detail: message,
    });
    overlay.querySelector('[data-progress-remaining]').textContent = 'Stopped';
    closeButton.hidden = false;
  }

  function getCookie(name) {
    const prefix = `${name}=`;
    return document.cookie.split(';').map((value) => value.trim()).find((value) => value.startsWith(prefix))?.slice(prefix.length) || '';
  }

  function responseMessage(request) {
    try {
      const payload = JSON.parse(request.responseText);
      if (payload.error) return payload.error;
    } catch (error) {
      // The validation endpoint returns HTML; use a concise status fallback.
    }
    return `The server returned status ${request.status}. Completion was not confirmed.`;
  }

  async function continueValidation(uploadState, csrfToken) {
    let state = await postProgress({
      operation: 'validate_start',
      upload_token: uploadState.token,
    }, csrfToken);
    setProgress(state.percent, {
      stage: 'Validating on server',
      title: `Checked ${state.processed_rows} of ${state.total_rows} rows`,
      detail: 'Checking student data, duplicates, placement, parent links and fee readiness.',
      elapsed: state.elapsed_seconds,
      remaining: state.eta_seconds,
    });
    while (!state.done) {
      state = await postProgress({
        operation: 'validate_process',
        upload_token: uploadState.token,
        cursor: state.cursor,
      }, csrfToken);
      setProgress(state.percent, {
        stage: state.done ? 'Completed' : 'Validating on server',
        title: state.done
          ? 'Validation report is ready'
          : `Checked ${state.processed_rows} of ${state.total_rows} rows`,
        detail: state.done
          ? 'Opening the validation preview.'
          : 'Progress and remaining time are calculated from rows confirmed by the server.',
        elapsed: state.elapsed_seconds,
        remaining: state.eta_seconds,
      });
    }
    stopTimer();
    window.setTimeout(() => window.location.assign(state.redirect_url), 250);
  }

  function submitValidation(form, csrfToken) {
    const button = form.querySelector('[type="submit"]');
    showProgress(form);
    if (button) button.disabled = true;
    const request = new XMLHttpRequest();
    const requestUrl = form.getAttribute('action') || window.location.pathname;
    request.open((form.method || 'POST').toUpperCase(), requestUrl, true);
    request.timeout = 10 * 60 * 1000;
    request.withCredentials = true;
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    request.setRequestHeader('X-CSRFToken', csrfToken);
    request.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) return;
      setProgress((event.loaded / event.total) * 100, {
        stage: 'Uploading spreadsheet',
        title: `Uploading ${input.files[0].name}`,
        detail: `${Math.round(event.loaded / 1024)} KB of ${Math.round(event.total / 1024)} KB uploaded.`,
      });
    });
    request.upload.addEventListener('load', () => setProgress(0, {
      stage: 'Validating on server',
      title: 'Checking student and parent data',
      detail: 'Waiting for the first server-confirmed row batch.',
      elapsed: 0,
      remaining: null,
    }));
    request.addEventListener('load', async () => {
      if (request.status >= 200 && request.status < 400) {
        try {
          const uploadState = JSON.parse(request.responseText);
          if (!uploadState.validation_pending || !uploadState.token) {
            throw new Error('The server did not return a valid bulk validation session.');
          }
          await continueValidation(uploadState, csrfToken);
        } catch (error) {
          showFailure(error.message || 'Validation stopped before completion was confirmed.');
          if (button) button.disabled = false;
        }
      } else {
        showFailure(responseMessage(request));
        if (button) button.disabled = false;
      }
    });
    request.addEventListener('error', () => {
      showFailure('The server could not be reached. No completion was confirmed.');
      if (button) button.disabled = false;
    });
    request.addEventListener('timeout', () => {
      showFailure('The request timed out before validation was confirmed.');
      if (button) button.disabled = false;
    });
    request.send(new FormData(form));
  }

  async function postProgress(payload, csrfToken) {
    const body = new URLSearchParams(payload);
    const response = await fetch(root.dataset.importProgressUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
      },
      body,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `The server returned status ${response.status}.`);
    return data;
  }

  async function submitChunkedImport(form, csrfToken) {
    const button = form.querySelector('[type="submit"]');
    const token = form.querySelector('[name="upload_token"]').value;
    showProgress(form);
    if (button) button.disabled = true;
    try {
      let state = await postProgress({ operation: 'start', upload_token: token }, csrfToken);
      while (!state.done) {
        state = await postProgress({ operation: 'process', upload_token: token, cursor: state.cursor }, csrfToken);
        setProgress(state.percent, {
          stage: state.done ? 'Completed' : 'Creating live records',
          title: state.done ? 'Student import completed' : `Processed ${state.processed_rows} of ${state.total_rows} rows`,
          detail: state.done
            ? 'Opening the complete import and delivery report.'
            : 'Committed students, parents, portal accounts, fee links and delivery queues are included.',
          elapsed: state.elapsed_seconds,
          remaining: state.eta_seconds,
        });
      }
      stopTimer();
      window.setTimeout(() => window.location.assign(state.redirect_url), 250);
    } catch (error) {
      showFailure(error.message || 'The import stopped before completion was confirmed.');
      if (button) button.disabled = false;
    }
  }

  async function postActivation(form, payload, csrfToken) {
    const response = await fetch(form.getAttribute('action'), {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
      },
      body: new URLSearchParams(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `The server returned status ${response.status}.`);
    return data;
  }

  async function submitLoginActivation(form, csrfToken) {
    const button = form.querySelector('[type="submit"]');
    showProgress(form);
    if (button) button.disabled = true;
    try {
      let state = await postActivation(form, { operation: 'start' }, csrfToken);
      while (!state.done) {
        state = await postActivation(form, { operation: 'process', cursor: state.cursor }, csrfToken);
        setProgress(state.percent, {
          stage: state.done ? 'Portal access ready' : 'Creating secure credentials',
          title: state.done ? 'Student logins activated' : `Activated ${state.processed_rows} of ${state.total_rows} logins`,
          detail: state.done
            ? 'Opening the report and downloadable portal credentials.'
            : 'Each completed batch is saved by the server before the next batch starts.',
          elapsed: state.elapsed_seconds,
          remaining: state.eta_seconds,
        });
      }
      stopTimer();
      window.setTimeout(() => window.location.assign(state.redirect_url), 250);
    } catch (error) {
      showFailure(error.message || 'Portal activation stopped before completion was confirmed.');
      if (button) button.disabled = false;
    }
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
      showFailure('Your secure session token is unavailable. Reload this page and try again.');
      return;
    }
    if ((form.dataset.progressMode || 'validate') === 'import') {
      submitChunkedImport(form, csrfToken);
    } else {
      submitValidation(form, csrfToken);
    }
  }));

  const activationForm = root.querySelector('[data-activation-form]');
  if (activationForm) activationForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const csrfInput = activationForm.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput?.value || getCookie('csrftoken');
    if (!csrfToken) {
      showProgress(activationForm);
      showFailure('Your secure session token is unavailable. Reload this page and try again.');
      return;
    }
    submitLoginActivation(activationForm, csrfToken);
  });

  if (closeButton) closeButton.addEventListener('click', () => {
    if (!requestFailed) return;
    overlay.hidden = true;
    document.body.classList.remove('bulk-progress-open');
  });

  window.setInterval(refreshActivity, 15000);
})();
