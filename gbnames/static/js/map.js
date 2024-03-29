//global
var mapcontrol;
var maplayer;

//basemap settings
var southWest = L.latLng(62, 20),
    northEast = L.latLng(50,-28),
    bbounds = L.latLngBounds(southWest,northEast);

//basemap settings
var southWest = L.latLng(62, 4),
    northEast = L.latLng(50,-12),
    lbounds = L.latLngBounds(southWest,northEast);

var map = L.map('kdemap').setView([54.505,-4],6);
map.setMaxBounds(bbounds);
map.createPane('labels');
map.getPane('labels').style.zIndex = 600;

//basemap
L.tileLayer('https://maps.cdrc.ac.uk/tiles/shine_urbanmask_light/{z}/{x}/{y}.png',
            {attribution: 'Contains Ordnance Survey Data &copy Crown Copyright'  ,
             minZoom: 6,
             maxZoom: 12,
             bounds: bbounds
            }).addTo(map);
            
//labels
L.tileLayer('https://maps.cdrc.ac.uk/tiles/shine_labels_gbnames/{z}/{x}/{y}.png',
            {minZoom: 6,
             maxZoom: 12,
             bounds: lbounds,
             pane: 'labels',
            }).addTo(map);

//zoom
L.easyButton('fas fa-arrows-alt', function(btn,map){
  map.setView([54.505,-4], 6);
}).addTo(map);

//load layers
async function renderLayers(surname,years) {

  //layers
  var layers = [];

  //individual features
  for (var i = 0, klen = years.length; i < klen; i++) {

    //files
    var name = surname.toLowerCase().replace(/[\W^0-9^\s]+/g,'');
    var fld = name.slice(0,2);
    var path = '/static/kde/' + fld + '/' + name + '/' + name + '_' + years[i] + '.json';
    var year = new Date (years[i].toString()).getTime();

    //parse
    var layer = await $j.getJSON(path,function(kde) {

      //individual polygons
      for (var p = 0, plen = kde.features.length; p < plen; p++) {
        kde.features[p].properties.time = year;
      };

      //return
      return kde;
    });

    //push
    layers.push(layer);
  };

  //scotland
  if (years.includes(1911)) {
    var path = '/static/kde/sc/scotland/scotland_0.json';
    var scotland = await $j.getJSON(path,function(sct) {

      //individual polygons
      for (var s = 0, slen = sct.features.length; s < slen; s++) {
        sct.features[s].properties.time = -1861920000000;
        sct.features[s].properties.level = 0;
      };

      //return
      return sct;
  });

  //push
  layers.push(scotland);
  };

  //return
  return layers;
};

//render contour
async function renderContour(surname,years) {

  //individual layers
  var layers = await renderLayers(surname,years);

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

//render map
async function renderMap(surname,years,map) {

  //remove previous layer
  if (mapcontrol != undefined) {
      map.removeControl(mapcontrol);
      map.removeLayer(maplayer);
      };

  //geoJSON
  var layer = await renderContour(surname,years);

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
    bounds: lbounds,
  });

  //manage
  mapcontrol = timeDimensionControl;
  maplayer = geoJsonTimeLayer;

  //functions
  stopMapLoad();

  //add
  map.setView([54.505,-4], 6);
  geoJsonTimeLayer.addTo(map);
};
