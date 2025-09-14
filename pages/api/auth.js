const { google } = require("googleapis");
const { kv } = require("@vercel/kv");

const SCOPES = ["https://www.googleapis.com/auth/calendar"];

async function getOAuth2Client() {
  const client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    process.env.OAUTH_REDIRECT_URI
  );

  const tokens = await kv.get("google_oauth_tokens");
  if (tokens) client.setCredentials(tokens);

  client.on("tokens", async (t) => {
    const prev = (await kv.get("google_oauth_tokens")) || {};
    await kv.set("google_oauth_tokens", { ...prev, ...t });
  });

  return client;
}

function calendar(client) {
  return google.calendar({ version: "v3", auth: client });
}

async function resolveCalendarId(cal, nameOrId) {
  const fallback = process.env.DEFAULT_CAL_NAME || "primary";
  const target = nameOrId || fallback;
  if (target.includes("@")) return target; // looks like an ID
  const list = await cal.calendarList.list();
  const items = list.data.items || [];
  const match = items.find(
    (i) => (i.summary || "").trim().toLowerCase() === target.trim().toLowerCase()
  );
  return (match && match.id) || "primary";
}

function checkBearer(req) {
  return req.headers.authorization === `Bearer ${process.env.API_BEARER_TOKEN}`;
}

module.exports = { getOAuth2Client, calendar, resolveCalendarId, checkBearer };
