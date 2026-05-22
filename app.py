import logging
import base64
import os
import sys
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from pyngrok import ngrok
from pyngrok.conf import PyngrokConfig
from pyngrok.exception import PyngrokError


load_dotenv(encoding="utf-8-sig")

PORT = 3000
WEBHOOK_PATH = "/webhook"
ZAPI_BASE_URL = "https://api.z-api.io"
PROJECT_DIR = Path(__file__).resolve().parent
LOCAL_NGROK_PATH = PROJECT_DIR / "ngrok.exe"
RECEIVED_EVENTS: deque[dict[str, Any]] = deque(maxlen=50)
AGENDA_STATE: dict[str, dict[str, Any]] = {}
TERMS_STATE: dict[str, dict[str, Any]] = {}
LOCATION_LINKS: dict[str, dict[str, Any]] = {}
DEFAULT_PUBLIC_BASE_URL = "https://testezapi.77indicadores.com.br"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", DEFAULT_PUBLIC_BASE_URL).strip().rstrip("/")
TERMS_PDF_PATH = PROJECT_DIR / "termo_aceite_ficticio.pdf"
TERMS_ACCEPTANCE_TEXT = "li e aceito os termos"
TERMS_REJECTION_TEXT = "não aceito os termos"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


CHAT_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nova Guarda Chat</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: #10251a;
      font-family: Arial, Helvetica, sans-serif;
      background: #eaf4ee;
    }
    .shell {
      width: min(1120px, calc(100vw - 28px));
      margin: 18px auto;
      border: 1px solid #7f8da6;
      background: #fff;
      box-shadow: 6px 6px 0 rgba(19, 32, 51, .16);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 14px;
      color: #fff;
      background: linear-gradient(180deg, #23845a, #145a3b);
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .brand-logo {
      width: 42px;
      height: 42px;
      border-radius: 4px;
      background: #fff;
      object-fit: contain;
      padding: 4px;
      flex: 0 0 auto;
    }
    h1 { margin: 0; font-size: 18px; letter-spacing: 0; }
    .status { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #47d16c; }
    main { display: grid; grid-template-columns: minmax(320px, 420px) 1fr; min-height: calc(100vh - 100px); }
    .composer, .events { padding: 16px; }
    .composer { border-right: 1px solid #b8c4d8; background: #f5f7fb; }
    .field { display: grid; gap: 6px; margin-bottom: 12px; }
    .grid-two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    label { font-size: 13px; font-weight: 700; color: #344054; }
    input, textarea {
      width: 100%;
      border: 1px solid #98a6bd;
      border-radius: 4px;
      padding: 10px;
      color: #10251a;
      background: #fff;
      font: inherit;
    }
    textarea { min-height: 150px; resize: vertical; line-height: 1.4; }
    button {
      width: 100%;
      border: 1px solid #0f4c33;
      border-radius: 4px;
      padding: 11px 14px;
      color: #fff;
      background: linear-gradient(180deg, #2f9d6a, #17623f);
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled { cursor: wait; opacity: .68; }
    .notice {
      margin-top: 12px;
      min-height: 42px;
      padding: 10px;
      border: 1px solid #b8c4d8;
      border-radius: 4px;
      background: #fff;
      color: #667085;
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .notice.ok { border-color: #9bd5bd; color: #1f8a5b; background: #f0fbf6; }
    .notice.error { border-color: #f0a6a0; color: #b42318; background: #fff4f2; }
    .status-card {
      margin-bottom: 12px;
      border: 1px solid #b8c4d8;
      border-radius: 6px;
      background: #fff;
      padding: 10px;
    }
    .status-card strong { display: block; margin-bottom: 4px; font-size: 13px; }
    .status-card span { color: #17623f; font-weight: 700; }
    .mode-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }
    .mode-row input { position: absolute; opacity: 0; pointer-events: none; }
    .mode-row span {
      display: block;
      border: 1px solid #98a6bd;
      border-radius: 4px;
      padding: 9px 8px;
      background: #fff;
      color: #344054;
      font-size: 13px;
      font-weight: 700;
      text-align: center;
      cursor: pointer;
    }
    .mode-row input:checked + span {
      border-color: #17623f;
      color: #fff;
      background: #23845a;
    }
    .toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
    .toolbar h2 { margin: 0; font-size: 16px; }
    .small-button { width: auto; padding: 7px 10px; font-size: 12px; background: #fff; color: #17623f; border-color: #b8c4d8; }
    .timeline { display: grid; gap: 10px; max-height: calc(100vh - 170px); overflow: auto; padding-right: 4px; align-content: start; }
    .event { max-width: 88%; border: 1px solid #b8c4d8; border-radius: 6px; background: #fff8df; overflow: hidden; }
    .event.received { justify-self: start; }
    .event.system { justify-self: center; max-width: 100%; background: #f7f9fc; }
    .event.sent { justify-self: end; background: #e6f6ed; }
    .event.auto { justify-self: end; background: #edf7ff; }
    .event-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 10px;
      color: #344054;
      background: #edf2f9;
      border-bottom: 1px solid #b8c4d8;
      font-size: 12px;
      font-weight: 700;
    }
    pre { margin: 0; padding: 10px; white-space: pre-wrap; overflow-wrap: anywhere; font: 12px/1.45 Consolas, "Courier New", monospace; }
    .message-text { padding: 10px; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; }
    .event-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 0 10px 10px;
    }
    .action-button {
      width: auto;
      padding: 6px 9px;
      border-color: #b8c4d8;
      background: #fff;
      color: #17623f;
      font-size: 12px;
    }
    .decision {
      display: inline-block;
      margin: 0 10px 10px;
      padding: 5px 8px;
      border-radius: 4px;
      background: #fff;
      border: 1px solid #b8c4d8;
      color: #17623f;
      font-size: 12px;
      font-weight: 700;
    }
    .map-link {
      display: inline-block;
      margin: 0 10px 10px;
      color: #17623f;
      font-size: 12px;
      font-weight: 700;
    }
    details summary { cursor: pointer; padding: 0 10px 10px; color: #667085; font-size: 12px; }
    .empty { padding: 28px 12px; color: #667085; text-align: center; border: 1px dashed #b8c4d8; background: #fff; }
    @media (max-width: 820px) {
      main { grid-template-columns: 1fr; }
      .composer { border-right: 0; border-bottom: 1px solid #b8c4d8; }
      header { align-items: flex-start; flex-direction: column; }
      .brand-logo { width: 38px; height: 38px; }
      .timeline { max-height: none; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand">
        <img class="brand-logo" src="/favicon/GuardaNova.svg" alt="Logo Guarda Nova Santos">
        <h1>Nova Guarda Chat</h1>
      </div>
      <div class="status"><span class="dot"></span> online na porta {{ port }}</div>
    </header>
    <main>
      <section class="composer">
        <form id="send-form">
          <div class="mode-row">
            <label>
              <input type="radio" name="mode" value="text">
              <span>Texto livre</span>
            </label>
            <label>
              <input type="radio" name="mode" value="agenda" checked>
              <span>Agenda</span>
            </label>
            <label>
              <input type="radio" name="mode" value="checkin">
              <span>Check-in</span>
            </label>
            <label>
              <input type="radio" name="mode" value="checkin2">
              <span>Check-in 2</span>
            </label>
            <label>
              <input type="radio" name="mode" value="terms">
              <span>Aceite</span>
            </label>
          </div>

          <div class="field">
            <label for="phone">Telefone</label>
            <input id="phone" name="phone" inputmode="numeric" autocomplete="tel" placeholder="5511999999999" required>
          </div>
          <div class="field">
            <label for="client_name">Nome do cliente</label>
            <input id="client_name" name="client_name" placeholder="Felipe Varella">
          </div>
          <div class="field">
            <label for="client_address">Endereço do cliente</label>
            <input id="client_address" name="client_address" placeholder="Rua Exemplo, 123 - Santos/SP">
          </div>
          <div class="grid-two">
            <div class="field">
              <label for="schedule_date">Data</label>
              <input id="schedule_date" name="schedule_date" placeholder="20/05/2026">
            </div>
            <div class="field">
              <label for="schedule_time">Horário</label>
              <input id="schedule_time" name="schedule_time" placeholder="15:00">
            </div>
          </div>
          <div class="field">
            <label for="service">Serviço</label>
            <input id="service" name="service" value="Atendimento da cooperativa">
          </div>
          <div class="field">
            <label for="message">Mensagem livre ou prévia da agenda</label>
            <textarea id="message" name="message" placeholder="Digite a mensagem..." required></textarea>
          </div>
          <button id="send-button" type="submit">Enviar mensagem</button>
        </form>
        <div id="notice" class="notice">Pronto para enviar pela Z-API.</div>
      </section>
      <section class="events">
        <div class="status-card">
          <strong>Status do fluxo</strong>
          <span id="agenda-status">Aguardando envio</span>
        </div>
        <div class="toolbar">
          <h2>Histórico da conversa</h2>
          <button class="small-button" id="refresh-button" type="button">Atualizar</button>
        </div>
        <div id="timeline" class="timeline"></div>
      </section>
    </main>
  </div>
  <script>
    const form = document.querySelector("#send-form");
    const button = document.querySelector("#send-button");
    const notice = document.querySelector("#notice");
    const timeline = document.querySelector("#timeline");
    const refreshButton = document.querySelector("#refresh-button");
    const phoneInput = document.querySelector("#phone");
    const messageInput = document.querySelector("#message");
    const agendaStatus = document.querySelector("#agenda-status");
    const agendaFields = ["client_name", "client_address", "schedule_date", "schedule_time", "service"]
      .map((name) => document.querySelector(`[name="${name}"]`));
    const savedPhone = localStorage.getItem("novaGuardaPhone");
    if (savedPhone) phoneInput.value = savedPhone;
    const savedAgenda = JSON.parse(localStorage.getItem("novaGuardaAgenda") || "{}");
    agendaFields.forEach((field) => {
      if (savedAgenda[field.name]) field.value = savedAgenda[field.name];
    });

    let currentEvents = [];

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    function setNotice(text, kind = "") {
      notice.className = `notice ${kind}`.trim();
      notice.textContent = text;
    }

    function getMessageText(payload) {
      return payload?.text?.message || payload?.buttonReply?.message || payload?.buttonsResponseMessage?.selectedDisplayText || payload?.listResponseMessage?.title || "";
    }

    function getEventKind(payload) {
      if (payload.type === "SentMessage") return "sent";
      if (payload.type === "AutoReply") return "auto";
      if (payload.type === "ReceivedCallback") return "received";
      return "system";
    }

    function getEventTitle(payload) {
      if (payload.summary_label) return payload.summary_label;
      if (payload.type === "SentMessage") return `Enviado para ${payload.phone || "contato"}`;
      if (payload.type === "AutoReply") return `Resposta automática para ${payload.phone || "contato"}`;
      if (payload.type === "LocationLinkCallback") return `Localização confirmada por ${payload.phone || "contato"}`;
      if (payload.type === "ReceivedCallback") return `${payload.chatName || payload.senderName || payload.phone || "Contato"}`;
      return payload.type || "Evento";
    }

    function getEventBody(payload, event) {
      const text = getMessageText(payload);
      const location = payload.location || null;
      if (location) {
        return `Localização recebida com data e hora
Data/Hora: ${location.received_at || event.received_at || ""}
Latitude: ${location.latitude ?? ""}
Longitude: ${location.longitude ?? ""}
Endereço: ${location.address || ""}`;
      }
      if (text) return text;
      return JSON.stringify(payload, null, 2);
    }

    function getMapsUrl(payload) {
      const location = payload.location || null;
      if (!location) return "";
      if (location.latitude && location.longitude) return `https://www.google.com/maps?q=${location.latitude},${location.longitude}`;
      return location.url || location.maps_url || "";
    }

    function getDecision(text) {
      const normalized = String(text || "").trim().toLowerCase();
      if (["1", "confirmar", "confirmado", "confirmada"].includes(normalized)) return "Agenda confirmada";
      if (["2", "reagendar", "remarcar"].includes(normalized)) return "Solicitou reagendamento";
      if (["3", "cancelar", "cancelado", "cancelada"].includes(normalized)) return "Agenda cancelada";
      if (["sim, cheguei", "cheguei", "sim"].includes(normalized)) return "Chegou ao local";
      if (["vou atrasar", "atrasarei", "atrasar"].includes(normalized)) return "Vai atrasar";
      if (["15 minutos", "15 min"].includes(normalized)) return "Vai atrasar 15 minutos";
      if (["30 minutos", "30 min"].includes(normalized)) return "Vai atrasar 30 minutos";
      if (["1 hora", "60 minutos", "60 min"].includes(normalized)) return "Vai atrasar 1 hora";
      if (["não vou", "nao vou", "não irei", "nao irei"].includes(normalized)) return "Não vai comparecer";
      if (["problema pessoal"].includes(normalized)) return "Motivo: problema pessoal";
      if (["sem acesso ao local"].includes(normalized)) return "Motivo: sem acesso ao local";
      if (["cliente cancelou"].includes(normalized)) return "Motivo: cliente cancelou";
      if (["outro motivo"].includes(normalized)) return "Motivo: outro motivo";
      return "";
    }

    function buildAgendaPreview() {
      const data = Object.fromEntries(agendaFields.map((field) => [field.name, field.value.trim()]));
      const client = data.client_name || "Cliente";
      const address = data.client_address || "Endereço não informado";
      const date = data.schedule_date || "Data não informada";
      const time = data.schedule_time || "Horário não informado";
      const service = data.service || "Atendimento da cooperativa";

      return `Olá, ${client}! Tudo bem?

Temos uma agenda pendente para confirmação.

Cliente: ${client}
Endereço: ${address}
Data: ${date}
Horário: ${time}
Serviço: ${service}

Por favor, escolha uma das opções abaixo.`;
    }

    function buildCheckinPreview() {
      const data = Object.fromEntries(agendaFields.map((field) => [field.name, field.value.trim()]));
      const client = data.client_name || "Cliente";
      const address = data.client_address || "Endereço não informado";
      const date = data.schedule_date || "Data não informada";
      const time = data.schedule_time || "Horário não informado";
      const service = data.service || "Atendimento da cooperativa";

      return `Olá, ${client}! Tudo bem?

Check-in da sua agenda:

Endereço: ${address}
Data: ${date}
Horário: ${time}
Serviço: ${service}

Você já chegou ao local?

Se escolher "Sim, cheguei", envie sua localização em seguida.`;
    }

    function buildCheckin2Preview() {
      const data = Object.fromEntries(agendaFields.map((field) => [field.name, field.value.trim()]));
      const client = data.client_name || "Cliente";
      const address = data.client_address || "Endereço não informado";
      const date = data.schedule_date || "Data não informada";
      const time = data.schedule_time || "Horário não informado";
      const service = data.service || "Atendimento da cooperativa";

      return `Olá, ${client}! Tudo bem?

Check-in da sua agenda:

Endereço: ${address}
Data: ${date}
Horário: ${time}
Serviço: ${service}

Você já chegou ao local?

Se escolher "Sim, cheguei", enviaremos um link para confirmar sua localização automaticamente.`;
    }

    function buildTermsPreview() {
      const data = Object.fromEntries(agendaFields.map((field) => [field.name, field.value.trim()]));
      const client = data.client_name || "Cliente";
      return `Olá, ${client}! Segue o termo de aceite para leitura.

Após ler o PDF, escolha uma das opções de aceite.

Esse aceite será registrado no sistema.`;
    }

    function syncMessagePreview() {
      if (form.mode.value === "agenda") {
        messageInput.value = buildAgendaPreview();
      } else if (form.mode.value === "checkin") {
        messageInput.value = buildCheckinPreview();
      } else if (form.mode.value === "checkin2") {
        messageInput.value = buildCheckin2Preview();
      } else if (form.mode.value === "terms") {
        messageInput.value = buildTermsPreview();
      } else {
        messageInput.value = "";
      }
    }

    function readAgendaData() {
      return Object.fromEntries(agendaFields.map((field) => [field.name, field.value.trim()]));
    }

    function renderEvents(events) {
      currentEvents = events;
      if (!events.length) {
        timeline.innerHTML = '<div class="empty">Nenhuma resposta recebida ainda.</div>';
        return;
      }

      timeline.innerHTML = events.map((event, index) => {
        const payload = event.payload || {};
        const kind = getEventKind(payload);
        const text = getMessageText(payload);
        const decision = getDecision(text);
        const title = getEventTitle(payload);
        const mapsUrl = getMapsUrl(payload);
        const body = getEventBody(payload, event);
        const canReuse = Boolean(text) && payload.type !== "ReceivedCallback";

        return `
          <article class="event ${kind}">
            <div class="event-head"><span>${escapeHtml(event.received_at)}</span><span>${escapeHtml(title)}</span></div>
            <div class="message-text">${escapeHtml(body)}</div>
            ${decision ? `<span class="decision">${decision}</span>` : ""}
            <div class="event-actions">
              <button class="action-button" type="button" data-action="copy" data-index="${index}">Copiar resposta</button>
              ${canReuse ? `<button class="action-button" type="button" data-action="reuse" data-index="${index}">Usar no campo</button>` : ""}
              ${mapsUrl ? `<button class="action-button" type="button" data-action="map" data-index="${index}">Abrir mapa</button>` : ""}
            </div>
            <details>
              <summary>Ver payload completo</summary>
              <pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
            </details>
          </article>
        `;
      }).join("");

      const latestDecision = events.find((event) => getDecision(getMessageText(event.payload || {})));
      if (latestDecision) {
        agendaStatus.textContent = getDecision(getMessageText(latestDecision.payload || {}));
      }
    }

    timeline.addEventListener("click", async (event) => {
      const actionButton = event.target.closest("[data-action]");
      if (!actionButton) return;

      const item = currentEvents[Number(actionButton.dataset.index)];
      if (!item) return;

      const payload = item.payload || {};
      const body = getEventBody(payload, item);
      const mapsUrl = getMapsUrl(payload);
      const action = actionButton.dataset.action;

      if (action === "copy") {
        await navigator.clipboard.writeText(body);
        setNotice("Resposta copiada do histórico.", "ok");
      } else if (action === "reuse") {
        messageInput.value = body;
        messageInput.focus();
        setNotice("Resposta carregada no campo de mensagem.", "ok");
      } else if (action === "map" && mapsUrl) {
        window.open(mapsUrl, "_blank", "noreferrer");
      }
    });

    async function loadEvents() {
      const response = await fetch("/api/events");
      const data = await response.json();
      renderEvents(data.events || []);
      await loadAgendaStatus();
    }

    async function loadAgendaStatus() {
      const phone = phoneInput.value.replace(/\\D/g, "");
      if (!phone) {
        agendaStatus.textContent = "Aguardando envio";
        return;
      }

      if (form.mode.value === "terms") {
        const response = await fetch(`/api/terms-status?phone=${phone}`);
        const data = await response.json();
        agendaStatus.textContent = data.status_label || "Aceite não enviado";
        return;
      }

      const response = await fetch(`/api/agenda-status?phone=${phone}`);
      const data = await response.json();
      agendaStatus.textContent = data.status_label || "Aguardando envio";
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      setNotice("Enviando...");

      const phone = form.phone.value.replace(/\\D/g, "");
      const message = form.message.value.trim();
      const mode = form.mode.value;
      const agendaData = readAgendaData();
      localStorage.setItem("novaGuardaPhone", phone);
      localStorage.setItem("novaGuardaAgenda", JSON.stringify(agendaData));

      try {
        const response = await fetch("/api/send-message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, message, mode, ...agendaData }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
          throw new Error(data.error || "Falha ao enviar mensagem.");
        }
        const label = mode === "agenda"
          ? "Mensagem com botões enviada"
          : mode === "checkin"
          ? "Check-in enviado"
          : mode === "terms"
          ? "Termo enviado"
          : "Mensagem enviada";
        setNotice(`${label}. ID: ${data.response.messageId || data.response.id || "sem id"}`, "ok");
        if (mode === "agenda" || mode === "checkin" || mode === "checkin2" || mode === "terms") {
          agendaStatus.textContent = mode === "checkin" || mode === "checkin2" ? "Check-in enviado" : mode === "terms" ? "Aguardando aceite" : "Aguardando resposta";
        }
        if (mode !== "agenda") {
          messageInput.value = "";
        }
      } catch (error) {
        setNotice(error.message, "error");
      } finally {
        button.disabled = false;
      }
    });

    refreshButton.addEventListener("click", loadEvents);
    agendaFields.forEach((field) => field.addEventListener("input", syncMessagePreview));
    document.querySelectorAll('[name="mode"]').forEach((field) => field.addEventListener("change", syncMessagePreview));
    syncMessagePreview();
    loadEvents();
    setInterval(loadEvents, 5000);
  </script>
</body>
</html>
"""


LOCATION_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Confirmar localização</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #eaf4ee;
      color: #10251a;
      font-family: Arial, Helvetica, sans-serif;
    }
    .box {
      width: min(440px, calc(100vw - 28px));
      border: 1px solid #7f8da6;
      border-radius: 6px;
      background: #fff;
      padding: 18px;
      box-shadow: 6px 6px 0 rgba(19, 32, 51, .16);
    }
    h1 { margin: 0 0 10px; font-size: 20px; }
    p { color: #667085; line-height: 1.45; }
    button {
      width: 100%;
      border: 1px solid #0f4c33;
      border-radius: 4px;
      padding: 12px 14px;
      color: #fff;
      background: linear-gradient(180deg, #2f9d6a, #17623f);
      font-weight: 700;
      cursor: pointer;
    }
    .status { margin-top: 12px; color: #17623f; font-weight: 700; }
  </style>
</head>
<body>
  <div class="box">
    <h1>Confirmar localização</h1>
    <p>Toque no botão abaixo e permita o acesso à localização para concluir o check-in.</p>
    <button id="confirm-button">Enviar minha localização</button>
    <div id="status" class="status"></div>
  </div>
  <script>
    const button = document.querySelector("#confirm-button");
    const statusBox = document.querySelector("#status");

    button.addEventListener("click", () => {
      statusBox.textContent = "Solicitando localização...";
      if (!navigator.geolocation) {
        statusBox.textContent = "Seu navegador não suporta localização.";
        return;
      }

      navigator.geolocation.getCurrentPosition(async (position) => {
        statusBox.textContent = "Enviando localização...";
        const response = await fetch(window.location.pathname, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          }),
        });
        const data = await response.json();
        const confirmadoEm = data.confirmado_em || new Date().toLocaleString("pt-BR");

        if (data.ok) {
          statusBox.textContent = `Sua localização foi registrada com sucesso.
Data/Hora: ${confirmadoEm}

Esta janela será fechada automaticamente.`;

          button.disabled = true;

          setTimeout(() => {
            window.close();

            document.body.innerHTML = `
              <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 40px auto; padding: 24px; border-radius: 14px; background: #fff; box-shadow: 0 8px 24px rgba(0,0,0,.12); text-align: center;">
                <h2>Check-in concluído ✅</h2>
                <p>Sua localização foi registrada com sucesso.</p>
                <p>Data/Hora: ${confirmadoEm}</p>
                <p>Você já pode fechar esta janela.</p>
              </div>
            `;
          }, 1800);
        } else {
          statusBox.textContent = data.message || "Não foi possível registrar sua localização.";
          button.disabled = false;
        }
      }, () => {
        statusBox.textContent = "Não foi possível acessar sua localização. Abra este link no Chrome/Safari e permita o acesso ao GPS.";
      }, {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      });
    });
  </script>
</body>
</html>
"""


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value or not value.strip():
        raise RuntimeError(f"Variável de ambiente obrigatória não encontrada: {name}")

    return value.strip()


def normalize_phone(value: str) -> str:
    phone = "".join(char for char in str(value) if char.isdigit())
    if len(phone) in {10, 11}:
        return f"55{phone}"
    return phone


def get_payload_text(payload: dict[str, Any]) -> str:
    text = payload.get("text")
    if isinstance(text, dict) and text.get("message"):
        return str(text["message"])

    for key in ("buttonReply", "buttonsResponseMessage", "listResponseMessage"):
        value = payload.get(key)
        if isinstance(value, dict):
            for text_key in ("selectedRowId", "id", "selectedButtonId", "selectedDisplayText", "title", "message"):
                if value.get(text_key):
                    return str(value[text_key])

    return ""


def classify_agenda_reply(text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized in {"1", "confirmar", "confirmado", "confirmada"}:
        return "confirmed"
    if normalized in {"2", "reagendar", "remarcar", "reagendamento"}:
        return "reschedule_requested"
    if normalized in {"3", "cancelar", "cancelado", "cancelada"}:
        return "cancelled"
    return None


def classify_checkin_reply(text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized in {"sim, cheguei", "cheguei", "sim", "checkin_arrived", "checkin2_arrived"}:
        return "arrived_link"
    if normalized in {"checkin2_arrived"}:
        return "arrived_link"
    if normalized in {"vou atrasar", "atrasarei", "atrasar", "checkin_late"}:
        return "late"
    if normalized in {"não vou", "nao vou", "não irei", "nao irei", "checkin_not_going"}:
        return "not_going"
    if normalized in {"15 minutos", "15 min", "late_15"}:
        return "late_15"
    if normalized in {"30 minutos", "30 min", "late_30"}:
        return "late_30"
    if normalized in {"1 hora", "60 minutos", "60 min", "late_60"}:
        return "late_60"
    if normalized in {"problema pessoal", "reason_personal"}:
        return "reason_personal"
    if normalized in {"sem acesso ao local", "reason_access"}:
        return "reason_access"
    if normalized in {"cliente cancelou", "reason_client_cancelled"}:
        return "reason_client_cancelled"
    if normalized in {"outro motivo", "reason_other"}:
        return "reason_other"
    return None


def should_send_location_link(checkin_decision: str, state: dict[str, Any]) -> bool:
    if checkin_decision == "arrived_link":
        return True

    if checkin_decision != "arrived":
        return False

    mode = state.get("mode")
    return mode in {"checkin2", None}


def is_terms_acceptance(text: str) -> bool:
    normalized = " ".join(text.strip().lower().split())
    return normalized in {
        TERMS_ACCEPTANCE_TEXT,
        "terms_accept",
        "aceito os termos",
        "li e aceito",
        "eu li e aceito os termos",
    }


def is_terms_rejection(text: str) -> bool:
    normalized = " ".join(text.strip().lower().split())
    return normalized in {
        TERMS_REJECTION_TEXT,
        "terms_reject",
        "nao aceito os termos",
        "não aceito",
        "nao aceito",
    }


def agenda_status_label(status: str) -> str:
    labels = {
        "pending": "Aguardando resposta",
        "confirmed": "Agenda confirmada",
        "reschedule_requested": "Reagendamento solicitado",
        "cancelled": "Agenda cancelada",
        "conflict": "Revisar manualmente",
    }
    return labels.get(status, status)


def checkin_status_label(status: str) -> str:
    labels = {
        "checkin_sent": "Check-in enviado",
        "arrived": "Chegou ao local",
        "location_received": "Localização recebida com data e hora",
        "location_requested": "Solicitou envio de localização",
        "late": "Aguardando tempo de atraso",
        "late_15": "Vai atrasar 15 minutos",
        "late_30": "Vai atrasar 30 minutos",
        "late_60": "Vai atrasar 1 hora",
        "not_going": "Não vai comparecer",
        "reason_personal": "Não vai: problema pessoal",
        "reason_access": "Não vai: sem acesso ao local",
        "reason_client_cancelled": "Não vai: cliente cancelou",
        "reason_other": "Não vai: outro motivo",
    }
    return labels.get(status, status)


def build_agenda_message(data: dict[str, str]) -> str:
    client = data.get("client_name") or "Cliente"
    address = data.get("client_address") or "Endereço não informado"
    date = data.get("schedule_date") or "Data não informada"
    time = data.get("schedule_time") or "Horário não informado"
    service = data.get("service") or "Atendimento da cooperativa"

    return (
        f"Olá, {client}! Tudo bem?\n\n"
        "Temos uma agenda pendente para confirmação.\n\n"
        f"Cliente: {client}\n"
        f"Endereço: {address}\n"
        f"Data: {date}\n"
        f"Horário: {time}\n"
        f"Serviço: {service}\n\n"
        "Por favor, escolha uma das opções abaixo."
    )


def build_checkin_message(data: dict[str, str]) -> str:
    client = data.get("client_name") or "Cliente"
    address = data.get("client_address") or "Endereço não informado"
    date = data.get("schedule_date") or "Data não informada"
    time = data.get("schedule_time") or "Horário não informado"
    service = data.get("service") or "Atendimento da cooperativa"

    return (
        f"Olá, {client}! Tudo bem?\n\n"
        "Check-in da sua agenda:\n\n"
        f"Endereço: {address}\n"
        f"Data: {date}\n"
        f"Horário: {time}\n"
        f"Serviço: {service}\n\n"
        "Você já chegou ao local?\n\n"
        'Se escolher "Sim, cheguei", envie sua localização em seguida.'
    )


def build_checkin2_message(data: dict[str, str]) -> str:
    message = build_checkin_message(data)
    return message.replace(
        'Se escolher "Sim, cheguei", envie sua localização em seguida.',
        'Se escolher "Sim, cheguei", enviaremos um link para confirmar sua localização automaticamente.',
    )


def build_terms_message(data: dict[str, str]) -> str:
    client = data.get("client_name") or "Cliente"
    return (
        f"Olá, {client}! Segue o termo de aceite para leitura.\n\n"
        "Após ler o PDF, escolha uma das opções de aceite.\n\n"
        "Esse aceite será registrado no sistema."
    )


def is_public_browser_url(url: str) -> bool:
    lowered = url.lower()
    return (
        lowered.startswith("https://")
        and "ngrok" not in lowered
        and not any(host in lowered for host in LOCAL_HOSTS)
    )


def get_location_link_base_url() -> str:
    request_base_url = request.host_url.strip().rstrip("/")
    if is_public_browser_url(request_base_url):
        return request_base_url

    if is_public_browser_url(PUBLIC_BASE_URL):
        return PUBLIC_BASE_URL

    return PUBLIC_BASE_URL or request_base_url or f"http://localhost:{PORT}"


def create_location_link(phone: str) -> str:
    token = uuid.uuid4().hex
    LOCATION_LINKS[token] = {
        "phone": phone,
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "status": "pending",
    }
    base_url = get_location_link_base_url()
    return f"{base_url}/checkin-location/{token}"


def build_location_confirmation_message(address: str) -> tuple[str, str]:
    confirmed_at = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    reply = (
        "Sua localização foi registrada com sucesso.\n"
        f"Data/Hora: {confirmed_at}\n"
        f"Local aproximado: {address}\n"
        "Obrigado pelas informações."
    )
    return reply, confirmed_at


def reverse_geocode(latitude: float, longitude: float) -> str:
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 18,
                "addressdetails": 1,
            },
            headers={"User-Agent": "NovaGuardaCheckin/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("display_name", ""))
    except requests.RequestException as exc:
        logger.warning("Não foi possível obter endereço aproximado: %s", exc)
        return ""


def build_confirmation_reply(status: str, agenda: dict[str, Any] | None = None) -> str:
    agenda = agenda or {}
    client = agenda.get("client_name") or "sua agenda"
    date = agenda.get("schedule_date") or "a data combinada"
    time = agenda.get("schedule_time") or "o horário combinado"

    if status == "confirmed":
        return f"Perfeito, {client}! Sua agenda foi confirmada para {date} às {time}."
    if status == "reschedule_requested":
        return "Recebemos sua solicitação de reagendamento. Nossa equipe vai entrar em contato para combinar um novo horário."
    if status == "cancelled":
        return "Recebemos seu cancelamento. A agenda foi marcada como cancelada."
    if status == "conflict":
        return "Recebemos sua nova resposta. Como ela altera uma agenda já cancelada, nossa equipe vai revisar manualmente."
    return "Recebemos sua resposta. Obrigado!"


def build_checkin_reply(status: str) -> str:
    if status == "arrived":
        return "Perfeito, recebemos seu check-in. Agora envie sua localização atual pelo WhatsApp, por favor."
    if status == "location_received":
        return "Localização recebida com data e hora com sucesso. Obrigado!"
    if status == "late":
        return "Sem problema. Informe quanto tempo deve atrasar."
    if status == "late_15":
        return "Recebido. Registramos que você deve atrasar 15 minutos."
    if status == "late_30":
        return "Recebido. Registramos que você deve atrasar 30 minutos."
    if status == "late_60":
        return "Recebido. Registramos que você deve atrasar 1 hora."
    if status == "not_going":
        return "Recebido. Informe o motivo do não comparecimento."
    if status == "reason_personal":
        return "Recebido. Registramos o motivo: problema pessoal."
    if status == "reason_access":
        return "Recebido. Registramos o motivo: sem acesso ao local."
    if status == "reason_client_cancelled":
        return "Recebido. Registramos o motivo: cliente cancelou."
    if status == "reason_other":
        return "Recebido. Registramos o motivo: outro motivo. Se quiser, envie uma mensagem com mais detalhes."
    return "Recebemos sua resposta de check-in."


def update_agenda_state(phone: str, decision: str, text: str) -> dict[str, Any]:
    state = AGENDA_STATE.setdefault(
        phone,
        {
            "phone": phone,
            "status": "pending",
            "status_label": agenda_status_label("pending"),
            "agenda": {},
            "history": [],
        },
    )

    previous_status = state.get("status", "pending")
    next_status = decision

    if previous_status == "cancelled" and decision == "confirmed":
        next_status = "conflict"

    state["status"] = next_status
    state["status_label"] = agenda_status_label(next_status)
    state["last_reply"] = text
    state["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    state.setdefault("history", []).append(
        {
            "at": state["updated_at"],
            "reply": text,
            "from": previous_status,
            "to": next_status,
        }
    )

    return state


def build_zapi_update_url(instance_id: str, instance_token: str) -> str:
    return (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/update-every-webhooks"
    )


def start_ngrok_tunnel(port: int) -> str:
    ngrok_authtoken = os.getenv("NGROK_AUTHTOKEN", "").strip()
    pyngrok_config = None

    if LOCAL_NGROK_PATH.exists():
        pyngrok_config = PyngrokConfig(ngrok_path=str(LOCAL_NGROK_PATH))
        logger.info("Usando ngrok local: %s", LOCAL_NGROK_PATH)
    else:
        logger.warning(
            "ngrok.exe local não encontrado em %s. Vou usar o padrão do pyngrok.",
            LOCAL_NGROK_PATH,
        )

    if ngrok_authtoken and ngrok_authtoken != "COLE_SEU_TOKEN_DO_NGROK_AQUI":
        try:
            logger.info("Configurando authtoken do ngrok...")
            ngrok.set_auth_token(ngrok_authtoken, pyngrok_config=pyngrok_config)
            logger.info("Authtoken do ngrok configurado com sucesso.")
        except Exception as exc:
            logger.warning(
                "Não foi possível salvar o authtoken pelo pyngrok. "
                "Vou tentar continuar usando a configuração já salva no ngrok. Erro: %s",
                exc,
            )
    else:
        logger.warning(
            "NGROK_AUTHTOKEN vazio ou inválido no .env. "
            "Vou tentar usar a configuração já salva no ngrok."
        )

    logger.info("Abrindo túnel ngrok para a porta %s...", port)

    tunnel = ngrok.connect(addr=port, proto="http", pyngrok_config=pyngrok_config)
    public_url = tunnel.public_url

    if not public_url.startswith("https://"):
        public_url = public_url.replace("http://", "https://", 1)

    logger.info("URL pública do ngrok: %s", public_url)

    return public_url


def update_zapi_webhook(public_url: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    webhook_url = f"{public_url}{WEBHOOK_PATH}"
    update_url = build_zapi_update_url(instance_id, instance_token)

    headers = {
        "Client-Token": client_token,
        "Content-Type": "application/json",
    }

    payload = {"value": webhook_url}

    logger.info("Atualizando webhook da Z-API para: %s", webhook_url)

    try:
        response = requests.put(
            update_url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        logger.info("Status Z-API: %s", response.status_code)
        logger.info("Resposta Z-API: %s", response.text)

        response.raise_for_status()
        response_payload = response.json()

        if isinstance(response_payload, dict) and response_payload.get("error"):
            raise RuntimeError(f"Z-API retornou erro: {response_payload}")

    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        response_text = getattr(getattr(exc, "response", None), "text", "")

        logger.exception(
            "Erro ao atualizar webhook da Z-API. Status: %s | Resposta: %s",
            status_code,
            response_text,
        )

        raise
    except ValueError as exc:
        logger.exception("A Z-API retornou uma resposta que não é JSON válido.")
        raise RuntimeError("Resposta inválida da Z-API.") from exc

    logger.info("Webhook atualizado com sucesso.")

    return {
        "status_code": response.status_code,
        "response": response_payload,
        "webhook_url": webhook_url,
    }


def send_zapi_text(phone: str, message: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-text"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={"phone": phone, "message": message},
        timeout=30,
    )

    logger.info("Status envio Z-API: %s", response.status_code)
    logger.info("Resposta envio Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload


def send_zapi_document(phone: str, document_path: Path, caption: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    document_base64 = base64.b64encode(document_path.read_bytes()).decode("ascii")
    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-document/pdf"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={
            "phone": phone,
            "document": f"data:application/pdf;base64,{document_base64}",
            "fileName": "Termo de Aceite - Nova Guarda.pdf",
            "caption": caption,
        },
        timeout=30,
    )

    logger.info("Status envio documento Z-API: %s", response.status_code)
    logger.info("Resposta envio documento Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload


def send_zapi_agenda_buttons(phone: str, message: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-button-list"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={
            "phone": phone,
            "message": message,
            "buttonList": {
                "buttons": [
                    {"id": "confirmar", "label": "Confirmar"},
                    {"id": "reagendar", "label": "Reagendar"},
                    {"id": "cancelar", "label": "Cancelar"},
                ]
            },
        },
        timeout=30,
    )

    logger.info("Status envio botões Z-API: %s", response.status_code)
    logger.info("Resposta envio botões Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload


def send_zapi_terms_buttons(phone: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-button-list"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={
            "phone": phone,
            "message": "Após ler o termo, escolha uma opção:",
            "buttonList": {
                "buttons": [
                    {"id": "terms_accept", "label": "Li e aceito os termos"},
                    {"id": "terms_reject", "label": "Não aceito os termos"},
                ]
            },
        },
        timeout=30,
    )

    logger.info("Status envio botões de aceite Z-API: %s", response.status_code)
    logger.info("Resposta envio botões de aceite Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload


def send_zapi_checkin_options(phone: str, message: str, use_location_link: bool = False) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-option-list"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={
            "phone": phone,
            "message": message,
            "optionList": {
                "title": "Check-in",
                "buttonLabel": "Responder check-in",
                "options": [
                    {
                        "id": "checkin2_arrived" if use_location_link else "checkin_arrived",
                        "title": "Sim, cheguei",
                        "description": "Confirmar chegada e receber link de localização" if use_location_link else "Confirmar chegada e enviar localização em seguida",
                    },
                    {
                        "id": "checkin_late",
                        "title": "Vou atrasar",
                        "description": "Informar tempo de atraso",
                    },
                    {
                        "id": "checkin_not_going",
                        "title": "Não vou",
                        "description": "Informar motivo do não comparecimento",
                    },
                ],
            },
        },
        timeout=30,
    )

    logger.info("Status envio check-in Z-API: %s", response.status_code)
    logger.info("Resposta envio check-in Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload


def send_zapi_late_buttons(phone: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-button-list"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={
            "phone": phone,
            "message": "Quanto tempo você deve atrasar?",
            "buttonList": {
                "buttons": [
                    {"id": "late_15", "label": "15 minutos"},
                    {"id": "late_30", "label": "30 minutos"},
                    {"id": "late_60", "label": "1 hora"},
                ]
            },
        },
        timeout=30,
    )

    logger.info("Status envio atraso Z-API: %s", response.status_code)
    logger.info("Resposta envio atraso Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload


def send_zapi_no_show_reasons(phone: str) -> dict[str, Any]:
    instance_id = get_required_env("ZAPI_INSTANCE_ID")
    instance_token = get_required_env("ZAPI_INSTANCE_TOKEN")
    client_token = get_required_env("ZAPI_CLIENT_TOKEN")

    send_url = (
        f"{ZAPI_BASE_URL}/instances/{instance_id}"
        f"/token/{instance_token}/send-option-list"
    )

    response = requests.post(
        send_url,
        headers={
            "Client-Token": client_token,
            "Content-Type": "application/json",
        },
        json={
            "phone": phone,
            "message": "Qual o motivo do não comparecimento?",
            "optionList": {
                "title": "Motivo",
                "buttonLabel": "Escolher motivo",
                "options": [
                    {
                        "id": "reason_personal",
                        "title": "Problema pessoal",
                        "description": "Não vou por problema pessoal",
                    },
                    {
                        "id": "reason_access",
                        "title": "Sem acesso ao local",
                        "description": "Não consegui acessar o local",
                    },
                    {
                        "id": "reason_client_cancelled",
                        "title": "Cliente cancelou",
                        "description": "O cliente cancelou a visita",
                    },
                    {
                        "id": "reason_other",
                        "title": "Outro motivo",
                        "description": "Outro motivo não listado",
                    },
                ],
            },
        },
        timeout=30,
    )

    logger.info("Status envio motivos Z-API: %s", response.status_code)
    logger.info("Resposta envio motivos Z-API: %s", response.text)
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Z-API retornou erro: {payload}")

    return payload



def get_payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Transforma payloads brutos da Z-API em informações amigáveis para o painel/log.
    """
    event_type = payload.get("type") or payload.get("event") or "Evento desconhecido"
    phone = payload.get("phone") or payload.get("from") or payload.get("sender") or ""

    summary = {
        "event_type": event_type,
        "phone": phone,
        "title": "Evento recebido",
        "description": "Payload recebido da Z-API.",
        "emoji": "📦",
        "category": "technical",
        "important": False,
    }

    # Status de mensagem enviada
    if event_type == "MessageStatusCallback":
        status = payload.get("status") or "STATUS_DESCONHECIDO"
        ids = payload.get("ids") or []

        status_label = {
            "SENT": "enviada",
            "RECEIVED": "recebida/entregue",
            "READ": "lida",
            "PLAYED": "áudio reproduzido",
            "ERROR": "erro no envio",
        }.get(status, status)

        summary.update({
            "title": f"Status da mensagem: {status_label}",
            "description": f"Mensagem {status_label} para {phone}. ID: {', '.join(ids) if ids else 'sem ID'}",
            "emoji": "✅" if status in {"SENT", "RECEIVED", "READ"} else "⚠️",
            "category": "message_status",
            "important": False,
        })
        return summary

    # Presença/status do contato
    if event_type == "PresenceChatCallback":
        status = payload.get("status") or "DESCONHECIDO"
        last_seen = payload.get("lastSeen")

        status_label = {
            "AVAILABLE": "online/disponível",
            "UNAVAILABLE": "offline/indisponível",
            "TYPING": "digitando",
            "RECORDING": "gravando áudio",
        }.get(status, status)

        summary.update({
            "title": f"Presença do contato: {status_label}",
            "description": f"Contato {phone} está {status_label}. Última visualização: {last_seen or 'não informada'}",
            "emoji": "👀",
            "category": "presence",
            "important": False,
        })
        return summary

    # Mensagem de texto recebida
    text_message = (
        payload.get("text", {}).get("message")
        if isinstance(payload.get("text"), dict)
        else payload.get("text")
    )

    if text_message:
        summary.update({
            "title": "Mensagem recebida",
            "description": f'{phone}: "{text_message}"',
            "emoji": "📩",
            "category": "received_message",
            "important": True,
        })
        return summary

    # Botão/lista recebida
    button_id = None
    button_title = None

    if isinstance(payload.get("buttonReply"), dict):
        button_id = payload["buttonReply"].get("id")
        button_title = payload["buttonReply"].get("title")

    if isinstance(payload.get("listResponseMessage"), dict):
        button_id = payload["listResponseMessage"].get("selectedRowId")
        button_title = payload["listResponseMessage"].get("title")

    if button_id or button_title:
        summary.update({
            "title": "Resposta de botão recebida",
            "description": f"{phone}: {button_title or button_id}",
            "emoji": "🟢",
            "category": "button_reply",
            "important": True,
        })
        return summary

    # Localização recebida com data e hora
    location = payload.get("location")
    if isinstance(location, dict):
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        summary.update({
            "title": "Localização recebida com data e hora",
            "description": f"{phone}: latitude {latitude}, longitude {longitude}",
            "emoji": "📍",
            "category": "location",
            "important": True,
        })
        return summary

    # Fallback
    summary.update({
        "title": f"Evento técnico: {event_type}",
        "description": f"Evento técnico recebido de {phone or 'telefone não informado'}.",
        "emoji": "⚙️",
        "category": "technical",
        "important": False,
    })

    return summary

def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/favicon/<path:filename>")
    def favicon_asset(filename: str):
        return send_from_directory(str(PROJECT_DIR / "favicon"), filename)

    @app.post(WEBHOOK_PATH)
    def webhook():
        payload = request.get_json(silent=True)

        if payload is None:
            payload = {
                "raw_body": request.get_data(as_text=True),
                "content_type": request.content_type,
            }

        logger.info("Payload recebido da Z-API: %s", payload)
        RECEIVED_EVENTS.appendleft(
            {
                "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "payload": payload,
                            "summary": get_payload_summary(payload),
            }
        )

        if payload.get("type") == "ReceivedCallback" and not payload.get("fromMe"):
            phone = normalize_phone(str(payload.get("phone", "")).strip())
            text = get_payload_text(payload)
            decision = classify_agenda_reply(text)
            checkin_decision = classify_checkin_reply(text)
            location = payload.get("location")

            if phone and is_terms_acceptance(text) and not payload.get("isGroup"):
                TERMS_STATE[phone] = {
                    "phone": phone,
                    "status": "accepted",
                    "status_label": "Termos aceitos",
                    "accepted_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "reply": text,
                }

                try:
                    reply = "Aceite registrado com sucesso. Obrigado!"
                    response_payload = send_zapi_text(phone, reply)
                    RECEIVED_EVENTS.appendleft(
                        {
                            "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "payload": {
                                "type": "AutoReply",
                                "summary_label": "🤖 Resposta automática enviada",
                                "phone": phone,
                                "status": "terms_accepted",
                                "text": {"message": reply},
                                "response": response_payload,
                            },
                        }
                    )
                except (RuntimeError, requests.RequestException, ValueError) as exc:
                    logger.exception("Erro ao confirmar aceite dos termos: %s", exc)

            elif phone and is_terms_rejection(text) and not payload.get("isGroup"):
                TERMS_STATE[phone] = {
                    "phone": phone,
                    "status": "rejected",
                    "status_label": "Termos recusados",
                    "rejected_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "reply": text,
                }

                try:
                    reply = "Recusa registrada. Nossa equipe poderá entrar em contato para orientar os próximos passos."
                    response_payload = send_zapi_text(phone, reply)
                    RECEIVED_EVENTS.appendleft(
                        {
                            "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "payload": {
                                "type": "AutoReply",
                                "summary_label": "🤖 Resposta automática enviada",
                                "phone": phone,
                                "status": "terms_rejected",
                                "text": {"message": reply},
                                "response": response_payload,
                            },
                        }
                    )
                except (RuntimeError, requests.RequestException, ValueError) as exc:
                    logger.exception("Erro ao confirmar recusa dos termos: %s", exc)

            elif phone and isinstance(location, dict) and not payload.get("isGroup"):
                latitude = location.get("latitude")
                longitude = location.get("longitude")
                state = AGENDA_STATE.setdefault(
                    phone,
                    {
                        "phone": phone,
                        "status": "checkin_sent",
                        "status_label": checkin_status_label("checkin_sent"),
                        "agenda": {},
                        "history": [],
                    },
                )
                state["status"] = "location_received"
                state["status_label"] = checkin_status_label("location_received")
                state["location"] = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "address": location.get("address", ""),
                    "url": location.get("url", ""),
                    "maps_url": f"https://www.google.com/maps?q={latitude},{longitude}" if latitude and longitude else "",
                    "received_at": state["updated_at"],
                }
                state["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                state.setdefault("history", []).append(
                    {
                        "at": state["updated_at"],
                        "reply": "location",
                        "to": "location_received",
                        "location": state["location"],
                    }
                )

                try:
                    location_info = state.get("location", {}) if isinstance(state, dict) else {}
                    address_msg = (
                        location_info.get("address")
                        or location_info.get("maps_url")
                        or location_info.get("url")
                        or "Localização recebida"
                    )

                    reply, confirmado_em = build_location_confirmation_message(address_msg)
                    response_payload = send_zapi_text(phone, reply)
                    RECEIVED_EVENTS.appendleft(
                        {
                            "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "payload": {
                                "type": "AutoReply",
                                "summary_label": "🤖 Resposta automática enviada",
                                "phone": phone,
                                "status": "location_received",
                                "text": {"message": reply},
                                "response": response_payload,
                            },
                        }
                    )
                except (RuntimeError, requests.RequestException, ValueError) as exc:
                    logger.exception("Erro ao confirmar Localização recebida com data e hora: %s", exc)

            elif phone and decision and not payload.get("isGroup"):
                state = update_agenda_state(phone, decision, text)
                reply = build_confirmation_reply(state["status"], state.get("agenda"))

                try:
                    response_payload = send_zapi_text(phone, reply)
                    RECEIVED_EVENTS.appendleft(
                        {
                            "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "payload": {
                                "type": "AutoReply",
                                "summary_label": "🤖 Resposta automática enviada",
                                "phone": phone,
                                "status": state["status"],
                                "text": {"message": reply},
                                "response": response_payload,
                            },
                        }
                    )
                except (RuntimeError, requests.RequestException, ValueError) as exc:
                    logger.exception("Erro ao enviar resposta automática: %s", exc)
            elif phone and checkin_decision and not payload.get("isGroup"):
                state = AGENDA_STATE.setdefault(
                    phone,
                    {
                        "phone": phone,
                        "status": "checkin_sent",
                        "status_label": checkin_status_label("checkin_sent"),
                        "agenda": {},
                        "history": [],
                    },
                )
                state["status"] = checkin_decision
                state["status_label"] = checkin_status_label(checkin_decision)
                state["last_reply"] = text
                state["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                state.setdefault("history", []).append(
                    {
                        "at": state["updated_at"],
                        "reply": text,
                        "to": checkin_decision,
                    }
                )

                try:
                    if should_send_location_link(checkin_decision, state):
                        location_url = create_location_link(phone)
                        reply = (
                            "Perfeito. Clique no link abaixo para confirmar sua localização:\n"
                            f"{location_url}"
                        )
                        response_payload = send_zapi_text(phone, reply)
                    elif checkin_decision == "late":
                        response_payload = send_zapi_late_buttons(phone)
                        reply = "Quanto tempo você deve atrasar?"
                    elif checkin_decision == "not_going":
                        response_payload = send_zapi_no_show_reasons(phone)
                        reply = "Qual o motivo do não comparecimento?"
                    else:
                        reply = build_checkin_reply(checkin_decision)
                        response_payload = send_zapi_text(phone, reply)

                    RECEIVED_EVENTS.appendleft(
                        {
                            "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "payload": {
                                "type": "AutoReply",
                                "summary_label": "🤖 Resposta automática enviada",
                                "phone": phone,
                                "status": checkin_decision,
                                "text": {"message": reply},
                                "response": response_payload,
                            },
                        }
                    )
                except (RuntimeError, requests.RequestException, ValueError) as exc:
                    logger.exception("Erro ao enviar resposta automática de check-in: %s", exc)

        return jsonify(
            {
                "ok": True,
                "message": "Evento recebido com sucesso",
                "payload": payload,
                            "summary": get_payload_summary(payload),
            }
        ), 200

    @app.get("/")
    def chat():
        return render_template_string(CHAT_HTML, port=PORT)

    @app.get("/health")
    def healthcheck():
        return jsonify(
            {
                "status": "online",
                "porta": PORT,
                "webhook": WEBHOOK_PATH,
            }
        ), 200

    @app.get("/checkin-location/<token>")
    def location_checkin_page(token: str):
        if token not in LOCATION_LINKS:
            return "Link de localização inválido ou expirado.", 404
        return render_template_string(LOCATION_HTML)

    @app.post("/checkin-location/<token>")
    def receive_location_checkin(token: str):
        link = LOCATION_LINKS.get(token)
        if not link:
            return jsonify({"ok": False, "message": "Link inválido ou expirado."}), 404

        payload = request.get_json(silent=True) or {}
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        accuracy = payload.get("accuracy")

        if latitude is None or longitude is None:
            return jsonify({"ok": False, "message": "Localização não recebida."}), 400

        phone = link["phone"]
        address = reverse_geocode(float(latitude), float(longitude))
        maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
        location_payload = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "address": address,
            "maps_url": maps_url,
            "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

        link["status"] = "received"
        link["location"] = location_payload
        link["received_at"] = location_payload["received_at"]

        state = AGENDA_STATE.setdefault(
            phone,
            {
                "phone": phone,
                "status": "checkin_sent",
                "status_label": checkin_status_label("checkin_sent"),
                "agenda": {},
                "history": [],
            },
        )
        state["status"] = "location_received"
        state["status_label"] = checkin_status_label("location_received")
        state["location"] = location_payload
        state["updated_at"] = link["received_at"]
        state.setdefault("history", []).append(
            {
                "at": link["received_at"],
                "reply": "location_link",
                "to": "location_received",
                "location": location_payload,
            }
        )

        RECEIVED_EVENTS.appendleft(
            {
                "received_at": link["received_at"],
                "payload": {
                    "type": "LocationLinkCallback",
                    "phone": phone,
                    "location": location_payload,
                },
            }
        )

        reply, confirmado_em = build_location_confirmation_message(address or maps_url)
        try:
            response_payload = send_zapi_text(phone, reply)
            RECEIVED_EVENTS.appendleft(
                {
                    "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "payload": {
                        "type": "AutoReply",
                                "summary_label": "🤖 Resposta automática enviada",
                        "phone": phone,
                        "status": "location_received",
                        "text": {"message": reply},
                        "response": response_payload,
                    },
                }
            )
        except (RuntimeError, requests.RequestException, ValueError) as exc:
            logger.exception("Erro ao confirmar localização do link: %s", exc)

        return jsonify({
            "ok": True,
            "message": "Localização enviada. Obrigado!",
            "confirmado_em": confirmado_em
        }), 200

    @app.get("/api/events")
    def list_events():
        return jsonify({"events": list(RECEIVED_EVENTS)}), 200

    @app.get("/api/agenda-status")
    def agenda_status():
        phone = normalize_phone(str(request.args.get("phone", "")))
        if not phone:
            return jsonify({"status": "empty", "status_label": "Aguardando envio"}), 200

        state = AGENDA_STATE.get(phone)
        if not state:
            return jsonify({"status": "empty", "status_label": "Aguardando envio"}), 200

        return jsonify(state), 200

    @app.get("/api/terms-status")
    def terms_status():
        phone = normalize_phone(str(request.args.get("phone", "")))
        if not phone:
            return jsonify({"status": "empty", "status_label": "Aceite não enviado"}), 200

        state = TERMS_STATE.get(phone)
        if not state:
            return jsonify({"status": "empty", "status_label": "Aceite não enviado"}), 200

        return jsonify(state), 200

    @app.post("/api/send-message")
    def send_message():
        payload = request.get_json(silent=True) or {}
        phone = normalize_phone(str(payload.get("phone", "")))
        message = str(payload.get("message", "")).strip()
        mode = str(payload.get("mode", "text")).strip().lower()
        agenda_data = {
            "client_name": str(payload.get("client_name", "")).strip(),
            "client_address": str(payload.get("client_address", "")).strip(),
            "schedule_date": str(payload.get("schedule_date", "")).strip(),
            "schedule_time": str(payload.get("schedule_time", "")).strip(),
            "service": str(payload.get("service", "")).strip(),
        }

        if mode == "agenda":
            message = build_agenda_message(agenda_data)
        elif mode == "checkin":
            message = build_checkin_message(agenda_data)
        elif mode == "checkin2":
            message = build_checkin2_message(agenda_data)
        elif mode == "terms":
            message = build_terms_message(agenda_data)

        if not phone:
            return jsonify({"ok": False, "error": "Informe um telefone com DDI e DDD."}), 400

        if len(phone) < 10:
            return jsonify({"ok": False, "error": "Telefone muito curto."}), 400

        if not message:
            return jsonify({"ok": False, "error": "Digite uma mensagem."}), 400

        if mode == "terms" and TERMS_STATE.get(phone, {}).get("status") == "accepted":
            return jsonify({"ok": False, "error": "Este contato já aceitou os termos."}), 409

        try:
            if mode == "agenda":
                response_payload = send_zapi_agenda_buttons(phone, message)
            elif mode in {"checkin", "checkin2"}:
                response_payload = send_zapi_checkin_options(
                    phone,
                    message,
                    use_location_link=mode == "checkin2",
                )
            elif mode == "terms":
                response_payload = send_zapi_document(phone, TERMS_PDF_PATH, message)
                send_zapi_terms_buttons(phone)
                TERMS_STATE[phone] = {
                    "phone": phone,
                    "status": "sent",
                    "status_label": "Aguardando aceite",
                    "sent_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                }
            else:
                response_payload = send_zapi_text(phone, message)
        except (RuntimeError, requests.RequestException, ValueError) as exc:
            logger.exception("Erro ao enviar mensagem pela Z-API: %s", exc)
            return jsonify({"ok": False, "error": str(exc)}), 502

        RECEIVED_EVENTS.appendleft(
            {
                "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "payload": {
                    "type": "SentMessage",
                    "phone": phone,
                    "mode": mode,
                    "agenda": agenda_data if mode == "agenda" else {},
                    "text": {"message": message},
                    "response": response_payload,
                },
            }
        )

        if mode in {"agenda", "checkin", "checkin2"}:
            AGENDA_STATE[phone] = {
                "phone": phone,
                "mode": mode,
                "status": "checkin_sent" if mode in {"checkin", "checkin2"} else "pending",
                "status_label": checkin_status_label("checkin_sent") if mode in {"checkin", "checkin2"} else agenda_status_label("pending"),
                "agenda": agenda_data,
                "last_reply": "",
                "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "history": [],
            }

        return jsonify({"ok": True, "response": response_payload}), 200

    return app


def main() -> None:
    global PUBLIC_BASE_URL
    load_dotenv(encoding="utf-8-sig")

    try:
        if os.getenv("LOCAL_ONLY", "").strip() == "1":
            PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://127.0.0.1:{PORT}").strip().rstrip("/")
            logger.info("Modo local ativo. Ngrok/webhook não serão atualizados.")
        elif PUBLIC_BASE_URL:
            logger.info("Usando URL pública configurada: %s", PUBLIC_BASE_URL)
            update_zapi_webhook(PUBLIC_BASE_URL)
        else:
            public_url = start_ngrok_tunnel(PORT)
            PUBLIC_BASE_URL = public_url
            update_zapi_webhook(public_url)

    except (RuntimeError, PyngrokError, requests.RequestException) as exc:
        logger.exception("Falha durante a inicialização: %s", exc)
        sys.exit(1)

    app = create_app()

    logger.info("Servidor Flask iniciado na porta %s", PORT)
    logger.info("URL local: http://127.0.0.1:%s", PORT)
    logger.info("Webhook local: http://127.0.0.1:%s%s", PORT, WEBHOOK_PATH)

    app.run(host="0.0.0.0", port=PORT, use_reloader=False)


if __name__ == "__main__":
    main()
















