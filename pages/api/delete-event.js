const { getOAuth2Client, calendar, resolveCalendarId, checkBearer } = require("./auth");

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (!checkBearer(req)) return res.status(403).json({ error: "forbidden" });

  const { event_id, calendarNameOrId } = req.body || {};
  if (!event_id) return res.status(400).json({ error: "missing event_id" });

  try {
    const auth = await getOAuth2Client();
    const cal = calendar(auth);
    const calendarId = await resolveCalendarId(cal, calendarNameOrId);

    await cal.events.delete({ calendarId, eventId: event_id });
    res.status(200).json({ status: "deleted", eventId: event_id });
  } catch (err) {
    console.error("delete-event error", err);
    res.status(500).json({ error: "internal_error", detail: String(err) });
  }
}
