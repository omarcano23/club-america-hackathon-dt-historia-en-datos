# -*- coding: utf-8 -*-
"""
08_build_v3_experience.py
Club América | El vuelo del bicampeón

Lee report/web_data.json y genera report/index.html.
No recalcula las métricas.
"""

from __future__ import annotations

import json
from pathlib import Path
from html import escape


# ------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
INPUT_FILE = REPORT_DIR / "web_data.json"
OUTPUT_FILE = REPORT_DIR / "index.html"


# ------------------------------------------------------------
# PLANTILLA HTML
# Los datos se insertan desde web_data.json.
# ------------------------------------------------------------

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#5b0a18">
<meta name="description" content="Una historia de datos sobre la identidad de juego del Club América de André Jardine.">
<title>El vuelo del bicampeón | Club América</title>

<style>
:root {
  --wine: #5b0a18;
  --wine-dark: #320710;
  --wine-soft: #8e2337;
  --cream: #f7f3ed;
  --paper: #fffdf9;
  --ink: #211b1c;
  --muted: #71686a;
  --line: #e7ded8;
  --gold: #c6a15b;
  --green: #315e4b;
  --shadow: 0 18px 55px rgba(42, 12, 18, .08);
  --radius: 22px;
}

* { box-sizing: border-box; }

html {
  scroll-behavior: smooth;
  scroll-padding-top: 100px;
}

body {
  margin: 0;
  background: var(--cream);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system,
    BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.6;
}

button, a { font: inherit; }

button:focus-visible, a:focus-visible, summary:focus-visible {
  outline: 3px solid var(--gold);
  outline-offset: 4px;
}

a { color: inherit; }

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(50, 7, 16, .97);
  color: white;
  border-bottom: 1px solid rgba(255,255,255,.12);
  backdrop-filter: blur(12px);
}

.topbar-inner {
  max-width: 1180px;
  margin: auto;
  padding: 13px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  font-size: .76rem;
  letter-spacing: .12em;
  font-weight: 800;
  text-transform: uppercase;
}

.brand-mark {
  display: grid;
  place-items: center;
  flex: 0 0 38px;
  height: 38px;
  border: 1px solid rgba(255,255,255,.42);
  border-radius: 50%;
  color: var(--gold);
  font-family: Georgia, serif;
  font-size: 1rem;
}

.topbar-note {
  color: rgba(255,255,255,.72);
  font-size: .76rem;
  text-align: right;
}

.hero {
  position: relative;
  overflow: hidden;
  color: white;
  background:
    radial-gradient(ellipse at 88% 8%, rgba(198,161,91,.18), transparent 34%),
    radial-gradient(ellipse at 8% 90%, rgba(142,35,55,.6), transparent 45%),
    linear-gradient(130deg, var(--wine-dark), var(--wine) 68%, #71152a);
}

.hero::after {
  content: "";
  position: absolute;
  width: 390px;
  height: 390px;
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 50%;
  right: -150px;
  bottom: -220px;
  box-shadow: 0 0 0 38px rgba(255,255,255,.025),
              0 0 0 78px rgba(255,255,255,.02);
  pointer-events: none;
}

.hero-inner {
  max-width: 1180px;
  margin: auto;
  padding: 82px 24px 74px;
  position: relative;
  z-index: 1;
}

.eyebrow {
  margin: 0 0 18px;
  color: var(--gold);
  text-transform: uppercase;
  font-size: .76rem;
  font-weight: 800;
  letter-spacing: .18em;
}

.hero h1 {
  max-width: 900px;
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2.8rem, 7vw, 6.3rem);
  line-height: .98;
  font-weight: 500;
  letter-spacing: -.045em;
}

.hero-copy {
  max-width: 690px;
  margin: 28px 0 0;
  color: rgba(255,255,255,.84);
  font-size: clamp(1rem, 2vw, 1.16rem);
}

.hero-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 42px;
  padding-top: 22px;
  border-top: 1px solid rgba(255,255,255,.2);
}

.hero-mantra {
  color: white;
  font-family: Georgia, serif;
  font-size: 1.2rem;
  font-style: italic;
}

.hero-meta {
  color: rgba(255,255,255,.72);
  font-size: .85rem;
}

main {
  max-width: 1180px;
  margin: auto;
  padding: 0 24px 70px;
}

.chapter-nav-wrap {
  position: sticky;
  top: 64px;
  z-index: 15;
  margin: 0 -24px;
  padding: 14px 24px;
  background: rgba(247,243,237,.94);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}

.chapter-nav {
  max-width: 1132px;
  margin: auto;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.tab {
  flex: 0 0 auto;
  border: 1px solid transparent;
  background: transparent;
  color: var(--muted);
  border-radius: 999px;
  padding: 10px 15px;
  cursor: pointer;
  font-size: .87rem;
  font-weight: 750;
  transition: background .2s ease, color .2s ease, border .2s ease;
}

.tab:hover {
  color: var(--wine);
  border-color: var(--line);
}

.tab[aria-selected="true"] {
  color: white;
  background: var(--wine);
  border-color: var(--wine);
}

.intro-strip {
  display: grid;
  grid-template-columns: 1.15fr .85fr;
  gap: 26px;
  padding: 32px 0 38px;
  border-bottom: 1px solid var(--line);
}

.intro-strip h2 {
  margin: 0 0 8px;
  font-family: Georgia, serif;
  font-weight: 500;
  font-size: 1.65rem;
}

.intro-strip p {
  margin: 0;
  color: var(--muted);
}

.coverage {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  align-self: center;
}

.coverage-item {
  background: rgba(255,255,255,.64);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
}

.coverage-item strong {
  display: block;
  color: var(--wine);
  font-size: 1.45rem;
  line-height: 1.2;
}

.coverage-item span {
  display: block;
  color: var(--muted);
  margin-top: 5px;
  font-size: .75rem;
}

.chapter {
  padding: 56px 0 42px;
  border-bottom: 1px solid var(--line);
  animation: reveal .35s ease both;
}

.chapter[hidden] { display: none; }

@keyframes reveal {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chapter-kicker {
  color: var(--wine-soft);
  font-size: .76rem;
  font-weight: 850;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.chapter h2 {
  max-width: 820px;
  margin: 10px 0 8px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2rem, 4vw, 3.45rem);
  line-height: 1.08;
  letter-spacing: -.03em;
  font-weight: 500;
}

.chapter-subtitle {
  max-width: 750px;
  margin: 0;
  color: var(--wine-soft);
  font-size: 1.08rem;
  font-weight: 650;
}

.chapter-intro {
  max-width: 800px;
  margin: 20px 0 30px;
  color: var(--muted);
  font-size: 1.02rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 26px 0 34px;
}

.metric-card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 21px 19px;
  box-shadow: 0 6px 24px rgba(42,12,18,.025);
  min-width: 0;
}

.metric-label {
  color: var(--muted);
  font-size: .82rem;
  font-weight: 750;
  min-height: 2.4em;
}

.metric-value {
  display: block;
  margin: 12px 0 10px;
  color: var(--wine);
  font-family: Georgia, serif;
  font-size: clamp(1.8rem, 3vw, 2.65rem);
  line-height: 1.04;
  letter-spacing: -.035em;
  overflow-wrap: anywhere;
}

.metric-description {
  color: var(--muted);
  font-size: .84rem;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, .85fr);
  gap: 18px;
  align-items: start;
}

.panel {
  min-width: 0;
  padding: 25px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.panel h3 {
  margin: 0 0 7px;
  font-size: 1.04rem;
}

.panel-lead {
  margin: 0 0 22px;
  color: var(--muted);
  font-size: .86rem;
}

.highlight {
  padding: 17px 0;
  border-top: 1px solid var(--line);
}

.highlight:first-of-type {
  border-top: 0;
  padding-top: 0;
}

.highlight h4 {
  margin: 0 0 6px;
  font-size: .96rem;
}

.highlight p {
  margin: 0;
  color: var(--muted);
  font-size: .9rem;
}

.bar-row { margin: 22px 0; }

.bar-label-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: .86rem;
  font-weight: 750;
  margin-bottom: 8px;
}

.bar-track {
  height: 13px;
  background: #eee7e2;
  border-radius: 99px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, var(--wine), var(--wine-soft));
  border-radius: inherit;
  transition: width .65s ease;
}

.table-wrap { overflow-x: auto; }

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: .88rem;
}

.data-table th,
.data-table td {
  text-align: left;
  vertical-align: top;
  padding: 13px 10px;
  border-bottom: 1px solid var(--line);
}

.data-table th {
  color: var(--muted);
  font-size: .76rem;
  text-transform: uppercase;
  letter-spacing: .06em;
}

.data-table td.numeric {
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.score-card {
  padding: 18px 0;
  border-top: 1px solid var(--line);
}

.score-card:first-of-type { border-top: 0; }

.score-card h4 { margin: 0 0 12px; }

.score-lines {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.score-line {
  background: #f7f1eb;
  padding: 12px;
  border-radius: 12px;
}

.score-line span {
  display: block;
  color: var(--muted);
  font-size: .74rem;
  margin-bottom: 4px;
}

.score-line strong {
  color: var(--wine);
  font-size: .95rem;
}

.score-note {
  color: var(--muted);
  font-size: .84rem;
  margin: 10px 0 0;
}

.ci-visual {
  margin-top: 22px;
  padding: 17px;
  background: #f7f1eb;
  border-radius: 14px;
}

.ci-visual p {
  margin: 0 0 12px;
  font-size: .85rem;
  font-weight: 750;
}

.ci-scale {
  position: relative;
  height: 44px;
  margin: 12px 8px 2px;
}

.ci-axis {
  position: absolute;
  left: 0;
  right: 0;
  top: 20px;
  height: 2px;
  background: #d8ccc4;
}

.ci-zero {
  position: absolute;
  left: 50%;
  top: 9px;
  height: 24px;
  width: 2px;
  background: var(--ink);
}

.ci-range {
  position: absolute;
  top: 16px;
  height: 10px;
  border-radius: 10px;
  background: var(--wine-soft);
}

.ci-estimate {
  position: absolute;
  top: 12px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: var(--gold);
  border: 2px solid white;
  box-shadow: 0 0 0 1px var(--gold);
  transform: translateX(-50%);
}

.ci-legend {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--muted);
  font-size: .72rem;
}

.method {
  margin-top: 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255,255,255,.55);
}

.method summary {
  cursor: pointer;
  padding: 15px 18px;
  font-weight: 800;
  color: var(--wine);
}

.method-content {
  padding: 0 20px 18px;
  color: var(--muted);
  font-size: .87rem;
}

.method-content ul {
  padding-left: 20px;
  margin: 8px 0;
}

.method-content li { margin: 8px 0; }

.chapter-controls {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 28px;
}

.nav-button {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 11px 17px;
  background: var(--paper);
  color: var(--wine);
  font-weight: 800;
  cursor: pointer;
}

.nav-button.primary {
  background: var(--wine);
  color: white;
  border-color: var(--wine);
}

.nav-button:disabled {
  opacity: .35;
  cursor: not-allowed;
}

.framework {
  padding: 54px 0 20px;
}

.framework h2 {
  margin: 0 0 8px;
  font-family: Georgia, serif;
  font-weight: 500;
  font-size: 2.2rem;
}

.framework > p {
  max-width: 760px;
  color: var(--muted);
}

.glossary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 25px 0;
}

.glossary-card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
}

.glossary-card h3 {
  margin: 0 0 7px;
  color: var(--wine);
  font-size: .95rem;
}

.glossary-card p {
  margin: 0;
  color: var(--muted);
  font-size: .84rem;
}

.limits {
  padding: 22px;
  background: #efe7df;
  border-radius: 18px;
}

.limits h3 { margin-top: 0; }

.limits li {
  margin: 8px 0;
  color: #5c5150;
  font-size: .88rem;
}

.footer {
  background: var(--wine-dark);
  color: rgba(255,255,255,.78);
  padding: 28px 24px;
  font-size: .8rem;
}

.footer-inner {
  max-width: 1132px;
  margin: auto;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.footer strong {
  color: white;
  letter-spacing: .06em;
}

.small-note {
  color: var(--muted);
  font-size: .78rem;
}

@media (max-width: 900px) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .content-grid { grid-template-columns: 1fr; }
  .intro-strip { grid-template-columns: 1fr; }
  .glossary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .topbar-inner { padding: 10px 16px; }
  .brand { font-size: .65rem; letter-spacing: .07em; }
  .topbar-note { display: none; }
  .hero-inner { padding: 58px 19px 48px; }
  main { padding-left: 18px; padding-right: 18px; }
  .chapter-nav-wrap { margin: 0 -18px; padding: 11px 18px; top: 58px; }
  .tab { padding: 9px 12px; font-size: .8rem; }
  .coverage { grid-template-columns: 1fr; }
  .coverage-item { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .coverage-item span { margin-top: 0; text-align: right; }
  .metric-grid { gap: 9px; }
  .metric-card { padding: 16px 13px; border-radius: 16px; }
  .metric-label { font-size: .75rem; }
  .metric-value { font-size: 1.8rem; }
  .metric-description { font-size: .78rem; }
  .panel { padding: 18px; }
  .chapter { padding-top: 40px; }
  .glossary-grid { grid-template-columns: 1fr; }
  .score-lines { grid-template-columns: 1fr; }
  .chapter-controls { align-items: center; }
  .nav-button { padding: 10px 12px; font-size: .8rem; }
}
</style>
</head>

<body>
<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">CA</span>
      <span>CLUB AMÉRICA · LAS ÁGUILAS DE JARDINE</span>
    </div>
    <div class="topbar-note">Historia en datos · 2023-24 y 2024-25</div>
  </div>
</header>

<section class="hero">
  <div class="hero-inner">
    <p class="eyebrow">Una forma de jugar. Una historia que contar.</p>
    <h1>EL VUELO DEL BICAMPEÓN</h1>
    <p class="hero-copy">
      Algunos equipos que ganan partidos. Otros dejan un legado.
      Esta es una mirada a los detalles que marcaron el camino de las
      Águilas de André Jardine (2023-24 y 2024-25).
    </p>
    <div class="hero-bottom">
      <div class="hero-mantra">Cinco capítulos. Una filosofía.</div>
      <div class="hero-meta" id="hero-meta">Club América · Análisis de partidos</div>
    </div>
  </div>
</section>

<main>
  <div class="chapter-nav-wrap">
    <nav class="chapter-nav" id="chapter-nav" aria-label="Capítulos del análisis" role="tablist">
      <button class="tab" id="tab-identidad" role="tab" aria-controls="chapter-identidad" aria-selected="true" tabindex="0" data-index="0">La identidad</button>
      <button class="tab" id="tab-progresion" role="tab" aria-controls="chapter-progresion" aria-selected="false" tabindex="-1" data-index="1">La progresión</button>
      <button class="tab" id="tab-recuperacion" role="tab" aria-controls="chapter-recuperacion" aria-selected="false" tabindex="-1" data-index="2">La recuperación</button>
      <button class="tab" id="tab-marcador" role="tab" aria-controls="chapter-marcador" aria-selected="false" tabindex="-1" data-index="3">El marcador</button>
      <button class="tab" id="tab-balon-parado" role="tab" aria-controls="chapter-balon-parado" aria-selected="false" tabindex="-1" data-index="4">El balón parado</button>
    </nav>
  </div>

  <section class="intro-strip" aria-label="Cobertura del análisis">
    <div>
      <h2>Una historia construida desde los datos</h2>
      <p>
        Cinco miradas al juego del América: el territorio que ocupa, las rutas
        que utiliza para avanzar, la recuperación, el marcador y las jugadas
        a balón parado. Cada resultado se acompaña de su contexto y sus límites.
      </p>
    </div>
    <div class="coverage" id="coverage"></div>
  </section>

  <div id="chapters"></div>

  <section class="framework" id="framework">
    <h2>Cómo leer esta historia</h2>
    <p>
      Las métricas ayudan a describir patrones del juego, pero no sustituyen
      el contexto de cada partido. Estas definiciones aclaran qué representa
      cada indicador y qué queda fuera del análisis.
    </p>
    <div class="glossary-grid" id="glossary"></div>
    <div class="limits" id="limits"></div>
  </section>
</main>

<footer class="footer">
  <div class="footer-inner">
    <div><strong>CLUB AMÉRICA</strong><br>El vuelo del bicampeón</div>
    <div>Una narrativa analítica basada en los datos reportados del proyecto.</div>
  </div>
</footer>

<script>
"use strict";

const DATA = __DATA_JSON__;

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function safeText(value) {
  return String(value ?? "");
}

function escapeHTML(value) {
  return safeText(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderCoverage() {
  const meta = DATA.meta;
  const target = $("#coverage");
  const entries = meta.competition_breakdown || [];

  target.innerHTML = entries.map(item => `
    <div class="coverage-item">
      <strong>${escapeHTML(item.matches)}</strong>
      <span>${escapeHTML(item.label)}</span>
    </div>
  `).join("");

  $("#hero-meta").textContent =
    `${meta.team} · ${meta.matches} partidos documentados`;
}

function renderMetrics(metrics = []) {
  if (!metrics.length) return "";

  return `
    <div class="metric-grid">
      ${metrics.map(metric => `
        <article class="metric-card">
          <div class="metric-label">${escapeHTML(metric.label)}</div>
          <strong class="metric-value">${escapeHTML(metric.value)}</strong>
          <div class="metric-description">${escapeHTML(metric.description)}</div>
        </article>
      `).join("")}
    </div>
  `;
}

function renderHighlights(highlights = []) {
  if (!highlights.length) return "";

  return `
    <section class="panel">
      <h3>Lo que nos dicen los datos</h3>
      <p class="panel-lead">La lectura táctica, con sus matices.</p>
      ${highlights.map(item => `
        <article class="highlight">
          <h4>${escapeHTML(item.title)}</h4>
          <p>${escapeHTML(item.text)}</p>
        </article>
      `).join("")}
    </section>
  `;
}

function renderComparison(comparison) {
  if (!comparison || !Array.isArray(comparison.items)) return "";

  const max = Math.max(
    1,
    ...comparison.items.map(item => Number(item.value) || 0)
  );

  return `
    <section class="panel">
      <h3>${escapeHTML(comparison.title)}</h3>
      <p class="panel-lead">
        Porcentaje de progresión reportado en cada grupo.
      </p>
      ${comparison.items.map(item => {
        const value = Number(item.value) || 0;
        const width = Math.max(0, Math.min(100, value / max * 100));
        return `
          <div class="bar-row">
            <div class="bar-label-line">
              <span>${escapeHTML(item.label)}</span>
              <span>${value.toFixed(2)}${escapeHTML(comparison.unit || "%")}</span>
            </div>
            <div class="bar-track" role="img"
              aria-label="${escapeHTML(item.label)}: ${value.toFixed(2)} por ciento">
              <div class="bar-fill" style="width:${width}%"></div>
            </div>
          </div>
        `;
      }).join("")}
      <p class="small-note">
        La comparación describe una asociación observada, no una relación causal.
      </p>
    </section>
  `;
}

function renderSetPieces(items = []) {
  if (!items.length) return "";

  return `
    <section class="panel">
      <h3>Qué ocurre después de cada reinicio</h3>
      <p class="panel-lead">
        Temporada regular · remates registrados y xG asociado.
      </p>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Reinicio</th>
              <th style="text-align:right">Remates</th>
              <th style="text-align:right">xG</th>
              <th style="text-align:right">xG/remate</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(item => `
              <tr>
                <td>${escapeHTML(item.label)}</td>
                <td class="numeric">${Number(item.shots).toLocaleString("es-MX")}</td>
                <td class="numeric">${Number(item.xg).toFixed(2)}</td>
                <td class="numeric">${Number(item.xg_per_shot).toFixed(4)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <p class="small-note">
        xG por remate describe la calidad media de los remates registrados.
        No es una tasa de goles por reinicio ejecutado.
      </p>
    </section>
  `;
}

function renderScoreExceptions(items = []) {
  if (!items.length) return "";

  return `
    <section class="panel">
      <h3>Dos marcadores que no coinciden</h3>
      <p class="panel-lead">
        Se conserva el marcador de referencia y se documenta la reconstrucción
        a partir de eventos.
      </p>
      ${items.map(item => `
        <article class="score-card">
          <h4>${escapeHTML(item.match)}</h4>
          <div class="score-lines">
            <div class="score-line">
              <span>Marcador de referencia</span>
              <strong>${escapeHTML(item.official)}</strong>
            </div>
            <div class="score-line">
              <span>Reconstrucción por eventos</span>
              <strong>${escapeHTML(item.events)}</strong>
            </div>
          </div>
          <p class="score-note">${escapeHTML(item.note)}</p>
        </article>
      `).join("")}
      <p class="small-note">
        La causa de estas diferencias no está confirmada por la información
        documentada aquí.
      </p>
    </section>
  `;
}

function renderUncertainty(uncertainty) {
  if (!uncertainty) return "";

  /*
   * El eje es una representación visual centrada en cero.
   * Los límites se muestran según el intervalo reportado.
   */
  const lower = Number(uncertainty.lower);
  const upper = Number(uncertainty.upper);
  const estimate = Number(uncertainty.estimate);
  const min = Math.min(-15, lower);
  const max = Math.max(15, upper);
  const span = max - min;

  const position = value => ((value - min) / span) * 100;
  const left = position(lower);
  const right = position(upper);
  const point = position(estimate);
  const zero = position(0);

  return `
    <div class="ci-visual">
      <p>${escapeHTML(uncertainty.label)}</p>
      <strong>${escapeHTML(uncertainty.value)}</strong>
      <div class="ci-scale" role="img"
        aria-label="Intervalo de confianza desde ${lower} hasta ${upper} puntos porcentuales, estimación ${estimate}">
        <div class="ci-axis"></div>
        <div class="ci-zero" style="left:${zero}%"></div>
        <div class="ci-range" style="left:${left}%;width:${Math.max(0, right-left)}%"></div>
        <div class="ci-estimate" style="left:${point}%"></div>
      </div>
      <div class="ci-legend">
        <span>${min} pp</span>
        <span>0</span>
        <span>+${max} pp</span>
      </div>
      <p class="small-note">
        Como el intervalo incluye el cero, la diferencia observada no es
        concluyente con el método reportado.
      </p>
    </div>
  `;
}

function renderMethodology(items = []) {
  if (!items.length) return "";

  return `
    <details class="method">
      <summary>Metodología y alcance de este capítulo</summary>
      <div class="method-content">
        <ul>
          ${items.map(item => `<li>${escapeHTML(item)}</li>`).join("")}
        </ul>
      </div>
    </details>
  `;
}

function renderChapter(chapter, index) {
  const comparison = renderComparison(chapter.comparison);
  const setPieces = renderSetPieces(chapter.set_pieces);
  const exceptions = renderScoreExceptions(chapter.score_exceptions);
  const uncertainty = renderUncertainty(chapter.uncertainty);

  let leftPanel = "";
  let rightPanel = renderHighlights(chapter.highlights);

  if (comparison) {
    leftPanel = comparison;
  } else if (setPieces) {
    leftPanel = setPieces;
  } else if (exceptions) {
    leftPanel = exceptions;
  } else if (uncertainty) {
    leftPanel = `
      <section class="panel">
        <h3>La diferencia y su incertidumbre</h3>
        <p class="panel-lead">
          La estimación puntual no cuenta toda la historia.
        </p>
        ${uncertainty}
      </section>
    `;
  } else {
    leftPanel = `
      <section class="panel">
        <h3>Dos indicadores complementarios</h3>
        <p class="panel-lead">
          Territorio y presión ayudan a describir aspectos diferentes del juego.
        </p>
        ${chapter.metrics.slice(0, 2).map(metric => `
          <article class="highlight">
            <h4>${escapeHTML(metric.label)} · ${escapeHTML(metric.value)}</h4>
            <p>${escapeHTML(metric.description)}</p>
          </article>
        `).join("")}
      </section>
    `;
  }

  return `
    <section class="chapter" id="chapter-${escapeHTML(chapter.id)}"
      role="tabpanel" aria-labelledby="tab-${escapeHTML(chapter.id)}"
      data-chapter-index="${index}" ${index === 0 ? "" : "hidden"}>
      <div class="chapter-kicker">Capítulo ${escapeHTML(chapter.number)}</div>
      <h2>${escapeHTML(chapter.title)}</h2>
      <p class="chapter-subtitle">${escapeHTML(chapter.subtitle)}</p>
      <p class="chapter-intro">${escapeHTML(chapter.intro)}</p>

      ${renderMetrics(chapter.metrics)}

      <div class="content-grid">
        ${leftPanel}
        ${rightPanel}
      </div>

      ${renderMethodology(chapter.methodology)}

      <div class="chapter-controls">
        <button class="nav-button" type="button" data-prev="${index}"
          ${index === 0 ? "disabled" : ""}>
          ← Capítulo anterior
        </button>
        <button class="nav-button primary" type="button" data-next="${index}"
          ${index === DATA.chapters.length - 1 ? "disabled" : ""}>
          Siguiente capítulo →
        </button>
      </div>
    </section>
  `;
}

function renderGlossary() {
  const framework = DATA.framework;
  $("#glossary").innerHTML = framework.items.map(item => `
    <article class="glossary-card">
      <h3>${escapeHTML(item.term)}</h3>
      <p>${escapeHTML(item.definition)}</p>
    </article>
  `).join("");

  $("#limits").innerHTML = `
    <h3>Qué conviene tener presente</h3>
    <ul>
      ${framework.limits.map(item => `<li>${escapeHTML(item)}</li>`).join("")}
    </ul>
  `;
}

function setupNavigation() {
  const tabs = $$(".tab");
  const panels = $$(".chapter");

  function activate(index, moveFocus = false) {
    const safeIndex = Math.max(0, Math.min(index, tabs.length - 1));

    tabs.forEach((tab, i) => {
      const active = i === safeIndex;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });

    panels.forEach((panel, i) => {
      panel.hidden = i !== safeIndex;
    });

    if (moveFocus) tabs[safeIndex].focus();

    /*
     * Lleva el título del capítulo a la vista sin saltos bruscos
     * en dispositivos pequeños.
     */
    const currentPanel = panels[safeIndex];
    currentPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(index));

    tab.addEventListener("keydown", event => {
      let next = index;

      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;

      event.preventDefault();
      activate(next, true);
    });
  });

  $$("[data-prev]").forEach(button => {
    button.addEventListener("click", () => {
      activate(Number(button.dataset.prev) - 1);
    });
  });

  $$("[data-next]").forEach(button => {
    button.addEventListener("click", () => {
      activate(Number(button.dataset.next) + 1);
    });
  });
}

function validateData() {
  if (!DATA || !Array.isArray(DATA.chapters) || DATA.chapters.length !== 5) {
    throw new Error("web_data.json debe contener cinco capítulos.");
  }

  const expectedIds = [
    "identidad",
    "progresion",
    "recuperacion",
    "marcador",
    "balon-parado"
  ];

  const actualIds = DATA.chapters.map(chapter => chapter.id);

  if (JSON.stringify(expectedIds) !== JSON.stringify(actualIds)) {
    throw new Error("Los identificadores u orden de capítulos no coinciden.");
  }
}

function main() {
  validateData();
  renderCoverage();

  $("#chapters").innerHTML = DATA.chapters
    .map((chapter, index) => renderChapter(chapter, index))
    .join("");

  renderGlossary();
  setupNavigation();
}

main();
</script>
</body>
</html>
'''


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No existe {INPUT_FILE}. Ejecuta primero "
            "'python scripts/07_export_data_for_web.py'."
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data.get("chapters"), list) or len(data["chapters"]) != 5:
        raise ValueError(
            "web_data.json no contiene los cinco capítulos esperados."
        )

    # JSON seguro para incrustar dentro del bloque JavaScript.
    # Evita que una cadena de datos pueda cerrar la etiqueta script.
    embedded_json = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    embedded_json = (
        embedded_json
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    html = HTML_TEMPLATE.replace("__DATA_JSON__", embedded_json)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    print(f"Experiencia web generada: {OUTPUT_FILE}")
    print(f"Capítulos: {len(data['chapters'])}")
    print("Archivo de datos utilizado: report/web_data.json")


if __name__ == "__main__":
    main()