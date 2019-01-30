// Attibution: SODA API requests based on this example: https://github.com/chriswhong/soda-leaflet
L.TimeDimension.Layer.kdemap = L.TimeDimension.Layer.extend({

    initialize: function(layer,options,surname,year,contour) {
        L.TimeDimension.Layer.prototype.initialize.call(this, layer, options);
        this._currentTimeData = renderMap(this._baseLayer.contour);
        this._currentLoadedTime = 0;
        this._loadingTimeIndex = 0;

        this._surname = this._baseLayer.surname;
        this._year = this._baseLayer.year;
    },

    onAdd: function(map,time) {
        L.TimeDimension.Layer.prototype.onAdd.call(this, map);
        if (this._timeDimension) {
            this._getDataForYear(this._timeDimension.getCurrentTime());
        }
    },

    _onNewTimeLoading: function(ev) {
        this._getDataForYear(ev.time);
        return;
    },

    isReady: function(time) {
        return (this._currentLoadedTime == time);
    },

    _update: function() {
      if (!this._map){
            return;
        }

        if (this._timeDimension) {
          console.log(this._timeDimension);
        }
        var layer = this._currentTimeData;
        console.log(layer);

        if (this._currentLayer) {
            this._map.removeLayer(this._currentLayer);
        }
        layer.addTo(this._map);
        this._currentLayer = layer;
    },

    _getDataForYear: function(time) {
      if (!this._map) {
        return;
      }
      var d = new Date(time).getFullYear();
      var contour = get_update_data(this._surname,d,'In db').then((function(value){

        this._currentTimeData = value;
        this._currentLoadedTime = time;

        console.log(this._currentTimeData);
        console.log(this._currentLoadedTime);

        if (this._timeDimension && time == this._timeDimension.getCurrentTime() && !this._timeDimension.isLoading()) {
            this._update();
        }
      }).bind(this));
      }
    });

function renderSlider(map, data) {

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

  //time layers
  L.timeDimension.layer.timekdemap = function(layer, options, surname, year, contour) {
      return new L.TimeDimension.Layer.kdemap(layer, options, surname, year, contour);
    };

  var surnamelayer = L.timeDimension.layer.timekdemap({
      surname: data.search_sur,
      year: data.data[0],
      contour: data.contourprj,
    });

  //add
  surnamelayer.addTo(map);
};
