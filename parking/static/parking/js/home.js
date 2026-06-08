(function () {
    const revealItems = document.querySelectorAll(
        '.section .section-header, .feature-card, .image-tile, .product-strip > *, .workflow-item, .contact-panel'
    );

    if (!revealItems.length) {
        return;
    }

    revealItems.forEach((item, index) => {
        item.classList.add('scroll-reveal');
        item.style.setProperty('--reveal-delay', `${Math.min(index % 5, 4) * 70}ms`);
    });

    if (!('IntersectionObserver' in window)) {
        revealItems.forEach((item) => item.classList.add('is-visible'));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) {
                    return;
                }
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            });
        },
        {
            threshold: 0.16,
            rootMargin: '0px 0px -8% 0px',
        }
    );

    revealItems.forEach((item) => observer.observe(item));
}());
