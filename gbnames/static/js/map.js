//global
var control;
var layer_rm;
var adminlayer;

//icons
var hist = new L.Icon({
  iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25,41],
  iconAnchor: [12,41],
  popupAnchor: [1,-34],
  shadowSize: [41,41]
});

var cont = new L.Icon({
  iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25,41],
  iconAnchor: [12,41],
  popupAnchor: [1,-34],
  shadowSize: [41,41]
});

//basemap
var map = L.map('kdemap').setView([54.505,-4],6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
            minZoom: 6,
            maxZoom: 12,
          }).addTo(map);

//bounds
var southWest = L.latLng(62.0,4.05),
    northEast = L.latLng(50.0,-12,01),
    bounds = L.latLngBounds(southWest,northEast);

map.setMaxBounds(bounds);

//zoom
L.easyButton('fas fa-arrows-alt', function(btn, map){
    map.setView([54.505,-4], 6);
}).addTo(map)

//cover mask
L.tileLayer('https://julie.geog.ucl.ac.uk/~ucfajtv/tiles/gbnames/out/{z}/{x}/{y}.png',
  {maxZoom: 12,
   minZoom: 6,
   bounds: bounds,
   zIndex: 600,
}).addTo(map);

//render geoJSON layer
function renderContour(years,kdes) {

  //individual features
  var layers = [];
  for (var i = 0, klen = kdes.length; i < klen; i++) {

    var year = new Date (years[i].toString()).getTime();
    var kde = JSON.parse(kdes[i].kde)

    //individual polygons
    for (var p = 0, plen = kde.features.length; p < plen; p++) {
      kde.features[p].properties.time = year};

    //combine
    layers.push(kde)};

  //leaflet layer
  var contourJSON = L.geoJSON(layers, {
    style: function(feature) {
      if (feature.properties.level == 1) {
        return {weight:0,color:'#6baed6',fillColor:'#6baed6',fillOpacity:.7,opacity:.2};
      } else if (feature.properties.level == 2) {
        return {weight:0,color:'#4292c6',fillColor:'#4292c6',fillOpacity:.7,opacity:.2};
      } else if (feature.properties.level == 3) {
        return {weight:0,color:'#2171b5',fillColor:'#2171b5',fillOpacity:.7,opacity:.2};
      }},
    smoothFactor: 0
    });

  //return
  return contourJSON;
};

function renderMap(years,kdes,map) {

  //remove previous layer
  if (control != undefined) {
      map.removeControl(control);
      map.removeLayer(layer_rm);
      };

  //geoJSON
  var layer = renderContour(years,kdes);
  map.setView([54.505, -4], 6);

  //set up years
  var slider = '';
  for (var i = 0; i < years.length - 1; ++i) {
    slider = slider + years[i] + ',';
    };
  var slider = slider + years[years.length-1];

  //set up time dimension
  var timeDimension = new L.TimeDimension({
      times: slider,
    });
  timeDimension.setCurrentTime(timeDimension.getAvailableTimes()[0]);

  //set up player
  var player = new L.TimeDimension.Player({
      transitionTime: 0,
      loop: false,
      buffer: -1,
      minBufferReady: -1,
      startOver:false
    }, timeDimension);

  var timeDimensionControlOptions = {
      player: player,
      timeDimension: timeDimension,
      position: 'topright',
      autoPlay: false,
      speedSlider: false,
      timeSliderDragUpdate: true,
    };

  var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);

  //add to map
  map.timeDimension = timeDimension;
  map.addControl(timeDimensionControl);

  //prepare layer
  var geoJsonTimeLayer = L.timeDimension.layer.geoJson.geometryCollection(layer,{
    updateTimeDimension: true,
    updateTimeDimensionMode: 'replace',
    duration: 'PT30M',
  });

  //manage
  control = timeDimensionControl;
  layer_rm = geoJsonTimeLayer;

  //add
  geoJsonTimeLayer.addTo(map);
  map.fitBounds(geoJsonTimeLayer.getBounds())
};

//top administrative areas
function mapAdmin(sel,all,sr) {

  //remove
  if (adminlayer != undefined) {
      map.removeLayer(adminlayer);
  };

  //render admin
  var markers = new L.featureGroup();
  var admin = JSON.parse(all);
  for (var i=0; i < admin.features.length; ++i) {
    var aa = admin.features[i].geometry.coordinates;
    if (sr == 'hr') {
      var id = admin.features[i].properties.id;
      var name = admin.features[i].properties.parish;
      var regcnty = admin.features[i].properties.regcnty;
      var cnty = admin.features[i].properties.cnty;
      var info = '<strong>'+name+'</strong><br>'+regcnty+' ('+cnty+')'
      var icon = hist;
    } else if (sr == 'cr') {
      var id = admin.features[i].properties.msoa11nm;
      var name = admin.features[i].properties.ladnm;
      var info = '<strong>'+name+'</strong><br>'+id;
      var icon = cont;
    };
    var mrkr = L.marker([aa[1],aa[0]],{icon: icon,id: id}).bindPopup(info,{autoPan: false});
    mrkr.addTo(markers);
    };

  //scroll
  scroll(0,0);

  //map
  adminlayer = markers;
  markers.addTo(map);
  markers.eachLayer(function (layer) {
  if (sel == layer.options.id) {
    layer.openPopup();
    };
  });
};
