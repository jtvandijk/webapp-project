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

// null means "no file for this name" (not found, or below the publish threshold) - not an error.
export async function fetchName(key) {
    const res = await fetch(`${DATA_ROOT}/names/${key.slice(0, 2)}/${key}.json`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`names/${key}.json: HTTP ${res.status}`);
    return res.json();
}
