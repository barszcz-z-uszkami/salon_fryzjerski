(function () {
    "use strict";

    var root = document.querySelector("[data-home-carousel]");
    if (!root) return;

    var viewport = root.querySelector("[data-carousel-viewport]");
    var track = root.querySelector("[data-carousel-track]");
    var slides = root.querySelectorAll("[data-carousel-slide]");
    var dots = root.querySelectorAll("[data-carousel-dot]");
    var prevBtn = root.querySelector("[data-carousel-prev]");
    var nextBtn = root.querySelector("[data-carousel-next]");

    var total = slides.length;
    if (!track || !viewport || total === 0) return;

    var MIN_VIEWPORT_H = 200;

    function syncCarouselHeight() {
        var slide = slides[index];
        if (!slide) return;
        var img = slide.querySelector(".carousel-photo");
        var h = 0;
        if (img) {
            h = img.getBoundingClientRect().height;
        }
        if (!h || h < MIN_VIEWPORT_H) {
            h = Math.max(slide.offsetHeight, MIN_VIEWPORT_H);
        }
        viewport.style.height = Math.round(h) + "px";
    }

    var index = 0;
    var autoplayMs = 3000;
    var timer = null;
    var touchStartX = null;

    function goTo(i) {
        index = (i + total) % total;
        track.style.transform = "translateX(-" + index * 100 + "%)";
        dots.forEach(function (dot, j) {
            var on = j === index;
            dot.classList.toggle("is-active", on);
            dot.setAttribute("aria-selected", on ? "true" : "false");
        });
        requestAnimationFrame(function () {
            requestAnimationFrame(syncCarouselHeight);
        });
    }

    function next() {
        goTo(index + 1);
    }

    function prev() {
        goTo(index - 1);
    }

    function resetAutoplay() {
        if (timer) clearInterval(timer);
        timer = setInterval(next, autoplayMs);
    }

    function stopAutoplay() {
        if (timer) clearInterval(timer);
        timer = null;
    }

    if (nextBtn) nextBtn.addEventListener("click", function () {
        next();
        resetAutoplay();
    });
    if (prevBtn) prevBtn.addEventListener("click", function () {
        prev();
        resetAutoplay();
    });

    dots.forEach(function (dot, j) {
        dot.addEventListener("click", function () {
            goTo(j);
            resetAutoplay();
        });
    });

    root.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") {
            e.preventDefault();
            prev();
            resetAutoplay();
        } else if (e.key === "ArrowRight") {
            e.preventDefault();
            next();
            resetAutoplay();
        }
    });

    root.addEventListener("focusin", stopAutoplay);
    root.addEventListener("focusout", resetAutoplay);

    root.addEventListener("mouseenter", stopAutoplay);
    root.addEventListener("mouseleave", resetAutoplay);

    track.addEventListener(
        "touchstart",
        function (e) {
            touchStartX = e.changedTouches[0].screenX;
        },
        { passive: true }
    );

    track.addEventListener(
        "touchend",
        function (e) {
            if (touchStartX == null) return;
            var dx = e.changedTouches[0].screenX - touchStartX;
            touchStartX = null;
            if (Math.abs(dx) < 40) return;
            if (dx < 0) next();
            else prev();
            resetAutoplay();
        },
        { passive: true }
    );

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reduceMotion.matches) {
        track.style.transition = "none";
        stopAutoplay();
    } else {
        resetAutoplay();
    }

    reduceMotion.addEventListener("change", function () {
        if (reduceMotion.matches) {
            track.style.transition = "none";
            stopAutoplay();
        } else {
            track.style.transition = "";
            resetAutoplay();
        }
    });

    slides.forEach(function (slide) {
        var img = slide.querySelector(".carousel-photo");
        if (img) {
            img.addEventListener("load", function () {
                var j = Array.prototype.indexOf.call(slides, slide);
                if (j === index) {
                    syncCarouselHeight();
                }
            });
        }
    });

    var resizeTimer;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(syncCarouselHeight, 120);
    });

    syncCarouselHeight();
    setTimeout(syncCarouselHeight, 50);
    setTimeout(syncCarouselHeight, 300);
})();
