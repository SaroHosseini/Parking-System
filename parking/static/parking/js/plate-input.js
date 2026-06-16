(function () {
    const persianDigits = "۰۱۲۳۴۵۶۷۸۹";
    const arabicDigits = "٠١٢٣٤٥٦٧٨٩";

    function normalizeDigits(value) {
        return String(value || "")
            .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
            .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)))
            .replace(/\D/g, "");
    }

    function parseFilterValue(value) {
        if (!value || !value.startsWith("plate-filter:")) {
            return {};
        }

        return value
            .replace("plate-filter:", "")
            .split(";")
            .reduce((parts, pair) => {
                const index = pair.indexOf("=");

                if (index === -1) {
                    return parts;
                }

                const key = pair.slice(0, index);
                const token = pair.slice(index + 1);

                if (key && token) {
                    parts[key] = token;
                }

                return parts;
            }, {});
    }

    function initPlateBuilder(builder) {
        const hiddenInput = document.getElementById(builder.dataset.hiddenInputId);
        const vehicleTypeSelect = builder.dataset.vehicleTypeId
            ? document.getElementById(builder.dataset.vehicleTypeId)
            : null;
        const isFilter = builder.dataset.plateFilter === "true";
        const carPanel = builder.querySelector("[data-plate-car]");
        const motorcyclePanel = builder.querySelector("[data-plate-motorcycle]");
        const motorcycleInput = builder.querySelector("[data-plate-motorcycle-input]");
        const carParts = {
            first: builder.querySelector('[data-plate-car-part="first"]'),
            letter: builder.querySelector('[data-plate-car-part="letter"]'),
            middle: builder.querySelector('[data-plate-car-part="middle"]'),
            region: builder.querySelector('[data-plate-car-part="region"]'),
        };

        if (!hiddenInput || !carPanel || !motorcyclePanel || !motorcycleInput) {
            return;
        }

        function fillFromFilterValue(value) {
            const parts = parseFilterValue(value);

            carParts.first.value = parts.first || "";
            carParts.letter.value = parts.letter || "";
            carParts.middle.value = parts.middle || "";
            carParts.region.value = parts.region || "";
            motorcycleInput.value = parts.motor || "";
        }

        function fillFromValue() {
            const value = hiddenInput.value || "";

            if (isFilter) {
                fillFromFilterValue(value);
                return;
            }

            const carMatch = value.match(/^(\d{2})(.+?)(\d{3})-(\d{2})$/);

            if (carMatch) {
                carParts.first.value = carMatch[1];
                if ([...carParts.letter.options].some((option) => option.value === carMatch[2])) {
                    carParts.letter.value = carMatch[2];
                }
                carParts.middle.value = carMatch[3];
                carParts.region.value = carMatch[4];
                return;
            }

            if (/^\d{8}$/.test(value)) {
                motorcycleInput.value = value;
            }
        }

        function updateFilterValue() {
            const tokens = [];
            const first = normalizeDigits(carParts.first.value).slice(0, 2);
            const middle = normalizeDigits(carParts.middle.value).slice(0, 3);
            const region = normalizeDigits(carParts.region.value).slice(0, 2);
            const motor = normalizeDigits(motorcycleInput.value).slice(0, 8);
            const letter = carParts.letter.value;

            carParts.first.value = first;
            carParts.middle.value = middle;
            carParts.region.value = region;
            motorcycleInput.value = motor;

            if (first) {
                tokens.push(`first=${first}`);
            }

            if (letter) {
                tokens.push(`letter=${letter}`);
            }

            if (middle) {
                tokens.push(`middle=${middle}`);
            }

            if (region) {
                tokens.push(`region=${region}`);
            }

            if (motor) {
                tokens.push(`motor=${motor}`);
            }

            hiddenInput.value = tokens.length ? `plate-filter:${tokens.join(";")}` : "";
        }

        function updateHiddenValue() {
            if (isFilter) {
                updateFilterValue();
                return;
            }

            const isMotorcycle = vehicleTypeSelect && vehicleTypeSelect.value === "motorcycle";

            if (isMotorcycle) {
                hiddenInput.value = normalizeDigits(motorcycleInput.value).slice(0, 8);
                motorcycleInput.value = hiddenInput.value;
                return;
            }

            const first = normalizeDigits(carParts.first.value).slice(0, 2);
            const middle = normalizeDigits(carParts.middle.value).slice(0, 3);
            const region = normalizeDigits(carParts.region.value).slice(0, 2);

            carParts.first.value = first;
            carParts.middle.value = middle;
            carParts.region.value = region;
            hiddenInput.value = first || middle || region
                ? `${first}${carParts.letter.value}${middle}-${region}`
                : "";
        }

        function syncMode() {
            if (!vehicleTypeSelect) {
                carPanel.hidden = false;
                motorcyclePanel.hidden = true;
                return;
            }

            const isMotorcycle = vehicleTypeSelect.value === "motorcycle";
            carPanel.hidden = isMotorcycle;
            motorcyclePanel.hidden = !isMotorcycle;
            updateHiddenValue();
        }

        Object.values(carParts).forEach((field) => {
            field.addEventListener("input", updateHiddenValue);
            field.addEventListener("change", updateHiddenValue);
        });

        [carParts.first, carParts.middle, carParts.region].forEach((field) => {
            field.addEventListener("input", function () {
                if (field.value.length >= Number(field.maxLength)) {
                    const next = field === carParts.first
                        ? carParts.letter
                        : field === carParts.middle
                            ? carParts.region
                            : null;
                    if (next) {
                        next.focus();
                    }
                }
            });
        });

        motorcycleInput.addEventListener("input", updateHiddenValue);
        if (vehicleTypeSelect) {
            vehicleTypeSelect.addEventListener("change", syncMode);
        }

        fillFromValue();
        syncMode();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-plate-builder]").forEach(initPlateBuilder);
    });
}());
