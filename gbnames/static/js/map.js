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

//zoom
L.easyButton('fas fa-arrows-alt', function(btn, map){
    cmap.setView([54.505,-4], 6);
}).addTo(cmap)

//countries
//$j.getJSON(ireland_gjson,function (data) {L.geoJSON(data,{weight:0,fillColor:'#DCDCDC',fillOpacity:'.8'}).addTo(cmap);});

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

//global
var control;
var layer_rm;

L.TimeDimension.Layer.GeoJson.GeometryCollection = L.TimeDimension.Layer.GeoJson.extend({

  _getFeatureBetweenDates: function(feature, minTime, maxTime) {
      var featureStringTimes = this._getFeatureTimes(feature);
         if (featureStringTimes.length == 0) {
             return feature;
         }
         var featureTimes = [];
         for (var i = 0, l = featureStringTimes.length; i < l; i++) {
             var time = featureStringTimes[i]
             if (typeof time == 'string' || time instanceof String) {
                 time = Date.parse(time.trim());
             }
             featureTimes.push(time);
         }

         if (featureTimes[0] > maxTime || featureTimes[l - 1] < minTime) {
             return null;
         }
         return feature;
     },
});

L.timeDimension.layer.geoJson.geometryCollection = function(layer, options) {
    return new L.TimeDimension.Layer.GeoJson.GeometryCollection(layer, options);
};

function renderMap(years,contours,nireland,cmap) {

  //remove previous layer
  if (control != undefined) {
      cmap.removeControl(control);
      cmap.removeLayer(layer_rm);
      };

  //geoJSON
  var layer = renderContour(years,contours,nireland);
  cmap.setView([54.505, -4], 6);

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
  cmap.timeDimension = timeDimension;
  cmap.addControl(timeDimensionControl);

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
  geoJsonTimeLayer.addTo(cmap);
};
