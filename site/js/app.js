// Wiring: search box, URL state, welcome/not-found/result panels, the period slider.
import { surnameKey, fetchManifest, fetchName } from "./data.js";
import { createMap } from "./map.js";

const NOT_FOUND_MESSAGE = "No map or statistics for this name: either we found no records, or it "
    + "has fewer than 100 bearers (we do not show these, to protect privacy).";

const searchForm = document.getElementById("searchForm");
const searchInput = document.getElementById("searchInput");
const welcomePanel = document.getElementById("welcomePanel");
const notFoundPanel = document.getElementById("notFoundPanel");
const resultSection = document.getElementById("resultSection");
const resultName = document.getElementById("resultName");
const exampleNames = document.getElementById("exampleNames");
const periodSlider = document.getElementById("periodSlider");
const periodLabel = document.getElementById("periodLabel");
const prevPeriodBtn = document.getElementById("prevPeriod");
const nextPeriodBtn = document.getElementById("nextPeriod");
const closeWelcomeBtn = document.getElementById("closeWelcome");

document.getElementById("notFoundMessage").textContent = NOT_FOUND_MESSAGE;

let manifest = null;
let mapController = null;
let currentName = null;    // the fetched name's own JSON
let currentPeriods = [];   // manifest period entries this name has a map for, in slider order

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

    searchForm.addEventListener("submit", event => {
        event.preventDefault();
        runSearch(searchInput.value);
    });

    periodSlider.addEventListener("input", () => showPeriod(Number(periodSlider.value)));
    prevPeriodBtn.addEventListener("click", () => stepPeriod(-1));
    nextPeriodBtn.addEventListener("click", () => stepPeriod(1));
    closeWelcomeBtn.addEventListener("click", () => { welcomePanel.hidden = true; });
    window.addEventListener("popstate", loadFromUrl);

    loadFromUrl();
}

function loadFromUrl() {
    const name = new URLSearchParams(window.location.search).get("name");
    if (name) {
        searchInput.value = name;
        runSearch(name, { updateUrl: false });
    } else {
        showWelcome();
    }
}

async function runSearch(raw, { updateUrl = true } = {}) {
    const key = surnameKey(raw);
    if (!key) {
        showWelcome();
        return;
    }
    if (updateUrl) {
        const url = new URL(window.location);
        url.searchParams.set("name", key);
        window.history.pushState({}, "", url);
    }

    const nameData = await fetchName(key);
    if (!nameData) {
        showNotFound();
        return;
    }
    showResult(nameData);
}

function showWelcome() {
    welcomePanel.hidden = false;
    notFoundPanel.hidden = true;
    resultSection.hidden = true;
}

function showNotFound() {
    welcomePanel.hidden = true;
    notFoundPanel.hidden = false;
    resultSection.hidden = true;
}

function showResult(nameData) {
    welcomePanel.hidden = true;
    notFoundPanel.hidden = true;
    resultSection.hidden = false;
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

function showPeriod(index, fitBounds = false) {
    const period = currentPeriods[index];
    if (!period) return;
    mapController.renderPeriod(currentName, period.id, fitBounds);

    const bearers = (currentName.counts[period.source] || {})[period.id];
    const bearersText = typeof bearers === "number" ? bearers.toLocaleString("en-GB") : "unknown";
    periodLabel.textContent = `${period.id} (${period.source}) — ${bearersText} bearers`;
}

init();
