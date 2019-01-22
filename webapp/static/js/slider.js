//time slider
var timeDimension = new L.TimeDimension({});

//player
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
    timeSliderDragUpdate: false
};

var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);
kdemap.addControl(timeDimensionControl);
