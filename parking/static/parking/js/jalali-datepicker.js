(function () {
    const monthNames = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
    const weekDays = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
    const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    const digitMap = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    };

    const div = (a, b) => Math.floor(a / b);
    const pad = (value) => String(value).padStart(2, '0');
    const normalize = (value) => String(value || '').replace(/[۰-۹٠-٩]/g, (char) => digitMap[char] || char);
    const faNumber = (value) => String(value).replace(/\d/g, (digit) => persianDigits[Number(digit)]);

    function gregorianToJalali(gy, gm, gd) {
        const gDaysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        const jDaysInMonth = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
        let gy2 = gy - 1600;
        let gm2 = gm - 1;
        let gd2 = gd - 1;
        let gDayNo = 365 * gy2 + div(gy2 + 3, 4) - div(gy2 + 99, 100) + div(gy2 + 399, 400);

        for (let i = 0; i < gm2; i += 1) {
            gDayNo += gDaysInMonth[i];
        }

        if (gm2 > 1 && ((gy2 + 1600) % 4 === 0 && ((gy2 + 1600) % 100 !== 0 || (gy2 + 1600) % 400 === 0))) {
            gDayNo += 1;
        }

        gDayNo += gd2;

        let jDayNo = gDayNo - 79;
        const jNp = div(jDayNo, 12053);
        jDayNo %= 12053;

        let jy = 979 + 33 * jNp + 4 * div(jDayNo, 1461);
        jDayNo %= 1461;

        if (jDayNo >= 366) {
            jy += div(jDayNo - 1, 365);
            jDayNo = (jDayNo - 1) % 365;
        }

        let jm = 0;
        while (jm < 11 && jDayNo >= jDaysInMonth[jm]) {
            jDayNo -= jDaysInMonth[jm];
            jm += 1;
        }

        return { jy, jm: jm + 1, jd: jDayNo + 1 };
    }

    function jalaliToGregorian(jy, jm, jd) {
        const gDaysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        const jDaysInMonth = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
        let jy2 = jy - 979;
        let jm2 = jm - 1;
        let jd2 = jd - 1;
        let jDayNo = 365 * jy2 + div(jy2, 33) * 8 + div((jy2 % 33) + 3, 4);

        for (let i = 0; i < jm2; i += 1) {
            jDayNo += jDaysInMonth[i];
        }

        jDayNo += jd2;

        let gDayNo = jDayNo + 79;
        let gy = 1600 + 400 * div(gDayNo, 146097);
        gDayNo %= 146097;

        let leap = true;
        if (gDayNo >= 36525) {
            gDayNo -= 1;
            gy += 100 * div(gDayNo, 36524);
            gDayNo %= 36524;

            if (gDayNo >= 365) {
                gDayNo += 1;
            } else {
                leap = false;
            }
        }

        gy += 4 * div(gDayNo, 1461);
        gDayNo %= 1461;

        if (gDayNo >= 366) {
            leap = false;
            gDayNo -= 1;
            gy += div(gDayNo, 365);
            gDayNo %= 365;
        }

        let gm = 0;
        while (gm < 11 && gDayNo >= gDaysInMonth[gm] + (gm === 1 && leap ? 1 : 0)) {
            gDayNo -= gDaysInMonth[gm] + (gm === 1 && leap ? 1 : 0);
            gm += 1;
        }

        return { gy, gm: gm + 1, gd: gDayNo + 1 };
    }

    function isLeapJalali(jy) {
        const current = jalaliToGregorian(jy, 12, 30);
        const check = gregorianToJalali(current.gy, current.gm, current.gd);
        return check.jy === jy && check.jm === 12 && check.jd === 30;
    }

    function monthLength(jy, jm) {
        if (jm <= 6) {
            return 31;
        }
        if (jm <= 11) {
            return 30;
        }
        return isLeapJalali(jy) ? 30 : 29;
    }

    function parseValue(value) {
        const parts = normalize(value).trim().replace(/[-.]/g, '/').split('/');
        if (parts.length !== 3 || parts.some((part) => !/^\d+$/.test(part))) {
            return null;
        }

        const parsed = {
            jy: Number(parts[0]),
            jm: Number(parts[1]),
            jd: Number(parts[2]),
        };

        if (parsed.jy < 1200 || parsed.jm < 1 || parsed.jm > 12 || parsed.jd < 1 || parsed.jd > monthLength(parsed.jy, parsed.jm)) {
            return null;
        }

        return parsed;
    }

    function formatValue(jy, jm, jd) {
        return `${jy}/${pad(jm)}/${pad(jd)}`;
    }

    function todayJalali() {
        const today = new Date();
        return gregorianToJalali(today.getFullYear(), today.getMonth() + 1, today.getDate());
    }

    let activeInput = null;
    let shown = todayJalali();
    let picker = null;

    function closePicker() {
        if (picker) {
            picker.hidden = true;
        }
        activeInput = null;
    }

    function positionPicker(input) {
        const rect = input.getBoundingClientRect();
        const width = Math.min(292, window.innerWidth - 24);
        let left = Math.max(12, rect.left);
        const topSpace = rect.top;
        const bottomSpace = window.innerHeight - rect.bottom;
        const openUp = bottomSpace < 300 && topSpace > bottomSpace;
        let top = openUp ? rect.top - 308 : rect.bottom + 8;

        if (left + width > window.innerWidth - 12) {
            left = window.innerWidth - width - 12;
        }

        if (top < 12) {
            top = 12;
        }

        picker.style.width = `${width}px`;
        picker.style.left = `${left}px`;
        picker.style.top = `${top}px`;
    }

    function selectDate(jy, jm, jd) {
        if (!activeInput) {
            return;
        }

        activeInput.value = formatValue(jy, jm, jd);
        activeInput.dispatchEvent(new Event('input', { bubbles: true }));
        activeInput.dispatchEvent(new Event('change', { bubbles: true }));
        closePicker();
    }

    function renderPicker() {
        const selected = activeInput ? parseValue(activeInput.value) : null;
        const firstGregorian = jalaliToGregorian(shown.jy, shown.jm, 1);
        const firstDate = new Date(firstGregorian.gy, firstGregorian.gm - 1, firstGregorian.gd);
        const firstOffset = (firstDate.getDay() + 1) % 7;
        const days = monthLength(shown.jy, shown.jm);
        const today = todayJalali();

        picker.innerHTML = '';

        const header = document.createElement('div');
        header.className = 'jalali-datepicker__header';

        const next = document.createElement('button');
        next.type = 'button';
        next.textContent = 'بعدی';
        next.addEventListener('click', (event) => {
            event.stopPropagation();
            shown.jm += 1;
            if (shown.jm > 12) {
                shown.jm = 1;
                shown.jy += 1;
            }
            renderPicker();
        });

        const title = document.createElement('strong');
        title.textContent = `${monthNames[shown.jm - 1]} ${faNumber(shown.jy)}`;

        const prev = document.createElement('button');
        prev.type = 'button';
        prev.textContent = 'قبلی';
        prev.addEventListener('click', (event) => {
            event.stopPropagation();
            shown.jm -= 1;
            if (shown.jm < 1) {
                shown.jm = 12;
                shown.jy -= 1;
            }
            renderPicker();
        });

        header.append(next, title, prev);
        picker.appendChild(header);

        const grid = document.createElement('div');
        grid.className = 'jalali-datepicker__grid';

        weekDays.forEach((day) => {
            const cell = document.createElement('span');
            cell.className = 'jalali-datepicker__weekday';
            cell.textContent = day;
            grid.appendChild(cell);
        });

        for (let i = 0; i < firstOffset; i += 1) {
            const empty = document.createElement('span');
            empty.className = 'jalali-datepicker__empty';
            grid.appendChild(empty);
        }

        for (let day = 1; day <= days; day += 1) {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = faNumber(day);

            if (selected && selected.jy === shown.jy && selected.jm === shown.jm && selected.jd === day) {
                button.classList.add('is-selected');
            }

            if (today.jy === shown.jy && today.jm === shown.jm && today.jd === day) {
                button.classList.add('is-today');
            }

            button.addEventListener('click', (event) => {
                event.stopPropagation();
                selectDate(shown.jy, shown.jm, day);
            });

            grid.appendChild(button);
        }

        picker.appendChild(grid);

        const footer = document.createElement('div');
        footer.className = 'jalali-datepicker__footer';

        const todayButton = document.createElement('button');
        todayButton.type = 'button';
        todayButton.textContent = 'امروز';
        todayButton.addEventListener('click', (event) => {
            event.stopPropagation();
            const todayValue = todayJalali();
            selectDate(todayValue.jy, todayValue.jm, todayValue.jd);
        });

        const clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.textContent = 'پاک کردن';
        clearButton.addEventListener('click', (event) => {
            event.stopPropagation();
            if (activeInput) {
                activeInput.value = '';
                activeInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            closePicker();
        });

        footer.append(todayButton, clearButton);
        picker.appendChild(footer);
    }

    function openPicker(input) {
        activeInput = input;
        shown = parseValue(input.value) || todayJalali();
        renderPicker();
        picker.hidden = false;
        positionPicker(input);
    }

    function enhanceInput(input) {
        if (input.dataset.jalaliReady === 'true') {
            return;
        }

        input.dataset.jalaliReady = 'true';

        const wrapper = document.createElement('span');
        wrapper.className = 'jalali-picker-field';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'jalali-picker-button';
        button.setAttribute('aria-label', 'انتخاب تاریخ شمسی');
        button.textContent = '▾';
        wrapper.appendChild(button);

        input.addEventListener('click', (event) => {
            event.stopPropagation();
            openPicker(input);
        });
        input.addEventListener('focus', () => openPicker(input));
        button.addEventListener('click', (event) => {
            event.stopPropagation();
            openPicker(input);
        });
    }

    function init() {
        picker = document.createElement('div');
        picker.className = 'jalali-datepicker';
        picker.setAttribute('role', 'dialog');
        picker.hidden = true;
        document.body.appendChild(picker);

        document.querySelectorAll('[data-jalali-datepicker]').forEach(enhanceInput);

        document.addEventListener('click', (event) => {
            if (picker && !picker.contains(event.target)) {
                closePicker();
            }
        });

        window.addEventListener('scroll', () => {
            if (activeInput && picker && !picker.hidden) {
                positionPicker(activeInput);
            }
        }, true);

        window.addEventListener('resize', () => {
            if (activeInput && picker && !picker.hidden) {
                positionPicker(activeInput);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
