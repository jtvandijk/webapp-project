// The KDE map: one Leaflet map, one GeoJSON layer for the current period's polygons, one for the
// Scotland mask. Replaces the legacy site's Leaflet.TimeDimension plugin (built for continuous,
// animated time series) - here the "time" axis is just an index into a short, fixed, unevenly
// spaced list of periods, so a plain slider plus "swap the layer's data" is all that's needed.
import { DATA_ROOT } from "./data.js";

// Same weight/contrast as manifest.levels' blues (ColorBrewer Blues[9], indices 4-6), but the
// SmartCensus base year (the newest, genuinely new survey, not a legacy register year) is marked
// out in red (ColorBrewer Reds[9], same indices) so it reads as visibly different data, not just
// another register year.
const SMARTCENSUS_LEVELS = { 1: "#fb6a4a", 2: "#ef3b2c", 3: "#cb181d" };

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
    const baseYear = manifest.standardisation.base_year;
    let currentPeriodId = null;

    const kdeLayer = L.geoJSON(null, {
        style: feature => {
            const colours = currentPeriodId === baseYear ? SMARTCENSUS_LEVELS : levelColour;
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

    async function renderPeriod(nameData, periodId, fitBounds = false) {
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
            maskLayer.addData(mask);
        }

        if (fitBounds && geojson && geojson.features.length) {
            map.fitBounds(kdeLayer.getBounds(), { maxZoom: manifest.basemap.maxZoom });
        }
    }

    return { map, renderPeriod };
}
