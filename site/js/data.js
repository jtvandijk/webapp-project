// Fetching and the surname key. surnameKey() must stay in lockstep with pipeline/names.py's
// surname_key(): same input always has to resolve to the same file, on both sides.
export const DATA_ROOT = "/data";

const PLACEHOLDERS = new Set(["", "xxxx", "nan", "null", "none", "unknown"]);

export function surnameKey(raw) {
    if (raw == null) return "";
    const stripped = raw.toString().normalize("NFKD").replace(/[̀-ͯ]/g, "");
    const key = stripped.toLowerCase().replace(/[^a-z]+/g, "");
    return PLACEHOLDERS.has(key) ? "" : key;
}

export async function fetchManifest() {
    const res = await fetch(`${DATA_ROOT}/manifest.json`);
    if (!res.ok) throw new Error(`manifest.json: HTTP ${res.status}`);
    return res.json();
}

export async function fetchLookups() {
    const res = await fetch(`${DATA_ROOT}/lookups.json`);
    if (!res.ok) throw new Error(`lookups.json: HTTP ${res.status}`);
    return res.json();
}

// null means "no file for this name" (not found, or below the publish threshold) - not an error.
export async function fetchName(key) {
    const res = await fetch(`${DATA_ROOT}/names/${key.slice(0, 2)}/${key}.json`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`names/${key}.json: HTTP ${res.status}`);
    return res.json();
}

// A name's facts are published separately from its counts/maps (tools/split_facts.py) - missing
// entirely (404) is expected for a name below the facts threshold even if it has a map, and for
// any fact key a name simply has no data for (both are "nothing to show", not an error).
export async function fetchFacts(key) {
    const res = await fetch(`${DATA_ROOT}/facts/${key.slice(0, 2)}/${key}.json`);
    if (res.status === 404) return {};
    if (!res.ok) throw new Error(`facts/${key}.json: HTTP ${res.status}`);
    return res.json();
}

// "Census 1851", "SmartCensus 2026" (the newest register year, the actual new survey), or
// "Smart Data: 1997" (every other, pre-existing register year) - the one place this naming rule
// is written, shared by the map slider and the bearers table.
export function formatPeriod(period, manifest) {
    if (period.source === "census") return `Census ${period.id}`;
    if (period.id === manifest.standardisation.base_year) return `SmartCensus ${period.id}`;
    return `Smart Data: ${period.id}`;
}

// The adjusted (standardised) count where one exists, otherwise the raw count - adjustment only
// exists for register years (counts_standardised is register-only, per the data contract).
export function bearersFor(nameData, period) {
    const standardised = nameData.counts_standardised && nameData.counts_standardised[period.source];
    const adjusted = standardised ? standardised[period.id] : undefined;
    const raw = (nameData.counts[period.source] || {})[period.id];
    const value = typeof adjusted === "number" ? adjusted : raw;
    return { value, adjusted: typeof adjusted === "number" };
}
