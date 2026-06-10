(function () {
    function debounce(callback, delay) {
        let timer;
        return function (...args) {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => callback.apply(this, args), delay);
        };
    }

    function initSpotPicker(picker) {
        const apiUrl = picker.dataset.apiUrl;
        const hiddenInput = document.getElementById(picker.dataset.inputId);
        const vehicleTypeSelect = document.getElementById(picker.dataset.vehicleTypeId);
        const searchInput = picker.querySelector('[data-spot-search]');
        const list = picker.querySelector('[data-spot-list]');
        const status = picker.querySelector('[data-spot-status]');
        const selectedLabel = picker.querySelector('[data-spot-selected]');
        const prevButton = picker.querySelector('[data-spot-prev]');
        const nextButton = picker.querySelector('[data-spot-next]');
        const clearButton = picker.querySelector('[data-spot-clear]');

        let page = 1;
        let currentQuery = '';

        function setSelected(spot) {
            if (!spot) {
                hiddenInput.value = '';
                selectedLabel.textContent = 'هنوز جایگاهی انتخاب نشده است';
                return;
            }

            hiddenInput.value = spot.id;
            selectedLabel.textContent = spot.text;
        }

        function renderSpots(data) {
            list.innerHTML = '';

            if (data.selected_spot && String(data.selected_spot.id) === String(hiddenInput.value)) {
                selectedLabel.textContent = data.selected_spot.text;
            }

            if (
                hiddenInput.value &&
                !data.selected_spot &&
                !data.spots.some((spot) => String(spot.id) === String(hiddenInput.value))
            ) {
                setSelected(null);
            }

            if (!data.spots.length) {
                const empty = document.createElement('div');
                empty.className = 'spot-picker__empty';
                empty.textContent = 'جایگاه آزادی با این جستجو پیدا نشد.';
                list.appendChild(empty);
            }

            data.spots.forEach((spot) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'spot-option';
                if (String(spot.id) === String(hiddenInput.value)) {
                    button.classList.add('is-selected');
                }
                button.dataset.spotId = spot.id;

                const code = document.createElement('strong');
                code.textContent = spot.code;

                const meta = document.createElement('span');
                meta.textContent = `${spot.parking_lot} · ${spot.level} · ${spot.type}`;

                button.append(code, meta);
                button.addEventListener('click', function () {
                    setSelected(spot);
                    renderSpots(data);
                });
                list.appendChild(button);
            });

            const firstItem = data.total === 0 ? 0 : ((data.page - 1) * data.page_size) + 1;
            const lastItem = Math.min(data.page * data.page_size, data.total);
            status.textContent = data.total
                ? `${firstItem} تا ${lastItem} از ${data.total} جایگاه`
                : '۰ جایگاه';

            prevButton.disabled = !data.has_previous;
            nextButton.disabled = !data.has_next;
        }

        function loadSpots() {
            const params = new URLSearchParams({
                vehicle_type: vehicleTypeSelect ? vehicleTypeSelect.value : '',
                q: currentQuery,
                page: String(page),
                page_size: '10',
                selected_id: hiddenInput.value || '',
            });

            list.innerHTML = '<div class="spot-picker__empty">در حال دریافت جایگاه‌ها...</div>';

            fetch(`${apiUrl}?${params.toString()}`)
                .then((response) => response.json())
                .then(renderSpots)
                .catch(() => {
                    list.innerHTML = '<div class="spot-picker__empty">دریافت جایگاه‌ها با خطا روبه‌رو شد.</div>';
                    status.textContent = 'خطا';
                });
        }

        searchInput.addEventListener('input', debounce(function () {
            currentQuery = searchInput.value.trim();
            page = 1;
            loadSpots();
        }, 250));

        prevButton.addEventListener('click', function () {
            if (page > 1) {
                page -= 1;
                loadSpots();
            }
        });

        nextButton.addEventListener('click', function () {
            page += 1;
            loadSpots();
        });

        clearButton.addEventListener('click', function () {
            setSelected(null);
            loadSpots();
        });

        if (vehicleTypeSelect) {
            vehicleTypeSelect.addEventListener('change', function () {
                setSelected(null);
                page = 1;
                currentQuery = '';
                searchInput.value = '';
                loadSpots();
            });
        }

        loadSpots();
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-spot-picker]').forEach(initSpotPicker);
    });
}());
