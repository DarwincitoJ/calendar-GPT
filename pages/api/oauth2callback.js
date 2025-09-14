const { getOAuth2Client } = require("./auth");
const { kv } = require("@vercel/kv");

module.exports = async function handler(req, res) {
  const client = await getOAuth2Client();
  const code = req.query.code;

  if (!code) {
    const url = client.generateAuthUrl({
      access_type: "offline",
      scope: ["https://www.googleapis.com/auth/calendar"],
    });
    return res.redirect(url);
  }

  const { tokens } = await client.getToken(code);
  await kv.set("google_oauth_tokens", tokens);
  res.status(200).send("✅ Google Calendar connected. You can close this tab.");
};
