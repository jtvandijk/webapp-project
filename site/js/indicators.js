// Rendering for the neighbourhood-classification indicator cards.
// - IMD / AHAH: a fixed 10-decile bar chart (renderDecileCard).
// - OAC / LOAC: two levels - all supergroups (fixed canonical order, official pen-portrait text
//   behind a click on the name), then just the groups inside this name's own modal supergroup,
//   shown as a share WITHIN that supergroup (renderGroupCard).
// - GB2C / FPC: a flat set of groups, same bar style, but no expand - neither classification has
//   official descriptive text per group the way OAC/LOAC do (renderFlatGroupCard).

function pct(share) {
    return `${(share * 100).toFixed(1)}%`;
}

// share (0-1) always drives the bar's width; valueText overrides what's printed (e.g. a raw count)
// when the row isn't itself a percentage of 100%, like the bearers-over-time table in profile.js.
export function barRow({ name, colour, share, valueText, detailsText }) {
    const widthPct = pct(share);
    const text = valueText != null ? valueText : widthPct;
    const label = `
        <span class="bar-label">
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
        body.textContent = detailsText;
        details.append(summary, body);
        return details;
    }
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = label;
    return row;
}

export function cardShell({ title, about }) {
    const card = document.createElement("div");
    card.className = "card mb-3 indicator-card";
    card.innerHTML = `<div class="card-header"><h4 class="m-0">${title}</h4></div>`;
    const body = document.createElement("div");
    body.className = "card-body";
    if (about) {
        const p = document.createElement("p");
        p.className = "indicator-about text-muted";
        p.textContent = about;
        body.appendChild(p);
    }
    card.appendChild(body);
    return { card, body };
}

export function renderDecileCard({ title, about, colours, distribution, mode, scaleText, scoreText }) {
    const { card, body } = cardShell({ title, about });
    if (scaleText) {
        const p = document.createElement("p");
        p.textContent = scaleText;
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
        const p = document.createElement("p");
        p.className = "indicator-score text-muted mt-3 mb-0";
        p.textContent = scoreText;
        body.appendChild(p);
    }
    return card;
}

export function renderGroupCard({ title, about, groups, supergroups, distribution, modeCode }) {
    const { card, body } = cardShell({ title, about });

    const supergroupTotals = {};
    for (const [code, share] of Object.entries(distribution)) {
        const sg = groups[code] && groups[code].supergroup;
        if (sg == null) continue;
        supergroupTotals[sg] = (supergroupTotals[sg] || 0) + share;
    }
    const modeSupergroup = groups[modeCode] && groups[modeCode].supergroup;

    const sgList = document.createElement("div");
    sgList.className = "bar-list";
    for (const code of Object.keys(supergroups).sort()) {
        const sg = supergroups[code];
        const row = barRow({ name: sg.name, colour: sg.colour, share: supergroupTotals[code] || 0, detailsText: sg.desc });
        if (code === modeSupergroup) row.classList.add("bar-row-mode");
        sgList.appendChild(row);
    }
    body.appendChild(sgList);

    if (modeSupergroup != null) {
        const supergroupShare = supergroupTotals[modeSupergroup] || 0;
        const sub = document.createElement("div");
        sub.className = "mt-3";
        const heading = document.createElement("h6");
        heading.className = "text-muted";
        heading.textContent = `Groups within ${supergroups[modeSupergroup].name} (share within this supergroup)`;
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

export function renderFlatGroupCard({ title, about, groups, distribution, modeCode }) {
    const { card, body } = cardShell({ title, about });
    const list = document.createElement("div");
    list.className = "bar-list";
    for (const code of Object.keys(groups).sort()) {
        const g = groups[code];
        const row = barRow({ name: g.name, colour: g.colour, share: distribution[code] || 0 });
        if (code === modeCode) row.classList.add("bar-row-mode");
        list.appendChild(row);
    }
    body.appendChild(list);
    return card;
}
