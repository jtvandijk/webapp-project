// Fetching and the surname key. surnameKey() must stay in lockstep with pipeline/names.py's
// surname_key(): same input always has to resolve to the same file, on both sides.
// Relative, not "/data": the release sits in a data/ folder next to index.html, so the site works the
// same at a domain root (gbnames.mappingdutchman.com) and under a sub-path (apps.geods.ac.uk/gbnames/).
export const DATA_ROOT = "data";

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

// {area code: human-readable name} for district and MSOA/Intermediate Zone codes (tools/
// build_places_lookup.py) - public ONS/NRS reference data, not part of the TRE export, so it's
// tracked in the repo and served alongside the site's own code, not from DATA_ROOT.
export async function fetchPlacesLookup() {
    const res = await fetch("lookups/places.json");
    if (!res.ok) throw new Error(`lookups/places.json: HTTP ${res.status}`);
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

// "Census 1851" or "SmartCensus 1997" - the one place this naming rule is written, shared by the
// map slider and the bearers table. Every register year says SmartCensus, not just the newest one -
// a separate "Smart Data" label for older register years was exactly the dual-branding confusion
// flagged by the user (2026-10-06).
export function formatPeriod(period) {
    if (period.source === "census") return `Census ${period.id}`;
    return `SmartCensus ${period.id}`;
}

// The estimated (standardised) adult count where one exists, otherwise the raw count - estimation
// only exists for register years (counts_standardised is register-only, per the data contract).
// Register counts are adults only, throughout - unlike census counts, which are everyone.
export function bearersFor(nameData, period) {
    const standardised = nameData.counts_standardised && nameData.counts_standardised[period.source];
    const estimated = standardised ? standardised[period.id] : undefined;
    const raw = (nameData.counts[period.source] || {})[period.id];
    const value = typeof estimated === "number" ? estimated : raw;
    return { value, estimated: typeof estimated === "number" };
}
