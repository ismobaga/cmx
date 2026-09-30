// Tiny FR/EN switcher shared by every page.
// Markup: data-i18n="key" (text), data-i18n-placeholder / -aria-label / -title (attributes),
// and buttons with data-set-lang="fr|en". French is the default.
const KEY = "crommix-ai-lang";

export const COMMON = {
  fr: {
    "brand.sub": "Laboratoire IA",
    "nav.models": "Modèles",
    "nav.github": "Code source",
    "footer.copy": "© Crommix Mali S.A. — Bamako",
    "footer.private": "Les modèles tournent dans votre navigateur : aucun texte n'est envoyé.",
    "status.live": "En ligne",
    "status.soon": "Bientôt",
  },
  en: {
    "brand.sub": "AI Lab",
    "nav.models": "Models",
    "nav.github": "Source code",
    "footer.copy": "© Crommix Mali S.A. — Bamako",
    "footer.private": "Models run in your browser: no text is sent anywhere.",
    "status.live": "Live",
    "status.soon": "Coming soon",
  },
};

export function initI18n(pageDict = { fr: {}, en: {} }) {
  const dict = {
    fr: { ...COMMON.fr, ...pageDict.fr },
    en: { ...COMMON.en, ...pageDict.en },
  };
  const listeners = [];
  let lang = "fr";
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "fr" || saved === "en") lang = saved;
  } catch { /* storage blocked: stay on default */ }

  const t = (key, vars = {}) => {
    let s = dict[lang][key] ?? dict.fr[key] ?? key;
    for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
    return s;
  };

  function apply() {
    document.documentElement.lang = lang;
    for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
    for (const attr of ["placeholder", "aria-label", "title"]) {
      for (const el of document.querySelectorAll(`[data-i18n-${attr}]`)) {
        el.setAttribute(attr, t(el.getAttribute(`data-i18n-${attr}`)));
      }
    }
    for (const b of document.querySelectorAll("[data-set-lang]")) {
      b.setAttribute("aria-pressed", String(b.dataset.setLang === lang));
    }
    // Longer blocks written once per language: <div data-lang-only="fr">…</div>
    for (const el of document.querySelectorAll("[data-lang-only]")) el.hidden = el.dataset.langOnly !== lang;
    if (dict[lang]["page.title"]) document.title = t("page.title");
    listeners.forEach((f) => f(lang));
  }

  for (const b of document.querySelectorAll("[data-set-lang]")) {
    b.addEventListener("click", () => {
      lang = b.dataset.setLang;
      try { localStorage.setItem(KEY, lang); } catch { /* ignore */ }
      apply();
    });
  }
  apply();
  return { t, get lang() { return lang; }, onChange: (f) => listeners.push(f) };
}
