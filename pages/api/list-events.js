// pages/api/list-events.js
const { getOAuth2Client, calendar, resolveCalendarId, checkBearer } = require("./auth");

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (!checkBearer(req)) return res.status(403).json({ error: "forbidden" });

  const { start_date, end_date, calendarNameOrId } = req.body || {};
  if (!start_date || !end_date) {
    return res.status(400).json({ error: "missing start_date/end_date (YYYY-MM-DD)" });
  }

  try {
    const auth = await getOAuth2Client();
    const cal = calendar(auth);
    const calendarId = await resolveCalendarId(cal, calendarNameOrId);

    const start = new Date(`${start_date}T00:00:00Z`);
    const end = new Date(`${end_date}T00:00:00Z`);
    end.setUTCDate(end.getUTCDate() + 1); // include entire end day

    const resp = await cal.events.list({
      calendarId,
      timeMin: start.toISOString(),
      timeMax: end.toISOString(),
      singleEvents: true,
      orderBy: "startTime",
      maxResults: 2500,
    });

    const events = (resp.data.items || []).map(e => ({
      eventId: e.id,
      summary: e.summary,
      start: e.start, // contains date or dateTime
      end: e.end,
      location: e.location,
      htmlLink: e.htmlLink,
    }));

    res.status(200).json({ events });
  } catch (err) {
    console.error("list-events error", err);
    res.status(500).json({ error: "internal_error", detail: String(err) });
  }
}
