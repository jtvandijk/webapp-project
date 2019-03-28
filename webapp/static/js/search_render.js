//render none
function renderNone() {

  //functions
  stopMapLoad();
  clearPage();

  //get elements
  var pSearch = document.getElementById('searchParam');
  var pLocation = document.getElementById('locParam');

  //create elements
  var noText = document.createElement('p');
  var noLoc = document.createElement('p');

  //set elements
  noText.className = 'p-3 mb-2 bg-orange text-dark';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  noLoc.className = 'p-3 mb-2 bg-orange text-dark';
  noLoc.id = 'locParam';
  noLoc.textContent = 'Please type in a surname before hitting submit.';

  //replace
  pSearch.replaceWith(noText);
  pLocation.replaceWith(noLoc);
};

//render not found
function renderNotFound(surname) {

  //functions
  stopMapLoad();
  clearPage();

  //get elements
  var pSearch = document.getElementById('searchParam');
  var pLocation = document.getElementById('locParam');

  //create elements
  var notFound = document.createElement('p');
  var notLoc = document.createElement('p');

  //set elements
  notFound.className = 'p-3 mb-2 bg-orange text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+surname+'</strong> is not in our database. Are you sure you did not make a typo?';

  notLoc.className = 'p-3 mb-2 bg-orange text-dark';
  notLoc.id = 'locParam';
  notLoc.textContent = 'Please type in a surname before hitting submit.';

  //replace
  pSearch.replaceWith(notFound);
  pLocation.replaceWith(notLoc);
};

//render found
function renderHTML(surname) {

  //get elements
  var pSearch = document.getElementById('searchParam');
  var pLocation = document.getElementById('locParam');
  var lSearch = document.getElementById('mapLegend');

  //create elements
  var foundPar = document.createElement('h1');
  var foundLoc = document.createElement('h1');
  var mapLegend = document.createElement('div');

  //set elements
  foundPar.id = 'searchParam';
  foundPar.innerHTML = surname.toUpperCase();

  foundLoc.id = 'locParam';
  foundLoc.innerHTML = surname.toUpperCase();

  mapLegend.id = 'mapLegend';
  mapLegend.className = 'card-footer small text-muted text-justify p-3';
  mapLegend.innerHTML = 'The red lines enclose the areas where 50% of name bearers lived over the period 1851-1911, where we have the historic Census data. The blue lines show the much more recent distributions.';

  //replace
  pSearch.replaceWith(foundPar);
  lSearch.replaceWith(mapLegend);
  pLocation.replaceWith(foundLoc);

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
  var pPar = document.getElementById('topPar');
  var topPar = document.createElement('ul');
  topPar.id = 'topPar';
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

//render modal oa cat
function renderCAT(oacat) {

  //get elements
  var sgButton = document.getElementById('sgCat');
  var gButton = document.getElementById('gCat');

  //create elements
  var sgDiv = document.createElement('div');
  var gDiv = document.createElement('div');
  var sgDivbtn = document.createElement('button');
  var gDivbtn = document.createElement('button');

  //set elements
  sgDiv.id = 'sgCat';
  gDiv.id = 'gCat';
  sgDiv.className = 'card-body p-2';
  gDiv.className = 'card-body p-2';

  //classname
  cls = oacat[2].slice(0,1);

  //values
  sgDivbtn.className = 'btn btn-g'+cls+' btn-lg btn-block';
  gDivbtn.className = 'btn btn-g'+cls+' sub btn-lg btn-block';
  sgDivbtn.innerHTML = oacat[0];
  gDivbtn.innerHTML = oacat[1];
  sgDiv.appendChild(sgDivbtn);
  gDiv.appendChild(gDivbtn);

  //replace
  sgButton.replaceWith(sgDiv);
  gButton.replaceWith(gDiv);
  };

//render modal oa ahah
function renderHealth(oahlth) {

  //remove select
  removeSelect('hlth',11);

  //table
  document.getElementById('AHAH').style.display='block';

  //get elements
  var id = 'hlth'+oahlth.toString();
  var hlthcat = document.getElementById(id);

  //select
  hlthcat.className = 'btn btn-h'+oahlth.toString()+' btn-sm btn-block btn-select p-0 m-0';
  };

//render modal oa imd
function renderIMD(oaimd) {

  //remove select
  removeSelect('imd',11);

  //table
  document.getElementById('IMD').style.display='block';

  //get elements
  var id = 'imd'+oaimd.toString();
  var imdcat = document.getElementById(id);

  //select
  imdcat.className = 'btn btn-l'+oaimd.toString()+' btn-sm btn-block btn-select p-0 m-0';
  };

//render modal oa bband
function renderBBAND(bband) {

  //remove selected
  removeSelect('bband',12);

  //table
  document.getElementById('BBAND').style.display='block';

  //get elements
  var id = 'bband'+bband.toString();
  var bbcat = document.getElementById(id);

  //select
  bbcat.className = 'btn btn-b'+bband.toString()+' btn-sm btn-block btn-select p-0 m-0';
  };

function renderIUC(iuc) {

  //get elements
  var iucEl = document.getElementById('IUC');

  //create elements
  var iucDiv = document.createElement('div');
  var iucBtn = document.createElement('button');

  //set elements
  iucDiv.id = 'IUC';
  iucDiv.className = 'card-body p-2';

  //classname
  cls = iuc[0];

  //values
  iucBtn.className = 'btn btn-iuc'+cls+' btn-lg btn-block';
  iucBtn.innerHTML = iuc[1];
  iucDiv.appendChild(iucBtn);

  //replace
  iucEl.replaceWith(iucDiv);
};

function renderCRVUL(crvul) {

  //get elements
  var crvulEl = document.getElementById('CRVUL');

  //create elements
  var crvulDiv = document.createElement('div');
  var crvulBtn = document.createElement('button');

  //set elements
  crvulDiv.id = 'CRVUL';
  crvulDiv.className = 'card-body p-2';

  //classname
  cls = crvul[0];

  //values
  crvulBtn.className = 'btn btn-crvul'+cls+' btn-lg btn-block';
  crvulBtn.innerHTML = crvul[1];
  crvulDiv.appendChild(crvulBtn);

  //replace
  crvulEl.replaceWith(crvulDiv);
};

//remove select
function removeSelect(rem,n) {

  //loop
  for (var i = 1; i < n; ++i) {
    var id = rem+i.toString();
    var remcat = document.getElementById(id);
    remcat.classList.remove('btn-select');
    };
  };

//clear page
function clearPage() {

  //get elements
  var lSearch = document.getElementById('mapLegend');
  var foreFemale = document.getElementById('ForeNamesFemale');
  var foreMale = document.getElementById('ForeNamesMale');
  var fLegend = document.getElementById('foreFemaleLegend');
  var mLegend = document.getElementById('foreMaleLegend');
  var pPar = document.getElementById('topPar');
  var pOA = document.getElementById('topOA');
  var sgCat = document.getElementById('sgCat');
  var gCat = document.getElementById('gCat');
  var tableHR = document.getElementById('tableHR');
  var tableCR = document.getElementById('tableCR');
  var iucEl = document.getElementById('IUC');
  var crvulEl = document.getElementById('CRVUL');

  //create elements
  var mapLegend = document.createElement('div');
  var foreMaleLegend = document.createElement('div');
  var foreFemaleLegend = document.createElement('div');
  var foreNamesF = document.createElement('ul');
  var foreNamesM = document.createElement('ul');
  var topPar = document.createElement('ul');
  var topOA = document.createElement('ul');
  var sgDiv = document.createElement('div');
  var gDiv = document.createElement('div');
  var hrFreq = document.createElement('table');
  var crFreq = document.createElement('table');
  var iuc = document.createElement('div');
  var crvul = document.createElement('div');

  //set elements
  mapLegend.id = 'mapLegend';
  foreNamesF.id = 'ForeNamesFemale';
  foreNamesM.id = 'ForeNamesMale';
  foreFemaleLegend.id = 'foreFemaleLegend';
  foreMaleLegend.id = 'foreMaleLegend';
  topPar.id = 'topPar';
  topOA.id = 'topOA';
  sgDiv.id = 'sgCat';
  gDiv.id = 'gCat';
  hrFreq.id = 'tableHR';
  crFreq.id = 'tableCR';
  iuc.id = 'IUC';
  crvul.id = 'CRVUL';

  //replace
  lSearch.replaceWith(mapLegend);
  foreFemale.replaceWith(foreNamesF);
  foreMale.replaceWith(foreNamesM);
  fLegend.replaceWith(foreFemaleLegend);
  mLegend.replaceWith(foreMaleLegend);
  pPar.replaceWith(topPar);
  pOA.replaceWith(topOA);
  sgCat.replaceWith(sgDiv);
  gCat.replaceWith(gDiv);
  tableHR.replaceWith(hrFreq);
  tableCR.replaceWith(crFreq);
  iucEl.replaceWith(iuc);
  crvulEl.replaceWith(crvul);

  //hide
  document.getElementById('AHAH').style.display='none';
  document.getElementById('IMD').style.display='none';
  document.getElementById('BBAND').style.display='none';

  //back to names tablist
  $('#nav-tab a[href="#names"]').tab('show');

  //remove previous map layer if exist
  if (control != undefined) {
      map.removeControl(control);
      map.removeLayer(layer_rm);
    };
  };
