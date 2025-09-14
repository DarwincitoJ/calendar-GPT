// pages/api/reset-auth.js
const { kv } = require("@vercel/kv");

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  try {
    await kv.del("google_oauth_tokens");
    res.status(200).json({ status: "cleared" });
  } catch (e) {
    res.status(500).json({ error: "internal_error", detail: String(e) });
  }
}
