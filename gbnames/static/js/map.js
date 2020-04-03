//global
var mapcontrol;
var maplayer;

//map settings
var southWest = L.latLng(62,  4),
    northEast = L.latLng(50,-12),
    bounds = L.latLngBounds(southWest,northEast);

var map = L.map('kdemap').setView([54.505,-4],6);
map.setMaxBounds(bounds);

//basemap
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
             minZoom: 6,
             maxZoom: 12,
             bounds: bounds
          }).addTo(map);

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
function renderContour(years,kdes,scotland) {

  //individual features
  var layers = [];
  for (var i = 0, klen = kdes.length; i < klen; i++) {

    var year = new Date (years[i].toString()).getTime();
    var kde = JSON.parse(kdes[i].kde)

    //individual polygons
    for (var p = 0, plen = kde.features.length; p < plen; p++) {
      kde.features[p].properties.time = year;
    };

    //combine
    layers.push(kde);
  };

  //scotland
  if (scotland != 'empty') {
    scotland = JSON.parse(scotland.kde);
    for (var s = 0, slen = scotland.features.length; s < slen; s++) {
      scotland.features[s].properties.time = -1861920000000;
      scotland.features[s].properties.level = 0;
    };
    layers.push(scotland);
  };

  //leaflet layer
  var contourJSON = L.geoJSON(layers, {
    style: function(feature) {
      if (feature.properties.level == 0) {
        return {weight:0,fillColor:'#DCDCDC',fillOpacity:'.7'};
      } else if (feature.properties.level == 1) {
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

function renderMap(years,kdes,scotland,map) {

  //remove previous layer
  if (mapcontrol != undefined) {
      map.removeControl(mapcontrol);
      map.removeLayer(maplayer);
      };

  //geoJSON
  var layer = renderContour(years,kdes,scotland);

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
    duration: 'PT20S',
    bounds: bounds,
  });

  //manage
  mapcontrol = timeDimensionControl;
  maplayer = geoJsonTimeLayer;

  //add
  map.setView([54.505,-4], 6);
  geoJsonTimeLayer.addTo(map);
};
