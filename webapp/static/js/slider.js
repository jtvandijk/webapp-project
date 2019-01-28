// Attibution: SODA API requests based on this example: https://github.com/chriswhong/soda-leaflet
L.TimeDimension.Layer.kdemap = L.TimeDimension.Layer.extend({

    initialize: function(options,data) {
        var heatmapCfg = this._getHeatmapOptions(options.heatmatOptions || {});
        var layer = new HeatmapOverlay(heatmapCfg);
        L.TimeDimension.Layer.prototype.initialize.call(this, layer, options);
        this._currentLoadedTime = 0;
        this._currentTimeData = {
            max: this.options.heatmapMax || 10,
            data: []
        };
        this._baseURL = this.options.baseURL || null;
        this._period = this.options.period || "P1M";
    },

    _getHeatmapOptions: function(options) {
        var config = {};
        var defaultConfig = {
            radius: 15,
            maxOpacity: .8,
            scaleRadius: false,
            useLocalExtrema: false,
            latField: 'lat',
            lngField: 'lng',
            valueField: 'count'
        };
        for (var attrname in defaultConfig) {
            config[attrname] = defaultConfig[attrname];
        }
        for (var attrname in options) {
            config[attrname] = options[attrname];
        }
        return config;
    },

    onAdd: function(map) {
        L.TimeDimension.Layer.prototype.onAdd.call(this, map);

        //
        var data = this.options.data;
        var sel_contour = renderMap(data);
        map.addLayer(sel_contour);
        //

        map.addLayer(this._baseLayer);
        console.log('on add');
        if (this._timeDimension) {
            this._getDataForTime(this._timeDimension.getCurrentTime());
        }
    },

    _onNewTimeLoading: function(ev) {
        this._getDataForTime(ev.time);
        this._updateDataForYear(map,ev.time);
        console.log('new time');
        return;
    },

    _updateDataForYear: async function() {

        //
        var update_data = get_update_data(this.options.data.search_sur,1998,'In db');
        update_data.then(function(value){
          var update_sel_contour = renderMap(value);
          map.addLayer(update_sel_contour);
        });
        //

    },

    isReady: function(time) {
        return (this._currentLoadedTime == time);
    },

    _update: function() {
        this._baseLayer.setData(this._currentTimeData);
        return true;
    },

    _getDataForTime: function(time) {
        if (!this._baseURL || !this._map) {
            return;
        }
        var url = this._constructQuery(time);
        var oReq = new XMLHttpRequest();
        oReq.addEventListener("load", (function(xhr) {
            var response = xhr.currentTarget.response;
            var data = JSON.parse(response);
            delete this._currentTimeData.data;
            this._currentTimeData.data = [];
            for (var i = 0; i < data.length; i++) {
                var marker = data[i];
                if (marker.location) {
                    this._currentTimeData.data.push({
                        lat: marker.location.latitude,
                        lng: marker.location.longitude,
                        count: 1
                    });
                }
            }
            this._currentLoadedTime = time;
            if (this._timeDimension && time == this._timeDimension.getCurrentTime() && !this._timeDimension.isLoading()) {
                this._update();
            }
            this.fire('timeload', {
                time: time
            });
        }).bind(this));

        oReq.open("GET", url);
        oReq.send();

    },

    _constructQuery: function(time) {
        var bbox = this._map.getBounds();
        var sodaQueryBox = [bbox._northEast.lat, bbox._southWest.lng, bbox._southWest.lat, bbox._northEast.lng];

        var startDate = new Date(time);
        var endDate = new Date(startDate.getTime());
        L.TimeDimension.Util.addTimeDuration(endDate, this._period, false);

        var where = "&$where=created_date > '" +
            startDate.format('yyyy-mm-dd') +
            "' AND created_date < '" +
            endDate.format('yyyy-mm-dd') +
            "' AND within_box(location," +
            sodaQueryBox +
            ")&$order=created_date desc";

        var url = this._baseURL + where;
        return url;
    }

});


function renderSlider(map, data) {

  //set up years
  var years = ''
  for (var i = 0; i < data.data.length - 1; ++i) {
    years = years + data.data[i] + ',';
  };
  var years = years + data.data[data.data.length-1]


  Date.prototype.format = function (mask, utc) {
      return dateFormat(this, mask, utc);
  };

  L.timeDimension.layer.timekdemap = function(options, data) {
      return new L.TimeDimension.Layer.kdemap(options, data);
  };

  var sel_contour = renderMap(data);
  console.log(sel_contour);

  var testSODALayer = L.timeDimension.layer.timekdemap({
      baseURL: 'https://data.cityofnewyork.us/resource/erm2-nwe9.json?$select=location,closed_date,complaint_type,street_name,created_date,status,unique_key,agency_name,due_date,descriptor,location_type,agency,incident_address&complaint_type=Noise - Commercial',
      data: data,});

  testSODALayer.addTo(map);

  L.Control.TimeDimensionCustom = L.Control.TimeDimension.extend({
      _getDisplayDateFormat: function(date){
          return date.format("mmmm yyyy");
      }
  });

  var timeDimensionControl = new L.Control.TimeDimensionCustom({
      playerOptions: {
          buffer: 1,
          minBufferReady: -1
      }
  });

    var timeDimension = new L.TimeDimension({
            times: years,
        });

    var player = new L.TimeDimension.Player({
        transitionTime: 100,
        loop: false,
        startOver:true
    }, timeDimension);

    //player options
    var timeDimensionControlOptions = {
        player: player,
        timeDimension: timeDimension,
        position: 'topright',
        autoPlay: false,
        speedSlider: false,
        timeSliderDragUpdate: false,
    };

  var timeDimensionControl2 = new L.Control.TimeDimension(timeDimensionControlOptions);


    //instantiate TimeDimension
    var timeDimension = new L.TimeDimension({
            times: years,
        });

  map.addControl(timeDimensionControl);
  map.addControl(timeDimensionControl2);

};







// //slider
// function renderSlider(data) {
//
//   //set up years
//   var years = ''
//   for (var i = 0; i < data.data.length - 1; ++i) {
//     years = years + data.data[i] + ',';
//   };
//   var years = years + data.data[data.data.length]
//
//   //instantiate TimeDimension
//   var timeDimension = new L.TimeDimension({
//           times: years,
//       });
//
//   //set to first available year
//   timeDimension.setCurrentTime(timeDimension.getAvailableTimes()[0]);
//
//   //data
//   var contourData = renderMap(data);
//
//   //instantiate TimeDimension layer
//   L.TimeDimension.Layer.kdemap = L.TimeDimension.Layer.extend({
//
//       initialize: function() {
//         L.TimeDimension.Layer.prototype.initialize.call(this);
//         console.log('init');
//         return;
//       },
//
//       onAdd: function(map) {
//         L.TimeDimension.Layer.prototype.onAdd.call(this, map);
//         map.addLayer(contourData);
//         console.log('add');
//         return;
//       },
//
//       _onNewTimeLoading: function(ev) {
//           console.log('new_time');
//           return;
//       },
//
//       _update: function(ev) {
//         console.log('update');
//       },
//
//       isReady: function(time) {
//         console.log('isready');
//       },
//
//
//     });
//
//   //player
//   var player = new L.TimeDimension.Player({
//       transitionTime: 100,
//       loop: false,
//       startOver:true
//   }, timeDimension);
//
//   //player options
//   var timeDimensionControlOptions = {
//       player: player,
//       timeDimension: timeDimension,
//       position: 'topright',
//       autoPlay: false,
//       speedSlider: false,
//       timeSliderDragUpdate: false,
//   };
//
//   //contour layer
//   L.timeDimension.layer.timekdemap = function() {
//       return new L.TimeDimension.Layer.kdemap();
//   };
//
//   //add
//   var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);
//   var contourLayer = L.timeDimension.layer.timekdemap({});
//
//   contourLayer.addTo(map);
//   map.addControl(timeDimensionControl);
//
// };
