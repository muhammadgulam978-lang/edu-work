(function () {
    const modal = document.querySelector('[data-announcement-modal]');
    if (!modal) return;
    const open = () => { modal.classList.add('show'); modal.setAttribute('aria-hidden', 'false'); };
    const close = () => { modal.classList.remove('show'); modal.setAttribute('aria-hidden', 'true'); };
    document.querySelectorAll('[data-open-announcement]').forEach((button) => button.addEventListener('click', open));
    document.querySelectorAll('[data-close-announcement]').forEach((button) => button.addEventListener('click', close));
    modal.addEventListener('click', (event) => { if (event.target === modal) close(); });
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') close(); });
}());
