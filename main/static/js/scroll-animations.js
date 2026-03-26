// D:\Django Internship\tprmsystem\main\static\js\scroll-animations.js
function initScrollAnimations() {
    // Check if GSAP and ScrollTrigger are loaded
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
        console.error('GSAP or ScrollTrigger not found. Please ensure both libraries are loaded.');
        return;
    }

    // Register ScrollTrigger plugin
    gsap.registerPlugin(ScrollTrigger);

    // Initialize all elements to be invisible
    const elements = gsap.utils.toArray('.pooja1-title, .pooja1-subtitle, .pooja1-card, .pooja1-btn');
    elements.forEach(el => {
        gsap.set(el, { opacity: 0, y: 20 });
    });

    // Title animation
    if (document.querySelector('.pooja1-title')) {
        gsap.to(".pooja1-title", {
            y: 0,
            opacity: 1,
            duration: 0.8,
            ease: "power2.out",
            scrollTrigger: {
                trigger: "#pooja1-section",
                start: "top 80%",
                once: true
            }
        });
    }

    // Subtitle animation
    if (document.querySelector('.pooja1-subtitle')) {
        gsap.to(".pooja1-subtitle", {
            y: 0,
            opacity: 1,
            duration: 0.8,
            delay: 0.2,
            ease: "power2.out",
            scrollTrigger: {
                trigger: "#pooja1-section",
                start: "top 75%",
                once: true
            }
        });
    }

    // Cards animation
    const cards = document.querySelectorAll('.pooja1-card');
    if (cards.length > 0) {
        cards.forEach((card, i) => {
            gsap.to(card, {
                y: 0,
                opacity: 1,
                duration: 0.6,
                delay: i * 0.15,
                ease: "back.out(1.2)",
                scrollTrigger: {
                    trigger: ".pooja1-cards",
                    start: "top 85%",
                    once: true
                }
            });
        });
    }

    // Button animation
    const button = document.querySelector('.pooja1-btn');
    if (button) {
        gsap.to(button, {
            y: 0,
            opacity: 1,
            duration: 0.8,
            delay: 0.4,
            ease: "back.out(1.7)",
            scrollTrigger: {
                trigger: ".pooja1-cards",
                start: "top 70%",
                once: true
            }
        });
    }
}

// Wait for DOM and GSAP to be ready
document.addEventListener("DOMContentLoaded", () => {
    // If GSAP is already loaded, initialize animations
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
        initScrollAnimations();
    } else {
        // If not, wait for window load
        window.addEventListener('load', initScrollAnimations);
    }
});