// Hub page: renders the model registry (/models.json) as cards.
import { initI18n } from "/assets/i18n.js";

const i18n = initI18n({
  fr: {
    "page.title": "Crommix AI — Modèles pour le bambara",
    "hub.badge": "Dans votre navigateur, hors ligne après chargement",
    "hub.title": "Des modèles d'IA pour le bambara",
    "hub.lede": "Petits modèles conçus pour tourner sur l'appareil, sans serveur ni envoi de données. Essayez-les ici.",
    "hub.try": "Essayer →",
  },
  en: {
    "page.title": "Crommix AI — Models for Bambara",
    "hub.badge": "In your browser, offline once loaded",
    "hub.title": "AI models for Bambara",
    "hub.lede": "Small models built to run on the device, with no server and no data sent anywhere. Try them here.",
    "hub.try": "Try it →",
  },
});

const grid = document.getElementById("models");
let models = [];

function render() {
  const L = i18n.lang;
  grid.replaceChildren(...models.map((m) => {
    const live = m.status === "live";
    const el = document.createElement(live ? "a" : "div");
    el.className = "card model" + (live ? "" : " soon");
    if (live) el.href = m.path;
    const top = document.createElement("div");
    top.className = "model-top";
    const mod = document.createElement("span");
    mod.className = "mod";
    mod.textContent = m.module;
    const badge = document.createElement("span");
    badge.className = "badge" + (live ? "" : " soon");
    badge.innerHTML = '<span class="dot"></span>';
    badge.append(i18n.t(live ? "status.live" : "status.soon"));
    top.append(mod, badge);
    const h = document.createElement("h2");
    h.textContent = m.name[L] ?? m.name.fr;
    const p = document.createElement("p");
    p.textContent = m.desc[L] ?? m.desc.fr;
    const tags = document.createElement("div");
    tags.className = "tags";
    for (const t of m.tags ?? []) {
      const s = document.createElement("span");
      s.className = "tag";
      s.textContent = t;
      tags.append(s);
    }
    el.append(top, h, p, tags);
    if (live) {
      const go = document.createElement("span");
      go.className = "go";
      go.textContent = i18n.t("hub.try");
      el.append(go);
    }
    return el;
  }));
}

fetch("/models.json").then((r) => r.json()).then((list) => { models = list; render(); })
  .catch(() => { grid.textContent = "models.json ?"; });
i18n.onChange(render);
