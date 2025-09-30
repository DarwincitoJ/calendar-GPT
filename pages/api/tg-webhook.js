// pages/api/tg-webhook.js
const SECRET = process.env.TG_WEBHOOK_SECRET;
const BOT_TOKEN = process.env.TG_BOT_TOKEN;

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (!SECRET || req.headers["x-telegram-bot-api-secret-token"] !== SECRET) return res.status(401).end();

  const update = req.body || {};
  const msg = update.message || update.edited_message;
  if (!msg) return res.status(200).json({ ok: true });

  const chatId = msg.chat.id;
  const text = (msg.text || "").trim();

  console.log("TG chat_id:", chatId); // check Vercel logs once

  const send = (t) => fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: t })
  });

  if (/^\/start/.test(text)) { await send("Hi! I’m your Family COO bot. Try /plan_today or /list_add milk"); return res.status(200).json({ ok:true }); }
  if (text === "/plan_today") { await send("Today: 3 events. Heads-up: pack water & shoes for basketball."); return res.status(200).json({ ok:true }); }
  if (/^\/list_add\s+/.test(text)) { const item = text.replace(/^\/list_add\s+/, ""); await send(`Added to family list: ${item}`); return res.status(200).json({ ok:true }); }
  await send("Try /plan_today or /list_add milk");
  return res.status(200).json({ ok: true });
}
