const html = document.documentElement;
const themeToggle = document.getElementById("theme-toggle");
const iconMoon = document.getElementById("icon-moon");
const iconSun = document.getElementById("icon-sun");
const repoCopyButton = document.querySelector("[data-copy-target]");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function setTheme(isDark) {
  html.classList.toggle("dark", isDark);
  if (iconMoon) {
    iconMoon.classList.toggle("hidden", !isDark);
  }
  if (iconSun) {
    iconSun.classList.toggle("hidden", isDark);
  }
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", String(isDark));
  }
}

function getPreferredTheme() {
  const persisted = localStorage.getItem("theme");
  if (persisted === "light") {
    return false;
  }
  if (persisted === "dark") {
    return true;
  }
  return !window.matchMedia("(prefers-color-scheme: light)").matches;
}

function setupThemeToggle() {
  if (!themeToggle) {
    return;
  }

  let isDark = getPreferredTheme();
  setTheme(isDark);

  themeToggle.addEventListener("click", () => {
    isDark = !isDark;
    setTheme(isDark);
    localStorage.setItem("theme", isDark ? "dark" : "light");
  });
}

async function copyText(button) {
  const target = document.querySelector(button.dataset.copyTarget || "");
  const status = document.querySelector("[data-copy-status]");
  const defaultIcon = button.querySelector(".copy-icon-default");
  const successIcon = button.querySelector(".copy-icon-success");

  if (!target) {
    return;
  }

  try {
    await navigator.clipboard.writeText(target.textContent.trim());
    status.textContent = "Repository URL copied.";
    defaultIcon.classList.add("hidden");
    successIcon.classList.remove("hidden");
    window.setTimeout(() => {
      defaultIcon.classList.remove("hidden");
      successIcon.classList.add("hidden");
      status.textContent = "Copy the URL or use one-click install.";
    }, 2000);
  } catch (error) {
    status.textContent = "Clipboard access failed. Copy the URL manually.";
  }
}

function setupCopyButton() {
  if (!repoCopyButton) {
    return;
  }
  repoCopyButton.addEventListener("click", () => {
    copyText(repoCopyButton);
  });
}

function setupActiveNavigation() {
  const navLinks = document.querySelectorAll("[data-nav-link]");
  const sections = document.querySelectorAll("section[id]");

  if (!navLinks.length || !sections.length || reducedMotion.matches) {
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }
      navLinks.forEach((link) => {
        const active = link.getAttribute("href") === `#${entry.target.id}`;
        link.classList.toggle("is-active", active);
        if (active) {
          link.setAttribute("aria-current", "true");
        } else {
          link.removeAttribute("aria-current");
        }
      });
    });
  }, { threshold: 0.45 });

  sections.forEach((section) => observer.observe(section));
}

function setupIconFallbacks() {
  const appIcons = document.querySelectorAll(".app-icon-image[data-icon-fallback]");

  appIcons.forEach((icon) => {
    icon.addEventListener("error", () => {
      const fallback = document.createElement("span");
      fallback.className = "app-icon-fallback";
      fallback.setAttribute("aria-hidden", "true");
      fallback.textContent = icon.dataset.iconFallback || "📦";
      icon.replaceWith(fallback);
    }, { once: true });
  });
}

setupThemeToggle();
setupCopyButton();
setupActiveNavigation();
setupIconFallbacks();
