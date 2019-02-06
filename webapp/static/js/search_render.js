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
  foundExt.innerHTML = 'The polygons on the map indicate the areas in which more than 50 per cent of the surname&#39;s population is concentrated. Note that the differences in sizes of the polygons between consecutive years can be minimal.';

  pSearch.replaceWith(foundPar);
  eSearch.replaceWith(foundExt);
};

//render none
async function renderNone(data) {

  //delay
  let promise = new Promise((resolve, reject) => {
    setTimeout(() => resolve(""), 700)
  });
  await promise;
  stopMapLoad();

  var pSearch = document.getElementById('searchParam');
  var noText = document.createElement('p');

  noText.className = 'card-text text-justify top pt-3';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  var foundExt = document.getElementById('searchExtra');
  var searchExt = document.createElement('p');
  searchExt.id = 'searchExtra';

  foundExt.replaceWith(searchExt);
  pSearch.replaceWith(noText);
};

//render not found
async function renderNotFound(data) {

  //delay
  let promise = new Promise((resolve, reject) => {
    setTimeout(() => resolve(""), 1500)
  });
  await promise;
  stopMapLoad();

  var pSearch = document.getElementById('searchParam');
  var notFound = document.createElement('p');

  notFound.className = 'card-text text-justify top pt-3';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+data.search_sur+'</strong> is not in our database. Are you sure you did not make a typo?';

  var foundExt = document.getElementById('searchExtra');
  var searchExt = document.createElement('p');
  searchExt.id = 'searchExtra';

  foundExt.replaceWith(searchExt);
  pSearch.replaceWith(notFound);
};

//render found // first search, before timedimension controller
function renderMap(data,year) {

  //create GeoJSON
  var contour = {
      "type": "Feature",
      "geometry": {
          "type": "MultiPolygon",
          "coordinates": [data]
      }
  };

  //define style
  if (year < 1997) {
    var contour_style = {
      color: '#FA2600',
      fillColor: '#FA2600',
      fillOpacity: .4,
      };
  } else {
    var contour_style = {
      color: '#3273d1',
      fillColor: '#3273d1',
      fillOpacity: .4,
    }
  };

  //prepare for Leaflet
  var contourJSON = L.geoJSON(contour, {style: contour_style});
  return contourJSON;
};
