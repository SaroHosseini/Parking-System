document.addEventListener("DOMContentLoaded", () => {
    const modal = document.querySelector("[data-bug-report-modal]");
    const openButtons = document.querySelectorAll("[data-bug-report-open]");
    const closeButtons = document.querySelectorAll("[data-bug-report-close]");
    const form = document.querySelector("[data-bug-report-form]");

    if (!modal || !form || !openButtons.length) {
        return;
    }

    const messageBox = form.querySelector("[data-bug-report-message]");
    const submitButton = form.querySelector("[data-bug-report-submit]");
    const fieldErrors = form.querySelectorAll("[data-bug-report-error]");

    const clearErrors = () => {
        fieldErrors.forEach((container) => {
            container.innerHTML = "";
        });
        if (messageBox) {
            messageBox.textContent = "";
            messageBox.className = "bug-report-message";
        }
    };

    const openModal = () => {
        clearErrors();
        modal.hidden = false;
        document.body.classList.add("bug-report-open");
        const firstField = form.querySelector("[data-bug-report-field]");
        if (firstField) {
            firstField.focus();
        }
    };

    const closeModal = () => {
        modal.hidden = true;
        document.body.classList.remove("bug-report-open");
    };

    const setMessage = (text, kind) => {
        if (!messageBox) {
            return;
        }
        messageBox.textContent = text || "";
        messageBox.className = `bug-report-message ${kind ? `is-${kind}` : ""}`.trim();
    };

    const renderFieldErrors = (errors) => {
        Object.entries(errors || {}).forEach(([field, messages]) => {
            const container = form.querySelector(`[data-bug-report-error="${field}"]`);
            if (!container) {
                return;
            }

            const list = document.createElement("ul");
            list.className = "errorlist";

            messages.forEach((message) => {
                const item = document.createElement("li");
                item.textContent = message;
                list.appendChild(item);
            });

            container.replaceChildren(list);
        });
    };

    openButtons.forEach((button) => {
        button.addEventListener("click", openModal);
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeModal);
    });

    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearErrors();
        setMessage("", "");

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "در حال ثبت...";
        }

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });
            const data = await response.json();

            if (!response.ok || !data.ok) {
                renderFieldErrors(data.errors);
                setMessage(data.message || "ثبت گزارش انجام نشد.", "error");
                return;
            }

            form.reset();
            setMessage(data.message || "پیام گزارش مشکل ثبت شد. باتشکر.", "success");
        } catch (error) {
            setMessage("ارتباط با سرور برقرار نشد. دوباره تلاش کنید.", "error");
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = "ثبت گزارش";
            }
        }
    });
});
