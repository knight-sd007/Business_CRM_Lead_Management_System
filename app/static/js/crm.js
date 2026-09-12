/**
 * Business CRM Lead Management System
 * Vanilla JavaScript UI Enhancement Foundation
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Mobile Navigation Toggle
    const navToggle = document.querySelector(".mobile-nav-toggle");
    const navMenu = document.querySelector(".nav-menu-wrapper");

    if (navToggle && navMenu) {
        navToggle.addEventListener("click", () => {
            const isExpanded = navToggle.getAttribute("aria-expanded") === "true";
            navToggle.setAttribute("aria-expanded", String(!isExpanded));
            navMenu.classList.toggle("nav-open");
        });

        // Close menu when clicking outside
        document.addEventListener("click", (e) => {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navToggle.setAttribute("aria-expanded", "false");
                navMenu.classList.remove("nav-open");
            }
        });
    }

    // 2. Alert Dismissal
    document.querySelectorAll(".alert-dismissible").forEach((alert) => {
        const closeBtn = alert.querySelector(".alert-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => {
                alert.style.opacity = "0";
                setTimeout(() => alert.remove(), 200);
            });
        }
    });

    // 3. Modal Foundation
    let activeModal = null;
    let previousActiveElement = null;

    function openModal(modal) {
        if (!modal) return;
        previousActiveElement = document.activeElement;
        modal.classList.add("modal-active");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        activeModal = modal;

        // Focus first interactive element or modal itself
        const focusable = modal.querySelectorAll("button, [href], input, select, textarea, [tabindex]:not([tabindex=\"-1\"])");
        if (focusable.length > 0) {
            focusable[0].focus();
        } else {
            modal.focus();
        }
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.remove("modal-active");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open");
        if (previousActiveElement && typeof previousActiveElement.focus === "function") {
            previousActiveElement.focus();
        }
        activeModal = null;
    }

    // Open triggers
    document.querySelectorAll("[data-modal-target]").forEach((trigger) => {
        trigger.addEventListener("click", (e) => {
            e.preventDefault();
            const targetId = trigger.getAttribute("data-modal-target");
            const targetModal = document.getElementById(targetId);
            openModal(targetModal);
        });
    });

    // Close triggers
    document.querySelectorAll("[data-modal-close]").forEach((trigger) => {
        trigger.addEventListener("click", (e) => {
            e.preventDefault();
            const modal = trigger.closest(".modal-backdrop");
            closeModal(modal);
        });
    });

    // Close on backdrop click
    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
        backdrop.addEventListener("click", (e) => {
            if (e.target === backdrop) {
                closeModal(backdrop);
            }
        });
    });

    // Escape key closes modal
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && activeModal) {
            closeModal(activeModal);
        }
    });

    // 4. Form Double-Submit Protection
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (e) => {
            if (form.dataset.submitting === "true") {
                e.preventDefault();
                return false;
            }
            const submitBtn = form.querySelector("button[type=\"submit\"]");
            if (submitBtn && !form.noValidate && form.checkValidity()) {
                form.dataset.submitting = "true";
                submitBtn.classList.add("btn-loading");
            }
        });
    });

    // 5. Back-Forward Cache (bfcache) Revalidation
    window.addEventListener("pageshow", (event) => {
        if (event.persisted) {
            window.location.reload();
        }
    });
});

