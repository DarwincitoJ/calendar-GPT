// pages/api/oauth2callback.js
const { getOAuth2Client } = require("./auth");
const { kv } = require("@vercel/kv");

/**
 * Starts/finishes the Google OAuth flow and stores tokens in KV.
 * - If no `code` is present, redirects to Google's consent screen.
 * - On return, exchanges the code for tokens and saves them.
 * - Always requests a refresh_token (prompt: "consent", access_type: "offline").
 */
export default async function handler(req, res) {
  try {
    const client = await getOAuth2Client();
    const { code } = req.query || {};

    // Step 1: kick off OAuth
    if (!code) {
      const url = client.generateAuthUrl({
        access_type: "offline",
        prompt: "consent", // IMPORTANT: ensures Google returns refresh_token
        scope: ["https://www.googleapis.com/auth/calendar"],
      });
      return res.redirect(url);
    }

    // Step 2: handle Google's redirect, exchange code for tokens
    const { tokens } = await client.getToken(code);

    // If Google didn't return a refresh_token this time, keep any existing one
    if (!tokens.refresh_token) {
      const existing = await kv.get("google_oauth_tokens");
      if (existing?.refresh_token) tokens.refresh_token = existing.refresh_token;
    }

    await kv.set("google_oauth_tokens", tokens);
    return res
      .status(200)
      .send("✅ Google Calendar connected. You can close this tab.");
  } catch (err) {
    console.error("oauth2callback error", err);
    return res
      .status(500)
      .json({ error: "internal_error", detail: String(err) });
  }
}
