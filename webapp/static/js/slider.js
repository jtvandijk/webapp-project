// Attibution: SODA API requests based on this example: https://github.com/chriswhong/soda-leaflet
L.TimeDimension.Layer.kdemap = L.TimeDimension.Layer.extend({

    initialize: function(layer,options,surname,contour) {
        L.TimeDimension.Layer.prototype.initialize.call(this, layer, options);
        this._currentLoadedTime = 0;
        this._currentTimeData = null;
        this._surname = this._baseLayer.surname;
    },

    // onAdd: function(map) {
    //     L.TimeDimension.Layer.prototype.onAdd.call(this, map);
    //     if (this._timeDimension) {
    //         this._getDataForTime(this._timeDimension.getCurrentTime());
    //     }
    // },

    _onNewTimeLoading: function(ev) {
        this._getDataForYear(ev.time);
        return;
    },

    isReady: function(time) {
        return (this._currentLoadedTime == time);
    },

    _update: function() {
        // if (!this._map)
        //     return;
        // var layer = L.geoJson(this._currentTimeData, this._baseLayer.options);
        // if (this._currentLayer) {
        //     this._map.removeLayer(this._currentLayer);
        // }
        // layer.addTo(this._map);
        // this._currentLayer = layer;
    },

    _getDataForYear: function(time,option,surname,contour) {
      var d = new Date(time).getFullYear();
      var update_data = get_update_data(this._surname,d,'In db');

      console.log(d);
      console.log(this._baseLayer.surname);
      console.log(update_data);
    },

    _getDataForTime: function(time) {
           if (!this._map) {
               return;
           }
           //var d = new Date(time).getFullYear();
           // var callback = function(status, data) {
           //     if (status == 'ok'){
           //         this._currentTimeData = data;
           //     } else{
           //         this._currentTimeData = [];
           //     }
           //     this._currentLoadedTime = time;
           //     if (this._timeDimension && time == this._timeDimension.getCurrentTime() && !this._timeDimension.isLoading()) {
           //         this._update();
           //     }
           //     this.fire('timeload', {
           //         time: time
           //     });
           // };
           //this._currenTimeData = get_update_data(surname, d , 'In db')

           //var update_data = get_data(surname,d,'In db');
           //console.log(d);
           //console.log(update_data);

           //

           // update_data.then(function(value){
           //   var update_sel_contour = renderMap(value);
           //   map.addLayer(update_sel_contour);
           // });

        },
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
  L.timeDimension.layer.timekdemap = function(layer, options, surname, contour) {
      return new L.TimeDimension.Layer.kdemap(layer, options, surname, contour);
    };

  var surnamelayer = L.timeDimension.layer.timekdemap({
      surname: data.search_sur,
      contour: data.contourprj,
    });

  console.log(surnamelayer);
  //add
  surnamelayer.addTo(map);
};
