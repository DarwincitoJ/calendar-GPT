const { getOAuth2Client, calendar, resolveCalendarId, checkBearer } = require("./auth");

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (!checkBearer(req)) return res.status(403).json({ error: "forbidden" });

  const { title, description = "", start_iso, end_iso, location, calendarNameOrId } = req.body || {};
  if (!title || !start_iso || !end_iso) return res.status(400).json({ error: "missing title/start_iso/end_iso" });

  try {
    const auth = await getOAuth2Client();
    const cal = calendar(auth);
    const calendarId = await resolveCalendarId(cal, calendarNameOrId);

    const body = {
      summary: title,
      description,
      start: { dateTime: start_iso, timeZone: process.env.TIMEZONE },
      end:   { dateTime: end_iso,   timeZone: process.env.TIMEZONE },
      ...(location ? { location } : {})
    };

    const created = await cal.events.insert({ calendarId, requestBody: body });
    res.status(200).json({ eventId: created.data.id, htmlLink: created.data.htmlLink, calendarId });
  } catch (err) {
    console.error("add-event error", err);
    res.status(500).json({ error: "internal_error", detail: String(err) });
  }
}
