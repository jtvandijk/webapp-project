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

// share (0-1) always drives the bar's width; valueText overrides what's printed (e.g. a raw count)
// when the row isn't itself a percentage of 100%, like the bearers-over-time table in profile.js.
export function barRow({ name, colour, share, valueText, detailsText }) {
    const widthPct = pct(share);
    const text = valueText != null ? valueText : widthPct;
    const chevron = detailsText ? `<span class="bar-chevron" aria-hidden="true">&#9656;</span>` : "";
    const label = `
        <span class="bar-label">
            ${chevron}
            <span class="bar-swatch" style="background:${colour}"></span>
            <span class="bar-name">${name}</span>
            <span class="bar-pct">${text}</span>
        </span>
        <span class="bar-track"><span class="bar-fill" style="width:${widthPct};background:${colour}"></span></span>`;

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
// input, so this is safe - it's how each card's real citation links render. about (+ clickHint, if
// given) sit in their own tinted box, set apart from the bars below - stands in for the old site's
// flier-thumbnail-alongside-text treatment until real fliers exist.
export function cardShell({ title, about, clickHint }) {
    const card = document.createElement("div");
    card.className = "card mb-3 indicator-card";
    card.innerHTML = `<div class="card-header"><h4 class="m-0">${title}</h4></div>`;
    const body = document.createElement("div");
    body.className = "card-body";
    if (about || clickHint) {
        const box = document.createElement("div");
        box.className = "indicator-about-box";
        if (about) {
            const p = document.createElement("p");
            p.className = "indicator-text";
            p.innerHTML = about;
            box.appendChild(p);
        }
        if (clickHint) {
            const p = document.createElement("p");
            p.className = "indicator-text";
            p.innerHTML = `Click on any label to find out its ${clickHint}.`;
            box.appendChild(p);
        }
        body.appendChild(box);
    }
    card.appendChild(body);
    return { card, body };
}

export function renderDecileCard({ title, about, colours, distribution, mode, scaleText, scoreText }) {
    const { card, body } = cardShell({ title, about });
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
        if (decile === mode) row.classList.add("bar-row-mode");
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

export function renderGroupCard({ title, about, groups, supergroups, distribution, modeCode, clickHint = "neighbourhood characteristics" }) {
    const { card, body } = cardShell({ title, about, clickHint });

    const supergroupTotals = {};
    for (const [code, share] of Object.entries(distribution)) {
        const sg = groups[code] && groups[code].supergroup;
        if (sg == null) continue;
        supergroupTotals[sg] = (supergroupTotals[sg] || 0) + share;
    }
    // Two different "winners", which can legitimately disagree: the supergroup with the highest
    // combined share across all its own groups (bolded in the list below, so bold always tracks the
    // longest bar), versus the supergroup that happens to contain the single most common group
    // (modeCode) - a name can be fairly spread across several groups in its leading supergroup while
    // being heavily concentrated in just one group that sits elsewhere.
    const topSupergroup = Object.keys(supergroupTotals)
        .reduce((best, code) => (supergroupTotals[code] > (supergroupTotals[best] || -1) ? code : best), null);
    const modeSupergroup = groups[modeCode] && groups[modeCode].supergroup;

    const sgList = document.createElement("div");
    sgList.className = "bar-list";
    for (const code of Object.keys(supergroups).sort()) {
        const sg = supergroups[code];
        const row = barRow({ name: sg.name, colour: sg.colour, share: supergroupTotals[code] || 0, detailsText: sg.desc });
        if (code === topSupergroup) row.classList.add("bar-row-mode");
        sgList.appendChild(row);
    }
    body.appendChild(sgList);

    if (modeSupergroup != null && topSupergroup != null && modeSupergroup !== topSupergroup) {
        const note = document.createElement("p");
        note.className = "indicator-text mt-3 mb-0";
        note.innerHTML = `<strong>${supergroups[topSupergroup].name}</strong> has the highest combined `
            + `share overall, but your name's single most common Group sits in a different Supergroup, `
            + `<strong>${supergroups[modeSupergroup].name}</strong>, shown below - a name can be spread `
            + `fairly evenly across several Groups in its leading Supergroup while being heavily `
            + `concentrated in just one Group elsewhere.`;
        body.appendChild(note);
    }

    if (modeSupergroup != null) {
        const supergroupShare = supergroupTotals[modeSupergroup] || 0;
        const sub = document.createElement("div");
        sub.className = "group-drilldown";
        const heading = document.createElement("h6");
        heading.innerHTML = `Groups within <strong>${supergroups[modeSupergroup].name}</strong> (share within this Supergroup)`;
        sub.appendChild(heading);
        const groupList = document.createElement("div");
        groupList.className = "bar-list";
        const codesInSupergroup = Object.keys(groups).filter(c => groups[c].supergroup === modeSupergroup).sort();
        for (const code of codesInSupergroup) {
            const g = groups[code];
            const withinShare = supergroupShare > 0 ? (distribution[code] || 0) / supergroupShare : 0;
            const row = barRow({ name: g.name, colour: g.colour, share: withinShare, detailsText: g.desc });
            if (code === modeCode) row.classList.add("bar-row-mode");
            groupList.appendChild(row);
        }
        sub.appendChild(groupList);
        body.appendChild(sub);
    }
    return card;
}

export function renderFlatGroupCard({ title, about, groups, distribution, modeCode, clickHint }) {
    const { card, body } = cardShell({ title, about, clickHint });
    const list = document.createElement("div");
    list.className = "bar-list";
    for (const code of Object.keys(groups).sort()) {
        const g = groups[code];
        const row = barRow({ name: g.name, colour: g.colour, share: distribution[code] || 0, detailsText: g.desc });
        if (code === modeCode) row.classList.add("bar-row-mode");
        list.appendChild(row);
    }
    body.appendChild(list);
    return card;
}
