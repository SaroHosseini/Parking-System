document.addEventListener("DOMContentLoaded", () => {
    const modal = document.querySelector("[data-announcement-modal]");
    const form = document.querySelector("[data-announcement-form]");

    if (!modal || !form) {
        return;
    }

    const closeButtons = modal.querySelectorAll("[data-announcement-close]");
    let seenRequestSent = false;

    const markAsSeen = async () => {
        if (seenRequestSent) {
            return;
        }

        seenRequestSent = true;

        try {
            await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });
        } catch (error) {
            seenRequestSent = false;
        }
    };

    const closeModal = () => {
        modal.hidden = true;
        document.body.classList.remove("announcement-open");
    };

    modal.hidden = false;
    document.body.classList.add("announcement-open");
    markAsSeen();

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
});
