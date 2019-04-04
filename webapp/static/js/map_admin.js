//basemap
var amap = L.map('adminmap').setView([54.505, -4], 6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
            minZoom: '6',
            maxZoom: '11',
          }).addTo(amap);

//bounds
var southWest = L.latLng(61.0, 4.05),
    northEast = L.latLng(50.0, -12,01),
    bounds = L.latLngBounds(southWest, northEast);

amap.setMaxBounds(bounds);

//fullscreen
amap.addControl(new L.Control.Fullscreen());

//countries
$j.getJSON(ireland_gjson, function (data) {L.geoJSON(data, {weight:0,fillColor:'#DCDCDC',fillOpacity:'.8'}).addTo(amap);});
