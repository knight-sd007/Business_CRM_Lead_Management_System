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

    // 4. Form Double-Submit Protection (excluding GET filter forms)
    document.querySelectorAll("form:not(.leads-filter-form)").forEach((form) => {
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

    // 6. Leads Filter Form Clean Parameter Submission
    const filterForm = document.querySelector(".leads-filter-form");
    if (filterForm) {
        filterForm.addEventListener("submit", (e) => {
            handleLeadsFilterSubmit(e, filterForm);
        });
    }
});

/**
 * Cleanly serialize and submit Leads Workspace filter form,
 * omitting empty optional fields and default sort parameters from the query string.
 */
function handleLeadsFilterSubmit(e, form) {
    if (e) {
        if (typeof e.preventDefault === "function") e.preventDefault();
        if (typeof e.stopPropagation === "function") e.stopPropagation();
    }
    const filterForm = form || document.querySelector(".leads-filter-form");
    if (!filterForm) return false;

    const formData = new FormData(filterForm);
    const params = new URLSearchParams();

    for (const [key, rawValue] of formData.entries()) {
        const value = typeof rawValue === "string" ? rawValue.trim() : rawValue;
        if (!value) {
            continue;
        }
        // Omit defaults if unchanged to keep URL minimal and clean
        if (key === "sort_by" && value === "created_at") {
            continue;
        }
        if (key === "sort_order" && value === "desc") {
            continue;
        }
        params.append(key, value);
    }

    // If non-default sort_by is specified with default sort_order='desc',
    // include sort_order for explicit sorting clarity
    const sortBy = formData.get("sort_by");
    const sortOrder = formData.get("sort_order");
    if (sortBy && sortBy !== "created_at" && sortOrder && !params.has("sort_order")) {
        params.append("sort_order", sortOrder);
    }

    // Fallback defense: disable empty inputs so native GET serializer will also omit them
    const inputs = filterForm.querySelectorAll("input, select");
    inputs.forEach((input) => {
        const val = input.value ? input.value.trim() : "";
        if (!val) {
            input.disabled = true;
        } else if (input.name === "sort_by" && val === "created_at") {
            input.disabled = true;
        } else if (input.name === "sort_order" && val === "desc" && (!sortBy || sortBy === "created_at")) {
            input.disabled = true;
        }
    });

    const queryString = params.toString();
    const targetUrl = queryString ? `/leads?${queryString}` : "/leads";

    // Re-enable inputs after a short tick in case the user navigates back
    setTimeout(() => {
        inputs.forEach((input) => {
            input.disabled = false;
        });
    }, 100);

    window.location.assign(targetUrl);
    return false;
}

window.handleLeadsFilterSubmit = handleLeadsFilterSubmit;

