//basemap
var map = L.map('kdemap').setView([54.505, -4], 6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
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

//countries
$j.getJSON(ireland_gjson, function (data) {L.geoJSON(data, {weight:0,fillColor:'#DCDCDC',fillOpacity:'.8'}).addTo(map);});

//render geoJSON layer
function renderContour(years,contours) {

  //individual features
  var layers = [];
  for (var i = 0, clen = contours.length; i < clen; i++) {
    var time = new Date (years[i].toString()).getTime();
    var cont = JSON.parse(contours[i][1])

    //individual polygons
    for (var j = 0, flen = cont.features.length; j < flen; j++) {
      cont.features[j].properties.time = time;
      };

    //combine
    layers.push(cont);
    };

  //leaflet layer
  var contourJSON = L.geoJSON(layers, {
    style: function(feature) {
      if(feature.properties.time < 1990) {
        return {color: '#FA2600',fillColor: '#FA2600',fillOpacity: .4};
      } else if (feature.properties.time > 1990) {
        return {color: '#3273d1',fillColor: '#3273d1',fillOpacity: .4};
      }
    }});

  //return
  return contourJSON;
};
