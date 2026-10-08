// Rendering for the neighbourhood-classification indicator cards.
// - IMD / AHAH: a fixed 10-decile bar chart (renderDecileCard).
// - OAC / LOAC / FPC: a genuine two-level structure - every supergroup (fixed canonical order,
//   official pen-portrait text behind a click on the name), then just the groups inside this name's
//   own modal supergroup, shown as a share WITHIN that supergroup (renderGroupCard).
// - GB2C: a flat list of its 11 groups, same bar style and pen portraits, but no supergroup level -
//   BG/B/G aren't a meaningful higher-level category the way OAC/LOAC/FPC's supergroups are, just a
//   naming prefix, so the classification is shown as given, group by group (renderFlatGroupCard).

function pct(share) {
    return `${(share * 100).toFixed(1)}%`;
}

// ---- Index view (OAC/LOAC/FPC/GB2C only; agreed with the user 2026-10-08) -------------------------
// A second way to read a group card: instead of each group's share of the name's bearers, its INDEX -
// 100 x (name's share) / (population's share), the population share being the same one the share
// view's tick marks use (lookups.json populationShare). 100 = as common among bearers as in the
// population, 200 = twice as common, 50 = half. Shares stay the default; a "Shares | Index" switch on
// each card flips every card at once (a class on <html>, so nothing is re-drawn) and the browser
// remembers the choice. Every bar row carries both views; CSS shows one. IMD/AHAH are left out on
// purpose: deciles are ~10% of areas each by construction, so their share chart already reads as an
// index against a flat line. To retire the feature, set INDEX_VIEW_ENABLED = false: no switch is
// drawn and every card stays on shares.
const INDEX_VIEW_ENABLED = true;
const VIEW_STORAGE_KEY = "gbnames.groupView";
// Drawn on a log2 scale centred on 100, so 50 and 200 sit the same distance either side; bars stop
// at 25 and 400 (INDEX_SCALE_STEPS doublings) while the printed number is always the real one.
const INDEX_SCALE_STEPS = 2;

let groupView = "share";
try {
    if (INDEX_VIEW_ENABLED && window.localStorage.getItem(VIEW_STORAGE_KEY) === "index") groupView = "index";
} catch (e) { /* storage blocked (private mode etc.) - just start on shares */ }

function applyGroupView() {
    document.documentElement.classList.toggle("group-view-index", groupView === "index");
    document.querySelectorAll(".view-toggle button").forEach(btn => {
        btn.setAttribute("aria-pressed", String(btn.dataset.view === groupView));
    });
}
applyGroupView();

function setGroupView(view) {
    groupView = view;
    try { window.localStorage.setItem(VIEW_STORAGE_KEY, view); } catch (e) { /* not remembered, fine */ }
    applyGroupView();
}

function indexOf(share, populationShare) {
    return populationShare ? 100 * share / populationShare : null;
}

// One line on how to read the view that is showing and, under it (directly above the bars), the
// right-aligned "Shares | Index" switch. The shares line replaced the tick-mark sentence each card's own description used to carry
// (user, 2026-10-08), so it is drawn even with INDEX_VIEW_ENABLED off (then without the switch).
// `population` names the baseline in words ("the UK population", "London's population", ...);
// `twoLevel` adds the note that Group bars are shares within the Supergroup shown.
function viewControls(population, twoLevel) {
    const wrap = document.createElement("div");
    wrap.className = "view-toggle-row";
    const shareExplainer = document.createElement("p");
    shareExplainer.className = "indicator-text view-explainer share-only";
    shareExplainer.textContent = "Shares: the percentage of this name's bearers living in each "
        + (twoLevel ? "Supergroup's or Group's neighbourhoods (for Groups, within the Supergroup shown). "
            : "group's neighbourhoods. ")
        + `The black tick shows the same for ${population}: a bar reaching past its tick means the name is `
        + "over-represented there.";
    const indexExplainer = document.createElement("p");
    indexExplainer.className = "indicator-text view-explainer index-only";
    indexExplainer.textContent = `Index: how common each group is among bearers of this name, compared with ${population}. `
        + "100 means as common, 200 twice as common, 50 half as common. Bars to the right of the centre line "
        + "are over-represented, to the left under-represented (drawn from 25 to 400).";
    if (!INDEX_VIEW_ENABLED) {
        wrap.append(shareExplainer);
        return wrap;
    }
    const toggle = document.createElement("div");
    toggle.className = "view-toggle";
    toggle.setAttribute("role", "group");
    toggle.setAttribute("aria-label", "Show the groups as shares or as index values");
    toggle.innerHTML = `<span class="view-toggle-label">Show as</span>`;
    for (const [view, text] of [["share", "Shares"], ["index", "Index"]]) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.view = view;
        btn.textContent = text;
        btn.setAttribute("aria-pressed", String(view === groupView));
        btn.addEventListener("click", () => setGroupView(view));
        toggle.appendChild(btn);
    }
    wrap.append(shareExplainer, indexExplainer, toggle);   // switch last: directly above the bars it controls
    return wrap;
}

function indexTrack(index, colour) {
    if (index == null) return `<span class="index-track index-only"><span class="index-axis"></span></span>`;
    const steps = index <= 0 ? -INDEX_SCALE_STEPS
        : Math.max(-INDEX_SCALE_STEPS, Math.min(INDEX_SCALE_STEPS, Math.log2(index / 100)));
    const half = Math.abs(steps) / INDEX_SCALE_STEPS * 50;
    const left = steps >= 0 ? 50 : 50 - half;
    const title = index <= 0 ? "No bearers of this name in this group"
        : `Index ${Math.round(index)}: ${(index / 100).toFixed(2)} times as common as in the population`;
    return `<span class="index-track index-only" title="${title}">`
        + `<span class="index-fill" style="left:${left}%;width:${half}%;background:${colour}"></span>`
        + `<span class="index-axis"></span></span>`;
}

// Deciles/Supergroups/Groups span dark reds/greens through very light yellows (see IMD_COLOURS/
// AHAH_COLOURS/OAC and friends in tools/build_lookups.py) - a solid-fill pill needs black text on
// the light end and white on the dark end, not one fixed colour. Standard YIQ brightness formula.
export function contrastText(hex) {
    const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 >= 128 ? "#1a1a1a" : "#fff";
}

// A pill filled with its own colour (a decile, a Supergroup, a Group...), text colour computed to
// stay readable against it.
export function colourPill(text, colour) {
    return `<span class="colour-pill" style="background:${colour};color:${contrastText(colour)}">${text}</span>`;
}

// share (0-1) always drives the bar's width; valueText overrides what's printed (e.g. a raw count)
// when the row isn't itself a percentage of 100%, like the bearers-over-time table in profile.js.
// populationShare (0-1), when given, draws a thin tick mark on the track at that position - what
// share of the real population falls in this group, on the SAME share-space as `share` itself, so a
// name's bar falling short of/past the tick means under-/over-represented there.
// `index`, when given (a number, or null for "no population share known"), adds the index view's
// value and bar next to the share ones; CSS shows one pair or the other (see INDEX_VIEW_ENABLED).
export function barRow({ name, colour, share, valueText, detailsText, populationShare, index }) {
    const widthPct = pct(share);
    const text = valueText != null ? valueText : widthPct;
    const withIndex = INDEX_VIEW_ENABLED && index !== undefined;
    const shareOnly = withIndex ? " share-only" : "";
    const chevron = detailsText ? `<span class="bar-chevron" aria-hidden="true">&#9656;</span>` : "";
    const baseline = populationShare != null
        ? `<span class="bar-baseline" style="left:${pct(populationShare)}" title="${pct(populationShare)} of the population"></span>`
        : "";
    const label = `
        <span class="bar-label">
            ${chevron}
            <span class="bar-swatch" style="background:${colour}"></span>
            <span class="bar-name">${name}</span>
            <span class="bar-pct${shareOnly}">${text}</span>
            ${withIndex ? `<span class="bar-pct index-only">${index == null ? "–" : Math.round(index)}</span>` : ""}
        </span>
        <span class="bar-track${shareOnly}"><span class="bar-fill" style="width:${widthPct};background:${colour}"></span>${baseline}</span>
        ${withIndex ? indexTrack(index, colour) : ""}`;

    if (detailsText) {
        const details = document.createElement("details");
        details.className = "bar-row bar-row-expandable";
        const summary = document.createElement("summary");
        summary.innerHTML = label;
        const body = document.createElement("div");
        body.className = "pen-portrait";
        body.style.borderLeftColor = colour;
        body.textContent = detailsText;
        details.append(summary, body);
        return details;
    }
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = label;
    return row;
}

// `about` is HTML, not plain text - lookups.json's own card text (build_lookups.py), never user
// input, so this is safe - it's how each card's real citation links render. about + clickHint (if
// given) sit in the same paragraph, in their own tinted box set apart from the bars below. `flier`,
// when given ({pdf, thumb}), adds the real GeoDS flier's cover thumbnail to the left of that text,
// linking out to the PDF - the old site's flier-thumbnail-alongside-text treatment, for the
// classifications that actually have one (not every indicator does).
export function cardShell({ title, about, clickHint, flier }) {
    const card = document.createElement("div");
    card.className = "card mb-3 indicator-card";
    card.innerHTML = `<div class="card-header"><h4 class="m-0">${title}</h4></div>`;
    const body = document.createElement("div");
    body.className = "card-body";
    if (about || clickHint) {
        const box = document.createElement("div");
        box.className = "indicator-about-box" + (flier ? " indicator-about-box-with-flier" : "");
        if (flier) {
            const a = document.createElement("a");
            a.href = flier.pdf;
            a.target = "_blank";
            a.rel = "noopener";
            a.className = "flier-thumb-link";
            a.title = `Open the ${title} flier (PDF)`;
            const img = document.createElement("img");
            img.src = flier.thumb;
            img.alt = `${title} flier cover`;
            img.className = "flier-thumb";
            a.appendChild(img);
            box.appendChild(a);
        }
        const textWrap = document.createElement("div");
        textWrap.className = "indicator-about-text";
        const p = document.createElement("p");
        p.className = "indicator-text";
        let html = about || "";
        if (clickHint) {
            html += (html ? " " : "") + `Click on any label to find out its ${clickHint}.`;
        }
        p.innerHTML = html;
        textWrap.appendChild(p);
        box.appendChild(textWrap);
        body.appendChild(box);
    }
    card.appendChild(body);
    return { card, body };
}

export function renderDecileCard({ title, about, colours, distribution, mode, scaleText, scoreText, flier }) {
    const { card, body } = cardShell({ title, about, flier });
    if (scaleText) {
        const p = document.createElement("p");
        p.className = "indicator-text";
        p.innerHTML = scaleText;
        body.appendChild(p);
    }
    const list = document.createElement("div");
    list.className = "bar-list";
    distribution.forEach((share, i) => {
        const decile = i + 1;
        const row = barRow({ name: `Decile ${decile}`, colour: colours[i], share });
        list.appendChild(row);
    });
    body.appendChild(list);
    if (scoreText) {
        const box = document.createElement("div");
        box.className = "indicator-about-box mt-3 mb-0";
        const p = document.createElement("p");
        p.className = "indicator-text";
        p.innerHTML = scoreText;
        box.appendChild(p);
        body.appendChild(box);
    }
    return card;
}

// A light-grey "<abbr> Supergroup"/"<abbr> Group" label (e.g. "OAC Supergroup") marking which
// level a bar list below it belongs to and which classification it's from - same shape as
// colourPill but not tied to any one Supergroup/Group's own colour, since the label itself is a
// category heading, not a specific coloured item. `caption`, when given, trails it as a small
// muted aside (e.g. "top-level category") - a one-line reminder of what Supergroup/Group
// actually means, sitting right where the reader needs it instead of only in the about text above.
function levelPill(text, caption) {
    const p = document.createElement("p");
    p.className = "level-pill-row";
    const captionHtml = caption ? `<span class="level-pill-caption">${caption}</span>` : "";
    p.innerHTML = `<span class="value-pill">${text}</span>${captionHtml}`;
    return p;
}

// The light "i" note under a card's bars; `viewClass` ("share-only"/"index-only") ties it to one view.
function calloutNote(viewClass, html) {
    const note = document.createElement("div");
    note.className = `callout-note mt-3 ${viewClass}`;
    const icon = document.createElement("span");
    icon.className = "callout-icon";
    icon.textContent = "ⓘ";               // circled "i" - no emoji font dependency
    icon.setAttribute("aria-hidden", "true");
    const p = document.createElement("p");
    p.className = "indicator-text";
    p.innerHTML = html;
    note.append(icon, p);
    return note;
}

export function renderGroupCard({ title, about, groups, supergroups, distribution, modeCode, clickHint = "neighbourhood characteristics", flier, name, abbr, population }) {
    const { card, body } = cardShell({ title, about, clickHint, flier });
    if (population) body.appendChild(viewControls(population, true));

    const supergroupTotals = {};
    for (const [code, share] of Object.entries(distribution)) {
        const sg = groups[code] && groups[code].supergroup;
        if (sg == null) continue;
        supergroupTotals[sg] = (supergroupTotals[sg] || 0) + share;
    }
    // Two different "winners", which can legitimately disagree: the supergroup with the highest
    // combined share across all its own groups (the longest bar), versus the supergroup that happens
    // to contain the single most common group (modeCode), whose groups are the ones listed below - a
    // name can be fairly spread across several groups in its leading supergroup while being heavily
    // concentrated in just one group that sits elsewhere. (No bar is bolded as "most common" any
    // more - dropped 2026-10-08, it read as contradicting the index view.)
    const topSupergroup = Object.keys(supergroupTotals)
        .reduce((best, code) => (supergroupTotals[code] > (supergroupTotals[best] || -1) ? code : best), null);
    const modeSupergroup = groups[modeCode] && groups[modeCode].supergroup;

    body.appendChild(levelPill(`${abbr} Supergroup`, "top-level category"));
    const sgList = document.createElement("div");
    sgList.className = "bar-list";
    for (const code of Object.keys(supergroups).sort()) {
        const sg = supergroups[code];
        const row = barRow({ name: sg.name, colour: sg.colour, share: supergroupTotals[code] || 0,
            detailsText: sg.desc, populationShare: sg.populationShare,
            index: population ? indexOf(supergroupTotals[code] || 0, sg.populationShare) : undefined });
        sgList.appendChild(row);
    }
    body.appendChild(sgList);

    if (modeSupergroup != null) {
        const supergroupShare = supergroupTotals[modeSupergroup] || 0;
        const supergroupPopulationShare = supergroups[modeSupergroup].populationShare;
        body.appendChild(levelPill(`${abbr} Group`, "sub-category"));
        const groupList = document.createElement("div");
        groupList.className = "bar-list";
        const codesInSupergroup = Object.keys(groups).filter(c => groups[c].supergroup === modeSupergroup).sort();
        for (const code of codesInSupergroup) {
            const g = groups[code];
            const withinShare = supergroupShare > 0 ? (distribution[code] || 0) / supergroupShare : 0;
            // Re-normalised the same way as withinShare above: what fraction of the SUPERGROUP's own
            // population (not the whole population) lives in this one Group - same share-space as
            // the bar it sits behind.
            const withinPopulationShare = g.populationShare != null && supergroupPopulationShare
                ? g.populationShare / supergroupPopulationShare : null;
            // The index needs no within-supergroup re-normalising: a group's share of the name's bearers
            // over its share of the population is the same number whichever level it is read at.
            const row = barRow({ name: g.name, colour: g.colour, share: withinShare, detailsText: g.desc,
                populationShare: withinPopulationShare,
                index: population ? indexOf(distribution[code] || 0, g.populationShare) : undefined });
            groupList.appendChild(row);
        }
        body.appendChild(groupList);
    }

    // Placed below both bar lists (rather than between them) so the reader sees the full picture
    // first - which Supergroup leads overall, and which Groups it breaks into - before being told
    // the two levels disagree.
    const sgPill = code => colourPill(supergroups[code].name, supergroups[code].colour);
    if (modeSupergroup != null && topSupergroup != null && modeSupergroup !== topSupergroup) {
        body.appendChild(calloutNote("share-only",   // about shares, so not shown in index view
            `${sgPill(topSupergroup)} has the `
            + `highest combined share overall, but the single most common Group for <span class="name-pill">${name}</span> sits `
            + `in a different Supergroup, ${sgPill(modeSupergroup)}, `
            + `shown above - a name can be spread fairly evenly across several Groups in its leading `
            + `Supergroup while being heavily concentrated in just one Group elsewhere.`));
    }

    // Index view's counterpart (option D, agreed with the user 2026-10-08): the Group list is chosen by
    // shares (the Supergroup holding the most common Group), so the Group with the HIGHEST INDEX is
    // often not in it (e.g. smith's OAC 8a, index 151, sits in Legacy Communities while Baseline UK's
    // Groups are listed). Say so, only when that happens. Listing all Groups was judged too long, and
    // switching the list by view would lose the shares view's granularity.
    if (population && modeSupergroup != null) {
        let topIndexCode = null, topIndex = -1;
        for (const [code, g] of Object.entries(groups)) {
            const index = indexOf(distribution[code] || 0, g.populationShare);
            if (index != null && index > topIndex) { topIndex = index; topIndexCode = code; }
        }
        const topIndexSupergroup = topIndexCode != null && groups[topIndexCode].supergroup;
        if (topIndexSupergroup != null && topIndexSupergroup !== modeSupergroup && supergroups[topIndexSupergroup]) {
            const g = groups[topIndexCode];
            body.appendChild(calloutNote("index-only",
                `The Groups listed are those in ${sgPill(modeSupergroup)}, the Supergroup containing the most `
                + `common Group for <span class="name-pill">${name}</span>. Relative to the population, <span class="name-pill">${name}</span> `
                + `is most over-represented in ${colourPill(g.name, g.colour)} (index ${Math.round(topIndex)}), which sits in `
                + `${sgPill(topIndexSupergroup)}.`));
        }
    }
    return card;
}

export function renderFlatGroupCard({ title, about, groups, distribution, modeCode, clickHint, flier, population }) {
    const { card, body } = cardShell({ title, about, clickHint, flier });
    if (population) body.appendChild(viewControls(population, false));
    const list = document.createElement("div");
    list.className = "bar-list";
    for (const code of Object.keys(groups).sort()) {
        const g = groups[code];
        const row = barRow({ name: g.name, colour: g.colour, share: distribution[code] || 0, detailsText: g.desc,
            populationShare: g.populationShare,
            index: population ? indexOf(distribution[code] || 0, g.populationShare) : undefined });
        list.appendChild(row);
    }
    body.appendChild(list);
    return card;
}
