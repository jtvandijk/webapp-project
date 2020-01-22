//basemap
var cmap = L.map('kdemap').setView([54.505,-4],6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
            minZoom: '6',
            maxZoom: '11',
          }).addTo(cmap);

//bounds
var southWest = L.latLng(62.0,4.05),
    northEast = L.latLng(50.0,-12,01),
    bounds = L.latLngBounds(southWest,northEast);

cmap.setMaxBounds(bounds);

//fullscreen
cmap.addControl(new L.Control.Fullscreen());

//countries
$j.getJSON(ireland_gjson,function (data) {L.geoJSON(data,{weight:0,fillColor:'#DCDCDC',fillOpacity:'.8'}).addTo(cmap);});

//render geoJSON layer
function renderContour(years,contours,nireland) {

  //individual features
  var layers = [];
  for (var i = 0, clen = contours.length; i < clen; i++) {
    var time = new Date (years[i].toString()).getTime();
    var cont = JSON.parse(contours[i][1])

    //individual polygons
    for (var j = 0, flen = cont.features.length; j < flen; j++) {
      cont.features[j].properties.time = time;
      cont.features[j].properties.type = 'contour';
      };

    //northern ireland
    if(years[i] < 1990) {
      var ni = JSON.parse(nireland)
      ni.features[0].properties.time = time;
      ni.features[0].properties.type = 'nireland';
      layers.push(ni);
    };

    //combine
    layers.push(cont);
    };

  //leaflet layer
  var contourJSON = L.geoJSON(layers, {
    style: function(feature) {
      if(feature.properties.time < 1990 && feature.properties.type == 'contour') {
        return {color: '#73777A',fillColor: '#73777A',fillOpacity: .4};
      } else if (feature.properties.time > 1990 && feature.properties.type == 'contour') {
        return {color: '#E68454',fillColor: '#E68454',fillOpacity: .4};
      } else if (feature.properties.time < 1990 && feature.properties.type == 'nireland') {
        return {weight:0,fillColor:'#DCDCDC',fillOpacity:'.8'};
      }}});

  //return
  return contourJSON;
};
