//render HTML
function renderHTML(data) {

  var pSearch = document.getElementById('searchParam');
  var foundPar = document.createElement('p');
  var foundForm = document.createElement('form');
  var foundList = document.createElement('select');

  foundPar.id = 'searchParam';
  foundPar.className = 'card-text text-justify top pt-3';
  foundPar.innerHTML = 'You searched for <strong>'+data.clean_sur+'</strong>.';

  pSearch.replaceWith(foundPar);

};

//render none
function renderNone(data) {

  var pSearch = document.getElementById('searchParam');
  var noText = document.createElement('p');

  noText.className = 'card-text text-justify top pt-3';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  pSearch.replaceWith(noText);
};

//render not found
function renderNotFound(data) {

  var pSearch = document.getElementById('searchParam');
  var notFound = document.createElement('p');

  notFound.className = 'card-text text-justify top pt-3';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+data.search_sur+'</strong> is not in our database. Are you sure you did not make a typo?';

  pSearch.replaceWith(notFound);
};

//render found // first search, before timedimension controller
function renderMap(data) {

  //create GeoJSON
  var contour = {
      "type": "Feature",
      "geometry": {
          "type": "MultiPolygon",
          "coordinates": [data]
      }
  };

  //define style
  var contour_style = {
    color: 'red',
    fillColor: '#f03'
  };

  //prepare for Leaflet
  var contourJSON = L.geoJSON(contour, {style: contour_style});
  return contourJSON;
};
