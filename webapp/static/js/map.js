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

//shapes
var ireland = $j.getJSON(ireland_gjson, function (data) {
    L.geoJSON(data, {weight: 0, fillColor: '#DCDCDC', fillOpacity: '.8'}).addTo(map);
});

//render geoJSON layer
function renderContour(years,contours) {

  //individual features
  var layers = [];
  //contours.length-1
  for (var i = 0, len = 1; i < len; i++){
      var time = new Date (years[i].toString()).getTime();
      layers.push({
          "type": "Feature",
          "properties": {
            "time": time,
          },
          "geometry": {
              "type": 'MultiPolygon',
              "coordinates": [contours[i][1]]
          }});
  };

  console.log(layers[0].geometry.coordinates);

  var poly1 = turf.polygon([[
    [-0.801742, 51.48565],
    [-0.801742, 51.60491],
    [-0.584762, 51.60491],
    [-0.584762, 51.48565],
    [-0.801742, 51.48565]
  ]]);


  var poly2 = turf.polygon([[
    [-0.520217, 51.535693],
    [-0.64038, 51.553967],
    [-0.720031, 51.526554],
    [-0.669906, 51.507309],
    [-0.723464, 51.446643],
    [-0.532577, 51.408574],
    [-0.487258, 51.477466],
    [-0.520217, 51.535693]
  ]]);

  var poly3 = turf.polygon(layers[0].geometry.coordinates);

  L.geoJSON(poly1).addTo(map);
  L.geoJSON(poly2).addTo(map);
  //var t = L.geoJSON(layers[0].geometry.coordinates)
//  console.log(poly3 );
//  var ukclip = turf.difference(poly1, poly2);
//  var clipclip = turf.difference(t, poly2);

//  L.geoJSON(ukclip,{color: '#FA2600',fillcolor: '#FA2600'}).addTo(map);
//  L.geoJSON(clipclip,{color: '#FA2600',fillcolor: '#FA2600'}).addTo(map);



  //
  //var difference = turf.intersect(feature1,feature2);
  //console.log(difference);
  //
  //L.geoJSON(difference).addTo(map);

  //leaflet layer
  var contourJSON = L.geoJSON(layers, {
    style: function(feature) {
      if(feature.properties.time < 1990) {
         return {color: '#FA2600',fillColor: '#FA2600',fillOpacity: .4};
      } else if (feature.properties.time > 1990) {
        return {color: '#3273d1',fillColor: '#3273d1',fillOpacity: .4};
      }
  }});

  console.log(contourJSON);
  //return
  return contourJSON;
};
