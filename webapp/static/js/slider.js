//timedimension layer
L.TimeDimension.Layer.kdemap = L.TimeDimension.Layer.extend({

  initialize: function(options) {
    L.TimeDimension.Layer.prototype.initialize.call(this, options);
    this._currentTimeData = renderMap(this._baseLayer.contour,this._baseLayer.year);
    this._surname = this._baseLayer.surname;
    this._year = this._baseLayer.year;
    },

  _onNewTimeLoading: function(ev) {
    this._getData(ev.time);
    return;
    },

  isReady: function(time) {
    return (this._currentLoadedTime == time);
    },

  _update: function() {

    if (this._currentLayer) {
      this._map.removeLayer(this._currentLayer);
    }

    var layer = this._currentTimeData;
    layer.addTo(this._map);
    map.fitBounds(layer.getBounds());
    this._currentLayer = layer;
    layerm=layer
    },

  _getData: function(time) {

    var d = new Date(time).getFullYear();
    var contour = get_update_data(this._surname,d,'In db').then((function(value){
      this._currentTimeData = value;
      this._currentLoadedTime = time;
      this._update();
      }).bind(this));
    },

  });

function renderSlider(map,data) {

  //remove control
  if (control != undefined) {
     map.removeControl(control);
     map.removeLayer(layerm);
     }

  //set up years
  var years = '';
  for (var i = 0; i < data.data.length - 1; ++i) {
    years = years + data.data[i] + ',';
    };
  var years = years + data.data[data.data.length-1];

  //set up time dimension
  var timeDimension = new L.TimeDimension({
      times: years,
    });

  //set time dimension to map
  map.timeDimension = timeDimension;
  timeDimension.setCurrentTime(timeDimension.getAvailableTimes()[0]);

  //  set up player
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
  map.addControl(timeDimensionControl);

  //time layers
  L.timeDimension.layer.timekdemap = function(options) {
      return new L.TimeDimension.Layer.kdemap(options);
    };

  var surnamelayer = L.timeDimension.layer.timekdemap({
      surname: data.search_sur,
      year: data.data[0],
      contour: data.contourprj,
    });

  //manage
  control = timeDimensionControl;
  layer = surnamelayer;

  //add
  map.addLayer(surnamelayer);

};

function renderMap(years,contours,map) {

  //geoJSON
  var layer = renderContour(years,contours);
  console.log(layer);

  layer.addTo(map);
  //L.timeDimension.layer.geoJson(layer).addTo(map);

  //set up years
  var slider = '';
  for (var i = 0; i < years - 1; ++i) {
    slider = slider + years[i] + ',';
    };
  var slider = slider + years[years.length-1];

  //set up time dimension
  var timeDimension = new L.TimeDimension({
      times: slider,
    });

  //set time dimension to map
  map.timeDimension = timeDimension;

  // set up player
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
  map.addControl(timeDimensionControl);
}
