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

function renderMap(years,contours,cmap) {

  //remove previous layer
  if (control != undefined) {
      cmap.removeControl(control);
      cmap.removeLayer(layer_rm);
      };

  //geoJSON
  var layer = renderContour(years,contours);
  cmap.fitBounds(layer.getBounds().pad(0,1));

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
