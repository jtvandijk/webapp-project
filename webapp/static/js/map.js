//basemap
var map = L.map('kdemap').setView([54.505, -4], 6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors,\n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
            minZoom: '6',
            maxZoom: '10',
          }).addTo(map);

//bounds
var southWest = L.latLng(61.0, 4.05),
    northEast = L.latLng(50.0, -12,01),
    bounds = L.latLngBounds(southWest, northEast);

map.setMaxBounds(bounds);

//fullscreen
map.addControl(new L.Control.Fullscreen());

//ireland
$j.getJSON(ireland, function (data) {
    L.geoJSON(data,  {weight: 0, fillColor: '#DCDCDC', fillOpacity: '.8'}).addTo(map);
});




//render found // first search, before timedimension controller
function renderMap(data,year) {

  //create GeoJSON
  var contour = {
      "type": "Feature",
      "geometry": {
          "type": "MultiPolygon",
          "coordinates": [data]
      }
  };

  //define style
  if (year < 1997) {
    var contour_style = {
      color: '#FA2600',
      fillColor: '#FA2600',
      fillOpacity: .4,
      };
  } else {
    var contour_style = {
      color: '#3273d1',
      fillColor: '#3273d1',
      fillOpacity: .4,
    }
  };

  //prepare for Leaflet
  var contourJSON = L.geoJSON(contour, {style: contour_style});
  return contourJSON;
};
