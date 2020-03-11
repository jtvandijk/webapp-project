//global
var control;
var layer_rm;

//basemap
var map = L.map('kdemap').setView([54.505,-4],6);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | \n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
             minZoom: 6,
             maxZoom: 7,
           }).addTo(map);

//bounds
var southWest = L.latLng(62.0,4.05),
    northEast = L.latLng(50.0,-12,01),
    bounds = L.latLngBounds(southWest,northEast);
    map.setMaxBounds(bounds);

//zoom
L.easyButton('fas fa-arrows-alt', function(btn,map){
    map.setView([54.505,-4],6);
}).addTo(map)

//kde
function loadControl(surname,years,map) {

  //surname
  window.surname=surname;

  //remove previous control if exist
  if (control != undefined) {
      map.removeControl(control);
      };

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
      transitionTime: 1800,
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

  //manage
  control = timeDimensionControl;
};

//slider
document.addEventListener("slide", function(e) {
  var year = e.detail;
  slideKDE(surname,year,map);
});

//KDE
function slideKDE(surname,year,map) {

  //remove previous layer if exist
  if (layer_rm != undefined) {
      map.removeLayer(layer_rm);
      };

  //add layer
  var fld =  surname.slice(0,1).toLowerCase(),
      png = 'static/kde/' + fld + '/' + surname.toLowerCase() + '/kde' + year + '.png',
      imageBounds = [[61.07083,3.181498],[49.55891,-9.806102]];

  var name_layer = L.imageOverlay(png,imageBounds,
                {opacity: 0.8,
                 minZoom: 6,
                 maxZoom: 10,
  }).addTo(map);

  //increase opacity
  //increase_opacity(name_layer)

  //name layer
  layer_rm = name_layer;
};

//pretty load
function increase_opacity(layer) {
  var t = 0;
  var id = setInterval(opacity_plus,20);
  function opacity_plus() {
    if (t == 60) {
      clearInterval(id);
    } else {
      t++;
      var o = 0.1 + (0.01*t);
      layer.setOpacity(o);
  }};
};
