// Wiring: search boxes, URL state, welcome/not-found/result panels, the period slider.
import { surnameKey, fetchManifest, fetchName } from "./data.js";
import { createMap } from "./map.js";

const NOT_FOUND_MESSAGE = "No map or statistics for this name: either we found no records, or it "
    + "has fewer than 100 bearers (we do not show these, to protect privacy).";

const welcomePanel = document.getElementById("welcomePanel");
const notFoundPanel = document.getElementById("notFoundPanel");
const resultSection = document.getElementById("resultSection");
const resultName = document.getElementById("resultName");
const exampleNames = document.getElementById("exampleNames");
const sliderWrapper = document.getElementById("sliderWrapper");
const periodSlider = document.getElementById("periodSlider");
const periodLabel = document.getElementById("periodLabel");
const periodNote = document.getElementById("periodNote");
const prevPeriodBtn = document.getElementById("prevPeriod");
const nextPeriodBtn = document.getElementById("nextPeriod");
const closeWelcomeBtn = document.getElementById("closeWelcome");
const navSearchWrapper = document.getElementById("navSearchWrapper");

document.getElementById("notFoundMessage").textContent = NOT_FOUND_MESSAGE;

let manifest = null;
let mapController = null;
let currentName = null;    // the fetched name's own JSON
let currentPeriods = [];   // manifest period entries this name has a map for, in slider order

// "welcome" (first visit), "idle" (welcome dismissed, nothing searched), "notfound" or "result".
function setMode(mode) {
    welcomePanel.hidden = mode !== "welcome";
    notFoundPanel.hidden = mode !== "notfound";
    resultSection.hidden = mode !== "result";
    sliderWrapper.hidden = mode !== "result";
    resultName.hidden = mode !== "result";
    navSearchWrapper.hidden = mode === "welcome";
}

function wireSearchForm(form, input) {
    form.addEventListener("submit", event => {
        event.preventDefault();
        runSearch(input.value);
    });
}

async function init() {
    manifest = await fetchManifest();
    mapController = createMap(document.getElementById("map"), manifest);

    for (const name of manifest.examples) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "example-chip";
        chip.textContent = name;
        chip.addEventListener("click", () => runSearch(name));
        exampleNames.appendChild(chip);
    }

    wireSearchForm(document.getElementById("searchFormJumbo"), document.getElementById("searchInputJumbo"));
    wireSearchForm(document.getElementById("searchFormNav"), document.getElementById("searchInputNav"));

    periodSlider.addEventListener("input", () => showPeriod(Number(periodSlider.value)));
    prevPeriodBtn.addEventListener("click", () => stepPeriod(-1));
    nextPeriodBtn.addEventListener("click", () => stepPeriod(1));
    closeWelcomeBtn.addEventListener("click", () => setMode("idle"));
    window.addEventListener("popstate", loadFromUrl);

    loadFromUrl();
}

function loadFromUrl() {
    const name = new URLSearchParams(window.location.search).get("name");
    if (name) {
        document.getElementById("searchInputJumbo").value = name;
        document.getElementById("searchInputNav").value = name;
        runSearch(name, { updateUrl: false });
    } else {
        setMode("welcome");
    }
}

async function runSearch(raw, { updateUrl = true } = {}) {
    const key = surnameKey(raw);
    if (!key) {
        setMode("welcome");
        return;
    }
    if (updateUrl) {
        const url = new URL(window.location);
        url.searchParams.set("name", key);
        window.history.pushState({}, "", url);
    }
    document.getElementById("searchInputJumbo").value = key;
    document.getElementById("searchInputNav").value = key;

    const nameData = await fetchName(key);
    if (!nameData) {
        setMode("notfound");
        return;
    }
    showResult(nameData);
}

function showResult(nameData) {
    setMode("result");
    mapController.map.invalidateSize();

    currentName = nameData;
    currentPeriods = manifest.periods.filter(p => nameData.maps[p.id]);
    resultName.textContent = nameData.name;

    const lastIndex = Math.max(currentPeriods.length - 1, 0);
    periodSlider.min = 0;
    periodSlider.max = lastIndex;
    periodSlider.value = lastIndex;    // most recent period first
    showPeriod(lastIndex, true);
}

function stepPeriod(delta) {
    const next = Math.min(Math.max(Number(periodSlider.value) + delta, 0), currentPeriods.length - 1);
    periodSlider.value = next;
    showPeriod(next);
}

// "Census 1851", "SmartCensus 2026" (the newest register year, the actual new survey), or
// "Smart Data: 1997" (every other, pre-existing register year).
function formatPeriod(period) {
    if (period.source === "census") return `Census ${period.id}`;
    if (period.id === manifest.standardisation.base_year) return `SmartCensus ${period.id}`;
    return `Smart Data: ${period.id}`;
}

function showPeriod(index, fitBounds = false) {
    const period = currentPeriods[index];
    if (!period) return;
    mapController.renderPeriod(currentName, period.id, fitBounds);

    // the adjusted (standardised) count where we have one, otherwise the raw count - adjustment
    // only exists for register years (counts_standardised is register-only, per the data contract).
    const standardised = currentName.counts_standardised && currentName.counts_standardised[period.source];
    const adjusted = standardised ? standardised[period.id] : undefined;
    const raw = (currentName.counts[period.source] || {})[period.id];
    const bearers = typeof adjusted === "number" ? adjusted : raw;
    const bearersText = typeof bearers === "number" ? bearers.toLocaleString("en-GB") : "unknown";
    periodLabel.textContent = `${formatPeriod(period)} — ${bearersText} bearers`;

    const geojson = currentName.maps[period.id];
    if (geojson && geojson.copyOf) {
        periodNote.textContent = `This map shows ${geojson.copyOf} data: census data for Scotland are `
            + `not available for ${period.id}, so this name's ${geojson.copyOf} map is shown instead.`;
        periodNote.hidden = false;
    } else {
        periodNote.hidden = true;
    }
}

init();
