//jQuery
var $j = jQuery.noConflict();

//set geography selector
function setGeo(geo) {
  document.getElementById('selLoc').value = geo;
}

//event listener
$j(document).on('submit','#locUser',function(e){
  e.preventDefault();
  var selLoc = document.getElementById('selLoc').value;
  if (selLoc==='user'){
    startLoad();
    getLocation();
  } else {
    startLoad();
    setTimeout(showGeography,1500,selLoc);
  }
});

//start loading indicator
function startLoad() {
  document.getElementById('share-loc').style.display='none';
  document.getElementById('loading-indicator').style.display='inline';
};

//stop loading indicator
function stopLoad() {
  document.getElementById('loading-indicator').style.display='none';
  document.getElementById('share-loc').style.display='inline';
};

//xy through https request
function getLocation() {

    //get location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showLocation);
    }
};

//post location to django backend
function showLocation(position) {
    var lat = position.coords.latitude;
    var lon = position.coords.longitude;

    $j.ajax({
      method: 'POST',
      url: '../udl-namekde/location/',
      // url: '../location/',
      data: {latitude: lat,
            longitude: lon,
            csrfmiddlewaretoken: csrftoken
            },
      success: function (loclist) {
        stopLoad();
        if(loclist){
          renderTopname(loclist);
          renderAlpha(loclist);
          renderUniq(loclist);
          renderLoclist(loclist);
      } else {
          renderNoLoc();
      }}
    })
  };

//post geography to django backend
function showGeography(geography) {

    $j.ajax({
      method: 'POST',
      url: '../udl-namekde/geography/',
      // url: '../geography/',
      data: {geography: geography,
            csrfmiddlewaretoken: csrftoken
            },
      success: function (loclist) {
        stopLoad();
        renderTopname(loclist);
        renderAlpha(loclist);
        renderUniq(loclist);
        renderLoclist(loclist);
      }
    })
  };
