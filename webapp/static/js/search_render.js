//render found
function renderHTML(data) {

  var pSearch = document.getElementById('searchParam');
  var eSearch = document.getElementById('searchExtra');
  var foundPar = document.createElement('p');
  var foundExt = document.createElement('p');

  foundPar.id = 'searchParam';
  foundPar.className = 'card-text text-justify top pt-3';
  foundPar.innerHTML = 'You searched for <strong>'+data.clean_sur+'</strong>. Use the slider navigation on the map to switch between the years that are available for your search.';

  foundExt.id = 'searchExtra';
  foundExt.className = 'card-text text-justify top';
  foundExt.innerHTML = 'The polygons on the map indicate the areas in which more than 50 per cent of the surname&quot;s population is concentrated. Note that the differences in sizes of the polygons between consecutive years can be minimal.';

  pSearch.replaceWith(foundPar);
  eSearch.replaceWith(foundExt);
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
function renderMap(data,selYear) {

  //create GeoJSON
  var contour = {
      "type": "Feature",
      "geometry": {
          "type": "MultiPolygon",
          "coordinates": [data]
      }
  };

  //define style
  if (selYear < 1997) {
    var contour_style = {
      color: 'red',
      fillColor: '#f03'
      };
  } else {
    var contour_style = {
      color: 'blue',
      fillColor: '#3273d1'
    }
  };

  //prepare for Leaflet
  var contourJSON = L.geoJSON(contour, {style: contour_style});
  return contourJSON;
};
