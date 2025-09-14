const { getOAuth2Client, calendar, resolveCalendarId, checkBearer } = require("./auth");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (!checkBearer(req)) return res.status(403).json({ error: "forbidden" });

  const { event_id, calendarNameOrId, title, description, location, start_iso, end_iso } = req.body || {};
  if (!event_id) return res.status(400).json({ error: "missing event_id" });

  const auth = await getOAuth2Client();
  const cal = calendar(auth);
  const calendarId = await resolveCalendarId(cal, calendarNameOrId);
  const ev = (await cal.events.get({ calendarId, eventId: event_id })).data;

  if (title !== undefined) ev.summary = title;
  if (description !== undefined) ev.description = description;
  if (location !== undefined) ev.location = location;
  if (start_iso !== undefined) ev.start = { dateTime: start_iso, timeZone: process.env.TIMEZONE };
  if (end_iso !== undefined)   ev.end   = { dateTime: end_iso,   timeZone: process.env.TIMEZONE };

  const updated = await cal.events.update({ calendarId, eventId: event_id, requestBody: ev });
  res.status(200).json({ eventId: updated.data.id, htmlLink: updated.data.htmlLink });
};
