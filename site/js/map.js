// The KDE map: one Leaflet map, one GeoJSON layer for the current period's polygons, one for the
// Scotland mask. Replaces the legacy site's Leaflet.TimeDimension plugin (built for continuous,
// animated time series) - here the "time" axis is just an index into a short, fixed, unevenly
// spaced list of periods, so a plain slider plus "swap the layer's data" is all that's needed.
import { DATA_ROOT } from "./data.js";

// Every SmartCensus (register) year is marked out from Historic Census years in teal, not just the
// newest one - a clean break at the 1921/1997 boundary, same idea and same colour as the bearers
// chart/place chips (site/js/profile.js's SMARTDATA_COLOUR). #27cca4 is GeoDS's own logo teal
// (colour-picked by the user, 2026-10-06); the lighter/darker shades are the same hue/saturation at
// different lightness, matching how manifest.levels' own blues step from light to dark.
const SMARTCENSUS_LEVELS = { 1: "#69e2c4", 2: "#27cca4", 3: "#1a896d" };

let scotlandMaskCache = null;

async function loadScotlandMask(url) {
    if (!scotlandMaskCache) {
        scotlandMaskCache = fetch(`${DATA_ROOT}/${url}`).then(res => res.json());
    }
    return scotlandMaskCache;
}

export function createMap(container, manifest) {
    const map = L.map(container, {
        center: manifest.basemap.center,
        zoom: manifest.basemap.zoom,
        minZoom: manifest.basemap.minZoom,
        maxZoom: manifest.basemap.maxZoom,
        maxBounds: manifest.basemap.maxBounds,
    });

    const labelPane = map.createPane("labels");
    labelPane.style.zIndex = 600;

    for (const tile of manifest.basemap.tiles) {
        L.tileLayer(tile.url, {
            attribution: tile.attribution || "",
            pane: tile.labels ? "labels" : "tilePane",
        }).addTo(map);
    }

    const levelColour = Object.fromEntries(manifest.levels.map(l => [l.level, l.colour]));
    const periodSource = Object.fromEntries(manifest.periods.map(p => [p.id, p.source]));
    let currentPeriodId = null;

    const kdeLayer = L.geoJSON(null, {
        style: feature => {
            const colours = periodSource[currentPeriodId] === "register" ? SMARTCENSUS_LEVELS : levelColour;
            return { color: colours[feature.properties.level] || colours[1], weight: 1, fillOpacity: 0.6 };
        },
    }).addTo(map);

    const maskStyle = manifest.masks.scotland;
    const maskLayer = L.geoJSON(null, {
        style: () => ({ color: maskStyle.colour, fillColor: maskStyle.colour, fillOpacity: maskStyle.opacity, weight: 0 }),
        interactive: false,
    }).addTo(map);

    // Which periods carry a mask, per the manifest - keyed by period id for a quick lookup per render.
    const maskedPeriods = new Map(manifest.periods.filter(p => p.mask).map(p => [p.id, p.mask]));

    // The initial zoom should comfortably fit every period's own extent, not just whichever one is
    // shown first - a name concentrated in a small area in one year but spread much further in
    // another would otherwise need re-zooming the moment the slider moves.
    function boundsAcrossAllPeriods(nameData) {
        let bounds = null;
        for (const geojson of Object.values(nameData.maps)) {
            if (!geojson || !geojson.features || !geojson.features.length) continue;
            const periodBounds = L.geoJSON(geojson).getBounds();
            bounds = bounds ? bounds.extend(periodBounds) : periodBounds;
        }
        return bounds;
    }

    // Guards the one await below: rapidly toggling the slider can start a second renderPeriod()
    // before the first's mask fetch resolves, and without this, the first call's mask data can land
    // after the second's and overwrite it with a stale period's mask (or lack of one).
    let renderToken = 0;

    async function renderPeriod(nameData, periodId, fitBounds = false) {
        const myToken = ++renderToken;
        currentPeriodId = periodId;
        const geojson = nameData.maps[periodId];
        kdeLayer.clearLayers();
        if (geojson) kdeLayer.addData(geojson);

        maskLayer.clearLayers();
        const maskName = maskedPeriods.get(periodId);
        // the mask is drawn only when this period's map was actually built from that year's own
        // data (no copyOf) - a copied map (e.g. 1911 showing 1901) already has Scotland in it.
        if (maskName && geojson && !geojson.copyOf) {
            const mask = await loadScotlandMask(manifest.masks[maskName].url);
            if (myToken !== renderToken) return;   // a newer render has since started - drop this one
            maskLayer.addData(mask);
        }

        if (fitBounds) {
            const bounds = boundsAcrossAllPeriods(nameData);
            if (bounds && bounds.isValid()) {
                map.fitBounds(bounds, { maxZoom: manifest.basemap.maxZoom });
            }
        }
    }

    return { map, renderPeriod };
}
