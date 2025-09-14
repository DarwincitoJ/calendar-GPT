// pages/api/find-event.js
const { getOAuth2Client, calendar, resolveCalendarId, checkBearer } = require("./auth");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (!checkBearer(req)) return res.status(403).json({ error: "forbidden" });

  const { title, start_date, end_date, calendarNameOrId } = req.body || {};
  if (!title || !start_date || !end_date) {
    return res.status(400).json({ error: "missing title/start_date/end_date" });
  }

  try {
    const auth = await getOAuth2Client();
    const cal = calendar(auth);
    const calendarId = await resolveCalendarId(cal, calendarNameOrId);

    // Build inclusive window [start_date, end_date]
    const start = new Date(`${start_date}T00:00:00Z`);
    const end = new Date(`${end_date}T00:00:00Z`);
    end.setUTCDate(end.getUTCDate() + 1); // make end exclusive at next midnight

    const resp = await cal.events.list({
      calendarId,
      q: title,
      timeMin: start.toISOString(),
      timeMax: end.toISOString(),
      singleEvents: true,
      orderBy: "startTime"
    });

    const events = (resp.data.items || []).map(e => ({
      eventId: e.id,
      summary: e.summary,
      start: e.start,
      end: e.end,
      htmlLink: e.htmlLink
    }));

    return res.status(200).json({ events });
  } catch (err) {
    console.error("find-event error", err);
    return res.status(500).json({ error: "internal_error", detail: String(err) });
  }
};
