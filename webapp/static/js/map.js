//basemap
var map = L.map('kdemap').setView([54.505, -4], 6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors,\n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
            minZoom: '6',
          }).addTo(map);

//bounds
var southWest = L.latLng(61.0, 4.05),
    northEast = L.latLng(50.0, -12,01),
    bounds = L.latLngBounds(southWest, northEast);

map.setMaxBounds(bounds);

//ireland
$j.getJSON(ireland, function (data) {
    L.geoJSON(data,  {weight: 0, fillColor: '#DCDCDC', fillOpacity: '.8'}).addTo(map);
});
