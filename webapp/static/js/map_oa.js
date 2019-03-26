//basemap
var omap = L.map('oamap').setView([54.505, -4], 5);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
            minZoom: '5',
            maxZoom: '10',
          }).addTo(omap);

//bounds
var southWest = L.latLng(61.0, 4.05),
    northEast = L.latLng(50.0, -12,01),
    bounds = L.latLngBounds(southWest, northEast);

omap.setMaxBounds(bounds);

//fullscreen
omap.addControl(new L.Control.Fullscreen());

//countries
$j.getJSON(ireland_gjson, function (data) {L.geoJSON(data, {weight:0,fillColor:'#DCDCDC',fillOpacity:'.8'}).addTo(omap);});
