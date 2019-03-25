//render none
function renderNone() {

  //stop load
  stopMapLoad();

  //render empty search
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var c1Search = document.getElementById('cardFreqHr');
  var c2Search = document.getElementById('cardFreqCr');
  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');

  var noText = document.createElement('p');
  var chartCanvas1 = document.createElement('div');
  var chartCanvas2 = document.createElement('div');
  var mapLegend = document.createElement('div');
  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');

  foreNamesF.id = 'ForeNamesFemale';
  foreNamesM.id = 'ForeNamesMale';

  foreFemaleLegend.id = 'foreFemaleLegend';
  foreMaleLegend.id = 'foreMaleLegend';

  noText.className = 'p-3 mb-2 bg-orange text-dark';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  mapLegend.id = 'mapLegend';
  chartCanvas1.id = 'cardFreqHr';
  chartCanvas1.className = 'card-body p-2'
  chartCanvas2.id = 'cardFreqCr';
  chartCanvas2.className = 'card-body p-2'

  pSearch.replaceWith(noText);
  lSearch.replaceWith(mapLegend);
  c1Search.replaceWith(chartCanvas1);
  c2Search.replaceWith(chartCanvas2);
  foreFemale.replaceWith(foreNamesF);
  foreMale.replaceWith(foreNamesM);
  fLegend.replaceWith(foreFemaleLegend);
  mLegend.replaceWith(foreMaleLegend);

  //back to names tablist
  $('#nav-tab a[href="#names"]').tab('show');

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
  var c1Search = document.getElementById('cardFreqHr');
  var c2Search = document.getElementById('cardFreqCr');
  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');

  var notFound = document.createElement('p');
  var chartCanvas1 = document.createElement('div');
  var chartCanvas2 = document.createElement('div');
  var mapLegend = document.createElement('div');
  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');

  foreNamesF.id = 'ForeNamesFemale';
  foreNamesM.id = 'ForeNamesMale';

  foreFemaleLegend.id = 'foreFemaleLegend';
  foreMaleLegend.id = 'foreMaleLegend';

  notFound.className = 'p-3 mb-2 bg-orange text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+surname+'</strong> is not in our database. Are you sure you did not make a typo?';

  mapLegend.id = 'mapLegend';
  chartCanvas1.id = 'cardFreqHr';
  chartCanvas1.className = 'card-body p-2'
  chartCanvas2.id = 'cardFreqCr';
  chartCanvas2.className = 'card-body p-2'

  pSearch.replaceWith(notFound);
  lSearch.replaceWith(mapLegend);
  c1Search.replaceWith(chartCanvas1);
  c2Search.replaceWith(chartCanvas2);
  foreFemale.replaceWith(foreNamesF);
  foreMale.replaceWith(foreNamesM);
  fLegend.replaceWith(foreFemaleLegend);
  mLegend.replaceWith(foreMaleLegend);

  //back to names tablist
  $('#nav-tab a[href="#names"]').tab('show');

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

  //back to names tablist
  $('#nav-tab a[href="#names"]').tab('show');

  pSearch.replaceWith(foundPar);
  lSearch.replaceWith(mapLegend);
};

//render forenames
function renderForenames(fmh,ffh,fmc,ffc) {

  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');

  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');

  foreNamesF.id = 'ForeNamesFemale';
  foreNamesF.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  foreNamesM.id = 'ForeNamesMale';
  foreNamesM.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  //hist
  for (var i = 0; i < ffh.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = ffh[i].toUpperCase();
    li.className = 'btn btn-historic mt-2 mr-1';
    foreNamesF.appendChild(li);
  };

  //cont
  for (var i = 0; i < ffc.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = ffc[i].toUpperCase();
    li.className = 'btn btn-contemporary mt-2 mr-1';
    foreNamesF.appendChild(li);
  };

  //hist
  for (var i = 0; i < fmh.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = fmh[i].toUpperCase();
    li.className = 'btn btn-historic mt-2 mr-1';
    foreNamesM.appendChild(li);
  };

  //cont
  for (var i = 0; i < fmc.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = fmc[i].toUpperCase();
    li.className = 'btn btn-contemporary mt-2 mr-1';
    foreNamesM.appendChild(li);
  };

  //legend
  foreFemaleLegend.id = 'foreFemaleLegend';
  foreFemaleLegend.className = 'card-footer small text-muted text-justify p-3';
  foreFemaleLegend.innerHTML = 'Female forenames with highest frequency in the period 1851-1911 (red) and in recent years (blue).';

  foreMaleLegend.id = 'foreMaleLegend';
  foreMaleLegend.className = 'card-footer small text-muted text-justify p-3';
  foreMaleLegend.innerHTML = 'Male forenames with highest frequency in the period 1851-1911 (red) and in recent years (blue).';

  //replace
  foreFemale.replaceWith(foreNamesF);
  foreMale.replaceWith(foreNamesM);
  fLegend.replaceWith(foreFemaleLegend);
  mLegend.replaceWith(foreMaleLegend);
};
