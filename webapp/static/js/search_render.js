//render none
function renderNone() {

  //stop load
  stopMapLoad();

  //get elements
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var c1Search = document.getElementById('cardFreqHr');
  var c2Search = document.getElementById('cardFreqCr');
  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');

  //create elements
  var noText = document.createElement('p');
  var mapLegend = document.createElement('div');
  var chartCanvas1 = document.createElement('div');
  var chartCanvas2 = document.createElement('div');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');
  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');

  //set elements
  noText.className = 'p-3 mb-2 bg-orange text-dark';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  mapLegend.id = 'mapLegend';

  chartCanvas1.id = 'cardFreqHr';
  chartCanvas1.className = 'card-body p-2';
  chartCanvas2.id = 'cardFreqCr';
  chartCanvas2.className = 'card-body p-2';

  foreNamesF.id = 'ForeNamesFemale';
  foreNamesM.id = 'ForeNamesMale';
  foreFemaleLegend.id = 'foreFemaleLegend';
  foreMaleLegend.id = 'foreMaleLegend';

  //replace
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

  //remove previous map layer if exist
  if (control != undefined) {
      map.removeControl(control);
      map.removeLayer(layer_rm);
      };
    };

//render not found
function renderNotFound(surname) {

  //stop load
  stopMapLoad();

  //get elements
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var c1Search = document.getElementById('cardFreqHr');
  var c2Search = document.getElementById('cardFreqCr');
  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');

  //create elements
  var notFound = document.createElement('p');
  var mapLegend = document.createElement('div');
  var chartCanvas1 = document.createElement('div');
  var chartCanvas2 = document.createElement('div');
  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');

  //set elements
  notFound.className = 'p-3 mb-2 bg-orange text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+surname+'</strong> is not in our database. Are you sure you did not make a typo?';

  mapLegend.id = 'mapLegend';

  chartCanvas1.id = 'cardFreqHr';
  chartCanvas1.className = 'card-body p-2';
  chartCanvas2.id = 'cardFreqCr';
  chartCanvas2.className = 'card-body p-2';

  foreNamesF.id = 'ForeNamesFemale';
  foreNamesM.id = 'ForeNamesMale';
  foreFemaleLegend.id = 'foreFemaleLegend';
  foreMaleLegend.id = 'foreMaleLegend';

  //replace
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

  //remove previous map layer if exist
  if (control != undefined) {
      map.removeControl(control);
      map.removeLayer(layer_rm);
      };
};

//render found
function renderHTML(surname) {

  //get elements
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');

  //create elements
  var foundPar = document.createElement('h1');
  var mapLegend = document.createElement('div');

  //set elements
  foundPar.id = 'searchParam';
  foundPar.innerHTML = surname.toUpperCase();

  mapLegend.id = 'mapLegend';
  mapLegend.className = 'card-footer small text-muted text-justify p-3';
  mapLegend.innerHTML = 'The red lines enclose the areas where 50% of name bearers lived over the period 1851-1911, where we have the historic Census data. The blue lines show the much more recent distributions.';

  //replace
  pSearch.replaceWith(foundPar);
  lSearch.replaceWith(mapLegend);

  //back to names tablist
  $('#nav-tab a[href="#names"]').tab('show');
};

//render forenames
function renderForenames(fmh,ffh,fmc,ffc) {

  //get elements
  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');

  //create elements
  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');

  //set elements
  foreNamesF.id = 'ForeNamesFemale';
  foreNamesF.className = 'list-inline ml-3 mt-2 mr-3 mb-3';
  foreNamesM.id = 'ForeNamesMale';
  foreNamesM.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  foreFemaleLegend.id = 'foreFemaleLegend';
  foreFemaleLegend.className = 'card-footer small text-muted text-justify p-3';
  foreFemaleLegend.innerHTML = 'Female forenames with highest frequency in the period 1851-1911 (red) and in recent years (blue).';
  foreMaleLegend.id = 'foreMaleLegend';
  foreMaleLegend.className = 'card-footer small text-muted text-justify p-3';
  foreMaleLegend.innerHTML = 'Male forenames with highest frequency in the period 1851-1911 (red) and in recent years (blue).';

  //hist buttons female
  for (var i = 0; i < ffh.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = ffh[i].toUpperCase();
    li.className = 'btn btn-historic mt-2 mr-1';
    foreNamesF.appendChild(li);
  };

  //cont buttons female
  for (var i = 0; i < ffc.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = ffc[i].toUpperCase();
    li.className = 'btn btn-contemporary mt-2 mr-1';
    foreNamesF.appendChild(li);
  };

  //hist buttons male
  for (var i = 0; i < fmh.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = fmh[i].toUpperCase();
    li.className = 'btn btn-historic mt-2 mr-1';
    foreNamesM.appendChild(li);
  };

  //cont buttons female
  for (var i = 0; i < fmc.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = fmc[i].toUpperCase();
    li.className = 'btn btn-contemporary mt-2 mr-1';
    foreNamesM.appendChild(li);
  };

  //replace
  foreFemale.replaceWith(foreNamesF);
  foreMale.replaceWith(foreNamesM);
  fLegend.replaceWith(foreFemaleLegend);
  mLegend.replaceWith(foreMaleLegend);
};

//render top parish
function renderParish(partop) {

  //get, create, set, elements
  var pPar = document.getElementById('topParish');
  var topPar = document.createElement('ul');
  topPar.id = 'topParish';
  topPar.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  //parish buttons
  for (var i = 0; i < partop.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = partop[i];
    li.className = 'btn btn-outline-secondary mt-2 mr-1';
    topPar.appendChild(li);
  };

  //replace
  pPar.replaceWith(topPar);
};

//render top oa
function renderOA(oatop) {

  //get, create, set, elements
  var pOA = document.getElementById('topOA');
  var topOA = document.createElement('ul');
  topOA.id = 'topOA';
  topOA.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  //oa buttons
  for (var i = 0; i < oatop.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = oatop[i];
    li.className = 'btn btn-outline-secondary mt-2 mr-1';
    topOA.appendChild(li);
  };

  //replace
  pOA.replaceWith(topOA);
};
