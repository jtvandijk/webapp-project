//render none
function renderNone() {

  //stop load
  stopMapLoad();

  //render empty search
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var noText = document.createElement('p');
  var mapLegend = document.createElement('div');

  noText.className = 'p-3 mb-2 bg-orange text-dark';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  mapLegend.id = 'mapLegend';

  pSearch.replaceWith(noText);
  lSearch.replaceWith(mapLegend);

  //remove previous layer if exist
  if (control != undefined) {
      map.removeControl(control);
      map.removeLayer(layer_rm);
      };
};

//render not found
function renderNotFound(surname) {

  //stop load
  stopMapLoad();

  //render not found
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var notFound = document.createElement('p');
  var mapLegend = document.createElement('div');

  notFound.className = 'p-3 mb-2 bg-orange text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+surname+'</strong> is not in our database. Are you sure you did not make a typo?';

  mapLegend.id = 'mapLegend';

  pSearch.replaceWith(notFound);
  lSearch.replaceWith(mapLegend);

  //remove previous layer if exist
  if (control != undefined) {
      map.removeControl(control);
      map.removeLayer(layer_rm);
      };
};

//render found
function renderHTML(surname) {

  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var foundPar = document.createElement('h1');
  var mapLegend = document.createElement('div');

  foundPar.id = 'searchParam';
  foundPar.innerHTML = surname.toUpperCase();

  mapLegend.id = 'mapLegend';
  mapLegend.className = 'card-footer small text-muted text-justify p-3'
  mapLegend.innerHTML = 'The red lines enclose the areas where 50% of name bearers lived over the period 1851-1911, where we have the historic Census data. The blue lines show the much more recent distributions.'

  pSearch.replaceWith(foundPar);
  lSearch.replaceWith(mapLegend);
};
