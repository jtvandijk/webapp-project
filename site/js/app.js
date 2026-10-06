// Wiring: search boxes, URL state, welcome/not-found/result panels, the period slider, the
// indicator cards.
import { surnameKey, fetchManifest, fetchLookups, fetchPlacesLookup, fetchName, fetchFacts, formatPeriod, bearersFor } from "./data.js";
import { createMap } from "./map.js";
import { renderDecileCard, renderGroupCard, renderFlatGroupCard, colourPill } from "./indicators.js";
import { renderPlacesCard, renderForenamesCard, renderEthnicityCard, renderCountsCard } from "./profile.js";

const NOT_FOUND_MESSAGE = "We couldn't find a page for this surname. This means either we hold no "
    + "records for it, or fewer than 100 people in our data share it — too few to show without "
    + "risking anyone's privacy.";

// Every other place a found name's display form is shown uses .textContent (inherently safe); this
// is the one spot it goes into innerHTML (the IMD score sentence), so it needs its own escaping.
function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function decilePill(decile, colour) {
    return colourPill(`Decile ${decile}`, colour);
}

// Real GeoDS fliers (two-page PDF leaflets) exist for some, not all, indicators - IMD and FPC don't
// have one yet, so those cards just omit the `flier` key entirely.
const FLIERS = {
    oac: { pdf: "fliers/oac.pdf", thumb: "fliers/thumbs/oac.png" },
    loac: { pdf: "fliers/loac.pdf", thumb: "fliers/thumbs/loac.png" },
    gb2c: { pdf: "fliers/gb2c.pdf", thumb: "fliers/thumbs/gb2c.png" },
    ahah: { pdf: "fliers/ahah.pdf", thumb: "fliers/thumbs/ahah.png" },
};

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
const indicatorContainer = document.getElementById("indicatorContainer");
const moreAboutContainer = document.getElementById("moreAboutContainer");

document.getElementById("notFoundMessage").textContent = NOT_FOUND_MESSAGE;

let manifest = null;
let lookups = null;
let placesLookup = null;
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
    [manifest, lookups, placesLookup] = await Promise.all([fetchManifest(), fetchLookups(), fetchPlacesLookup()]);
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
    const facts = await fetchFacts(key);
    showResult(nameData, facts);
}

function showResult(nameData, facts) {
    setMode("result");
    mapController.map.invalidateSize();

    currentName = nameData;
    currentPeriods = manifest.periods.filter(p => nameData.maps[p.id]);
    resultName.textContent = nameData.name;

    periodSlider.min = 0;
    periodSlider.max = Math.max(currentPeriods.length - 1, 0);
    periodSlider.value = 0;    // earliest period first
    showPeriod(0, true);

    renderIndicators(facts);
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

    const { value, estimated } = bearersFor(currentName, period);
    const bearersText = typeof value === "number" ? value.toLocaleString("en-GB") : "unknown";
    const bearersWord = estimated ? "estimated adult bearers" : "bearers";
    periodLabel.textContent = `${formatPeriod(period)} — ${bearersText} ${bearersWord}`;

    const geojson = currentName.maps[period.id];
    if (geojson && geojson.copyOf) {
        periodNote.textContent = `This map shows ${geojson.copyOf} data: census data for Scotland are `
            + `not available for ${period.id}, so this name's ${geojson.copyOf} map is shown instead.`;
        periodNote.hidden = false;
    } else {
        periodNote.hidden = true;
    }
}

// Indicator order, per the agreed page layout: KDE map (above) > IMD > OAC > LOAC > GB2C > AHAH >
// FPC > "more about your name" (places, forenames, ethnicity, counts).
function renderIndicators(facts) {
    indicatorContainer.replaceChildren();
    moreAboutContainer.replaceChildren();

    // nameEscaped: plain text, for sentences that just bold the searched name inline (e.g. the
    // Supergroup-mismatch callout, which already has its own colour pills for the Supergroups).
    // namePill: the full pill treatment, for the IMD score sentence specifically ("For {name}, it
    // averages...") - everywhere else that mentions "your selected surname" stays plain text, per
    // the user's call that pills on every mention felt like too much (2026-10-06).
    const nameEscaped = escapeHtml(currentName.name);
    const namePill = `<span class="name-pill">${nameEscaped}</span>`;

    if (facts.imd) {
        indicatorContainer.appendChild(renderDecileCard({
            title: lookups.cards.imd.title,
            about: lookups.cards.imd.about,
            colours: lookups.scales.imd.colours,
            distribution: facts.imd.distribution,
            mode: facts.imd.mode,
            scaleText: lookups.scales.imd.text
                .replace("{decile}", decilePill(facts.imd.mode, lookups.scales.imd.colours[facts.imd.mode - 1])),
            scoreText: lookups.cards.imd.score
                && lookups.cards.imd.score.replace("{name}", namePill)
                    .replace("{mean}", facts.imd.mean).replace("{sd}", facts.imd.sd),
        }));
    }
    if (facts.oac) {
        indicatorContainer.appendChild(renderGroupCard({
            title: lookups.cards.oac.title,
            about: lookups.cards.oac.about,
            groups: lookups.oac.groups,
            supergroups: lookups.oac.supergroups,
            distribution: facts.oac.distribution,
            modeCode: facts.oac.group,
            clickHint: "neighbourhood characteristics",
            flier: FLIERS.oac,
            name: nameEscaped,
            abbr: "OAC",
        }));
    }
    if (facts.loac) {
        indicatorContainer.appendChild(renderGroupCard({
            title: lookups.cards.loac.title,
            about: lookups.cards.loac.about,
            groups: lookups.loac.groups,
            supergroups: lookups.loac.supergroups,
            distribution: facts.loac.distribution,
            modeCode: facts.loac.group,
            clickHint: "neighbourhood characteristics",
            flier: FLIERS.loac,
            name: nameEscaped,
            abbr: "LOAC",
        }));
    }
    if (facts.gb2c) {
        indicatorContainer.appendChild(renderFlatGroupCard({
            title: lookups.cards.gb2c.title,
            about: lookups.cards.gb2c.about,
            groups: lookups.gb2c.groups,
            distribution: facts.gb2c.distribution,
            modeCode: facts.gb2c.group,
            clickHint: "gambling behaviour characteristics",
            flier: FLIERS.gb2c,
        }));
    }
    if (facts.ahah) {
        indicatorContainer.appendChild(renderDecileCard({
            title: lookups.cards.ahah.title,
            about: lookups.cards.ahah.about,
            colours: lookups.scales.ahah.colours,
            distribution: facts.ahah.distribution,
            mode: facts.ahah.mode,
            scaleText: lookups.scales.ahah.text
                .replace("{decile}", decilePill(facts.ahah.mode, lookups.scales.ahah.colours[facts.ahah.mode - 1])),
            flier: FLIERS.ahah,
        }));
    }
    if (facts.fpc) {
        indicatorContainer.appendChild(renderGroupCard({
            title: lookups.cards.fpc.title,
            about: lookups.cards.fpc.about,
            groups: lookups.fpc.groups,
            supergroups: lookups.fpc.supergroups,
            distribution: facts.fpc.distribution,
            modeCode: facts.fpc.group,
            clickHint: "neighbourhood characteristics",
            name: nameEscaped,
            abbr: "FPC",
        }));
    }

    moreAboutContainer.appendChild(renderPlacesCard({ places: facts.places, placesLookup }));
    moreAboutContainer.appendChild(renderForenamesCard({ forenames: facts.forenames }));
    if (facts.eth) {
        moreAboutContainer.appendChild(renderEthnicityCard({
            eth: facts.eth, ethLookup: lookups.eth, about: lookups.cards.eth.about,
        }));
    }
    moreAboutContainer.appendChild(renderCountsCard({ nameData: currentName, manifest }));
}

init();
