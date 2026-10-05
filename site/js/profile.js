// "More about your name": places, forenames, ethnicity (modal value only) and the bearers-over-time
// table - everything that isn't a neighbourhood classification (see indicators.js for those).
import { formatPeriod, bearersFor } from "./data.js";
import { cardShell, barRow } from "./indicators.js";

export function renderPlacesCard({ places, placesLookup }) {
    const { card, body } = cardShell({
        title: "Where your name is found",
        about: "The counties and parishes your name was most often recorded in historically, and the "
            + "areas it is most concentrated in today.",
    });
    const row = document.createElement("div");
    row.className = "row";
    row.appendChild(placesColumn("Historic Census", places && places.census, null));
    row.appendChild(placesColumn("SmartData", places && places.register, placesLookup));
    body.appendChild(row);
    return card;
}

// Historic Census places already come as real names (e.g. "London" / "London parishes"). SmartData
// places come as district/MSOA GSS codes (tools/split_facts.py), resolved here via
// tools/build_places_lookup.py's lookup - falling back to the raw code on the rare miss.
function placesColumn(heading, items, placesLookup) {
    const col = document.createElement("div");
    col.className = "col-md-6";
    col.innerHTML = `<h6 class="text-muted">${heading}</h6>`;
    if (!items || !items.length) {
        col.innerHTML += `<p class="text-muted small mb-0">No data available.</p>`;
        return col;
    }
    const list = document.createElement("div");
    list.className = "places-list";
    for (const item of items.slice(0, 5)) {
        const area = (placesLookup && placesLookup[item.area]) || item.area;
        const name = (placesLookup && placesLookup[item.name]) || item.name;
        const chip = document.createElement("div");
        chip.className = "place-chip";
        chip.innerHTML = `<span class="place-area">${area} —</span> ${name}`;
        list.appendChild(chip);
    }
    col.appendChild(list);
    return col;
}

export function renderForenamesCard({ forenames }) {
    const { card, body } = cardShell({ title: "Forenames",
        about: "The most common forenames recorded alongside your surname." });
    const row = document.createElement("div");
    row.className = "row";
    row.appendChild(forenameColumn("Historic Census", forenames && forenames.census));
    row.appendChild(forenameColumn("SmartData", forenames && forenames.register));
    body.appendChild(row);
    return card;
}

function forenameColumn(heading, data) {
    const col = document.createElement("div");
    col.className = "col-md-6";
    col.innerHTML = `<h6 class="text-muted">${heading}</h6>`;
    if (!data) {
        col.innerHTML += `<p class="text-muted small mb-0">No data available.</p>`;
        return col;
    }
    for (const [label, names] of [["Female", data.f], ["Male", data.m]]) {
        const sub = document.createElement("div");
        sub.className = "mb-2";
        sub.innerHTML = `<div class="small text-muted">${label}</div>`;
        const pills = document.createElement("div");
        pills.className = "forename-pills";
        for (const name of (names || []).slice(0, 10)) {
            const span = document.createElement("span");
            span.className = `forename-pill forename-pill-${label.toLowerCase()}`;
            span.textContent = name;
            pills.appendChild(span);
        }
        sub.appendChild(pills);
        col.appendChild(sub);
    }
    return col;
}

export function renderEthnicityCard({ eth, ethLookup, about }) {
    const { card, body } = cardShell({ title: "Ethnicity Estimator", about });
    const code = eth && eth.group;
    const info = (ethLookup && ethLookup[code]) || null;
    if (!info) {
        body.innerHTML += `<p class="text-muted small mb-0">No data available.</p>`;
        return card;
    }
    const pill = document.createElement("span");
    pill.className = "eth-pill";
    pill.style.background = info.colour;
    pill.textContent = info.name;
    body.appendChild(pill);
    return card;
}

// Census = light blue, SmartData/SmartCensus = navy, so the source is obvious at a glance - the
// same light blue as manifest.levels' own level-1 KDE colour, reused rather than inventing a new one.
const CENSUS_COLOUR = "#6baed6";
const SMARTDATA_COLOUR = "#1f428f";

export function renderCountsCard({ nameData, manifest }) {
    const { card, body } = cardShell({ title: "Number of Bearers",
        about: "How many people have shared your name, in each year we have data for. Census counts "
            + "(light blue) are everyone recorded that year. Modern SmartData/SmartCensus counts (navy) "
            + "are estimated against the dataset's own adult population each year, so its growth over "
            + "time doesn't look like your name becoming more common." });
    const list = document.createElement("div");
    list.className = "bar-list";
    const entries = manifest.periods
        .map(period => ({ period, ...bearersFor(nameData, period) }))
        .filter(e => typeof e.value === "number");
    const maxValue = Math.max(1, ...entries.map(e => e.value));
    for (const { period, value, estimated } of entries) {
        const row = barRow({
            name: formatPeriod(period, manifest) + (estimated ? " (estimated)" : ""),
            colour: period.source === "census" ? CENSUS_COLOUR : SMARTDATA_COLOUR,
            share: value / maxValue,
            valueText: value.toLocaleString("en-GB"),
        });
        list.appendChild(row);
    }
    body.appendChild(list);
    return card;
}
