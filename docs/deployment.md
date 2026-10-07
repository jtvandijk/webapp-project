# Deploying GBNames

For whoever puts the site on a web server. The new GBNames is a **static website**: HTML, CSS, JavaScript and
JSON files. No application server, no database, no build step. It replaces the old Django site at
`https://apps.geods.ac.uk/gbnames/`.

## What to put on the server

One folder, served as-is:

```
gbnames/
  index.html, about.html, robots.txt
  css/  js/  img/  vendor/  fliers/  lookups/      the site itself (about 7 MB)
  data/                                            the data release (about 5.5 GB, about 86,500 files)
    manifest.json, lookups.json
    index/<xx>.json        search suggestions
    names/<xx>/<name>.json one file per surname: counts and maps
    facts/<xx>/<name>.json one file per surname: the neighbourhood facts
    masks/scotland.json
```

Every path in the site is relative, so the folder works at a domain root or under a sub-path such as
`/gbnames/` without changes. In this repository the site is `site/` and the release is the git-ignored `data/`
(the `site/data/` folder in git is a small synthetic sample for development, never deployed).

## Must have

1. **Serve it over http(s).** Opening `index.html` from disk does not work (the JavaScript uses ES modules and `fetch`).
2. **A missing file must return a real 404.** A search for a name we have no page for requests
   `data/names/<xx>/<name>.json`; the 404 is what makes the page say "We couldn't find a page for this surname".
   Do not add a catch-all that returns `index.html` (or anything else with status 200) for missing files.
3. **`.json` served as `application/json`** (nginx's default `mime.types` already does this).

## Up to you, but worth doing

- **gzip** for JSON, JavaScript and CSS. The map files are GeoJSON and shrink to about a quarter (the largest,
  `smith.json`, goes from about 790 KB to about 215 KB). nginx does not gzip JSON unless told to.
- **Caching `data/`.** The files never change within a release, so they can be cached. They are not versioned by
  file name, though: a later release (or a corrected `lookups.json`) replaces files at the same paths. A max-age of
  a day to a week, with the default `ETag`/`Last-Modified` revalidation, is a reasonable balance. Avoid `immutable`
  or very long lifetimes, unless it is fine for returning visitors to keep seeing old data for that long after an update. Keep the site's own
  `js/` and `css/` on a short cache for the same reason.
- **robots.txt.** `robots.txt` asks crawlers to stay out of `data/` (tens of thousands of JSON files, no value in
  search results). Crawlers only read it at the root of the host, so under `/gbnames/` the file in the folder is
  ignored. If you want the same effect, add `Disallow: /gbnames/data/` to `https://apps.geods.ac.uk/robots.txt`.

An example for nginx, with the folder at `/var/www/gbnames` and the site at `/gbnames/`:

```nginx
# inside the existing server { } block for apps.geods.ac.uk
gzip on;
gzip_types application/json application/javascript text/css image/svg+xml;
gzip_min_length 1024;

location /gbnames/ {
    root /var/www;                      # /gbnames/x -> /var/www/gbnames/x
    index index.html;
    try_files $uri $uri/ =404;
    expires 1h;
}

location /gbnames/data/ {
    root /var/www;
    try_files $uri =404;
    expires 7d;
}
```

## Google Analytics

Already included: the GA4 tag (`G-PL2DNHVGGL`, property "gbnames - liverpool") is in the `<head>` of both
`index.html` and `about.html`; nothing to add. (The old site's tags are Universal Analytics, `UA-157283744-…`,
which Google stopped processing in 2023.) Searches change the address (`?name=smith`) without reloading the page;
GA4's enhanced measurement counts these as page views by default.

## What the site loads from elsewhere

- Basemap tiles from `maps.cdrc.ac.uk` (set in `data/manifest.json`, `basemap.tiles`).
- The Open Sans font from Google Fonts.

Everything else (Bootstrap, Leaflet, images, the GeoDS fliers) is in the folder.

## Checks after it is live

- `/gbnames/` shows the welcome page with five example names.
- `/gbnames/?name=smith` shows the map, the year slider, and the cards (deprivation, OAC, LOAC, gambling, AHAH,
  financial precarity, places, forenames, ethnicity, number of bearers).
- On Smith's 1911 map Scotland is shaded grey; on Macdonald's 1911 map it is not, and a note says the 1901 map is shown.
- A made-up name (`?name=qqqqzz`) shows "We couldn't find a page for this surname".
- `/gbnames/data/names/sm/smith.json` comes back with `Content-Encoding: gzip` (if gzip is on) and your cache headers.

## Updating later

| What changed | What to replace |
|---|---|
| Card text, classification names or colours | `data/lookups.json` (made by `tools/build_lookups.py`) |
| Page text, layout, code | the changed files in the site folder (`index.html`, `about.html`, `css/`, `js/`, ...) |
| A new data release | the whole `data/` folder |

How the release itself is built: [how-to-build-the-dataset.md](how-to-build-the-dataset.md), section 11 for the
steps after the TRE.
