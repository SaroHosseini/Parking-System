(function () {
    const storageKey = 'parkino-theme';
    const root = document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');

    function preferredTheme() {
        const saved = localStorage.getItem(storageKey);
        if (saved === 'light' || saved === 'dark') {
            return saved;
        }
        return media.matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        root.dataset.theme = theme;
        document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
            button.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
            const label = theme === 'dark' ? 'حالت روشن' : 'حالت تاریک';
            button.setAttribute('aria-label', label);
            const text = button.querySelector('[data-theme-label]');
            if (text) {
                text.textContent = label;
            }
        });
    }

    applyTheme(preferredTheme());

    document.addEventListener('click', function (event) {
        const button = event.target.closest('[data-theme-toggle]');
        if (!button) {
            return;
        }

        const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem(storageKey, nextTheme);
        applyTheme(nextTheme);
    });
}());
