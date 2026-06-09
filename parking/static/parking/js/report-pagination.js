(function () {
    function buildFetchUrl(linkUrl) {
        const url = new URL(linkUrl, window.location.href);
        url.searchParams.set('partial', 'closed_sessions');
        url.hash = '';
        return url;
    }

    function buildVisibleUrl(linkUrl) {
        const url = new URL(linkUrl, window.location.href);
        url.searchParams.delete('partial');
        return `${url.pathname}${url.search}${url.hash}`;
    }

    document.addEventListener('click', function (event) {
        const link = event.target.closest('[data-report-closed-panel] .pagination a');

        if (!link) {
            return;
        }

        event.preventDefault();

        const panel = link.closest('[data-report-closed-panel]');
        const fetchUrl = buildFetchUrl(link.href);

        panel.classList.add('is-loading');

        fetch(fetchUrl.toString(), {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Report pagination failed');
                }
                return response.text();
            })
            .then(function (html) {
                panel.innerHTML = html;
                window.history.replaceState(null, '', buildVisibleUrl(link.href));
            })
            .catch(function () {
                window.location.href = link.href;
            })
            .finally(function () {
                panel.classList.remove('is-loading');
            });
    });
}());
