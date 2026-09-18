const errText = async (r) => {
  const t = await r.text()
  try {
    const d = JSON.parse(t).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).join('.')}: ${e.msg}`).join('; ')
  } catch { /* not a JSON error body */ }
  return t
}
export async function getJSON(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(await errText(r))
  return r.json()
}
export async function postJSON(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await errText(r))
  return r.json()
}
