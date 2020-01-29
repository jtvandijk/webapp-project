//render none
function renderNone() {

  //functions
  stopMapLoad();
  clearPage();

  //get elements
  var pSearch = document.getElementById('searchParam');

  //create elements
  var noText = document.createElement('p');

  //set elements
  noText.className = 'p-3 mb-3 bg-orange text-dark';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  //replace
  pSearch.replaceWith(noText);
};

//render not found
function renderNotFound(surname) {

  //functions
  stopMapLoad();
  clearPage();

  //get elements
  var pSearch = document.getElementById('searchParam');

  //create elements
  var notFound = document.createElement('p');

  //set elements
  notFound.className = 'p-3 mb-3 bg-orange text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+surname.toUpperCase()+'</strong> is not in our database. Are you sure you did not make a typo?';

  //replace
  pSearch.replaceWith(notFound);
};

//render found
function renderHTML(surname) {

  //functions
  clearPage();

  //get elements
  var pSearch = document.getElementById('searchParam');
  var lSearch = document.getElementById('mapLegend');
  var parSearch = document.getElementById('parLegend');
  var msoaSearch = document.getElementById('msoaLegend');

  //create elements
  var foundPar = document.createElement('h1');
  var mapLegend = document.createElement('div');
  var parLegend = document.createElement('div');
  var msoaLegend = document.createElement('div');

  //set elements
  foundPar.id = 'searchParam';
  foundPar.className = 'mt-3';
  foundPar.innerHTML = surname.toUpperCase();

  mapLegend.id = 'mapLegend';
  mapLegend.className = 'card-footer small text-muted text-justify p-3';
  mapLegend.innerHTML = 'The grey lines enclose the areas where the population-weighted density of the surname is highest in the period 1851-1911, where we have the historic Census data. Use the slider bar to show the same metric for much more recent distributions, shown in orange.';

  parLegend.id = 'parLegend';
  parLegend.className = 'card-footer small text-muted text-justify p-3';
  parLegend.innerHTML = 'Click on any of the <b>Top Historical Parishes</b> to add these to the map. The grey pins show the centroids of the areas with the highest absolute number of bearers with the surname in the period 1851-1911.';

  msoaLegend.id = 'msoaLegend';
  msoaLegend.className = 'card-footer small text-muted text-justify p-3';
  msoaLegend.innerHTML = 'Click on any of the <b>Top Areas</b> to add these to the map. The orange pins show the centroids of the areas with the highest absolute number of bearers with the surname for 1997-2016.';

  //replace
  pSearch.replaceWith(foundPar);
  lSearch.replaceWith(mapLegend);
  parSearch.replaceWith(parLegend);
  msoaSearch.replaceWith(msoaLegend);

};

//render forenames
function renderForenames(fmh,ffh,fmc,ffc) {

  //get elements
  var foreHist = document.getElementById('ForeNamesHist');
  var foreCont = document.getElementById('ForeNamesCont');
  var hLegend = document.getElementById('foreHistLegend');
  var cLegend = document.getElementById('foreContLegend');

  //create elements
  var foreNamesHist = document.createElement('ul');
  var foreNamesCont = document.createElement('ul');
  var foreHistLegend = document.createElement('div');
  var foreContLegend = document.createElement('div');

  //set elements
  foreNamesHist.id = 'ForeNamesHist';
  foreNamesHist.className = 'list-inline ml-3 mt-2 mr-3 mb-3';
  foreNamesCont.id = 'ForeNamesCont';
  foreNamesCont.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  foreHistLegend.id = 'foreHistLegend';
  foreHistLegend.className = 'card-footer small text-muted text-justify p-3';
  foreHistLegend.innerHTML = 'Female and male forenames with highest frequencies for all residents over the period 1851-1911.';
  foreContLegend.id = 'foreContLegend';
  foreContLegend.className = 'card-footer small text-muted text-justify p-3';
  foreContLegend.innerHTML = 'Female and male forenames with highest frequencies for adult residents over the period 1997-2016.';;

  //hist buttons female
  for (var i = 0; i < ffh.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = ffh[i].toUpperCase();
    li.className = 'btn btn-historic mt-2 mr-1';
    foreNamesHist.appendChild(li);
  };

  //cont buttons female
  for (var i = 0; i < ffc.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = ffc[i].toUpperCase();
    li.className = 'btn btn-historic mt-2 mr-1';
    foreNamesCont.appendChild(li);
  };

  //hist buttons male
  for (var i = 0; i < fmh.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = fmh[i].toUpperCase();
    li.className = 'btn btn-contemporary mt-2 mr-1';
    foreNamesHist.appendChild(li);
  };

  //cont buttons female
  for (var i = 0; i < fmc.length; ++i) {
    var li = document.createElement('button');
    li.innerHTML = fmc[i].toUpperCase();
    li.className = 'btn btn-contemporary mt-2 mr-1';
    foreNamesCont.appendChild(li);
  };

  //replace
  foreHist.replaceWith(foreNamesHist);
  foreCont.replaceWith(foreNamesCont);
  hLegend.replaceWith(foreHistLegend);
  cLegend.replaceWith(foreContLegend);
};

//render top parish
function renderParish(partop) {

  //get, create, set, elements
  var pPar = document.getElementById('topPar');
  var topPar = document.createElement('ul');
  topPar.id = 'topPar';
  topPar.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  //parish buttons
  allid = [];
  for (var i = 0; i < partop.length; ++i) {
    var li = document.createElement('button');
    var id = partop[i][0];
    allid.push(parseInt(id));
    li.innerHTML = partop[i][1];
    li.id = id;
    if (id == 99) {
      li.className = 'btn btn-outline-secondary btn-deactivate mt-2 mr-1';
    } else {
      li.className = 'btn btn-outline-secondary mt-2 mr-1';
    }
    li.value = id;
    li.onclick = function () {
      var parid = $j(this).val();
      showAdmin(parid,allid,'hr');
    }
    topPar.appendChild(li);

  //replace
  pPar.replaceWith(topPar);
  };
};

//render top oa
function renderOA(oatop) {

  //get, create, set, elements
  var pOA = document.getElementById('topOA');
  var topOA = document.createElement('ul');
  topOA.id = 'topOA';
  topOA.className = 'list-inline ml-3 mt-2 mr-3 mb-3';

  //oa buttons
  alloa = [];
  for (var i = 0; i < oatop.length; ++i) {
    var li = document.createElement('button');
    var id = oatop[i][0]
    alloa.push(id);
    li.innerHTML = oatop[i][1];
    li.id = id;
    if (oatop[i][0] == 99) {
      li.className = 'btn btn-outline-secondary btn-deactivate mt-2 mr-1';
    } else {
      li.className = 'btn btn-outline-secondary mt-2 mr-1';
    }
    li.value = id;
    li.onclick = function () {
      var oaid = $j(this).val();
      showAdmin(oaid,alloa,'cr');
    }
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
  if (oacat[2] == 99) {
    var cls = 99;
  } else {
    var cls = oacat[2].slice(0,1);
  };

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

//render selection oa ahah
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

//render selection oa imd
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

//render selection oa bband
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
  //no data
  var nd = rem+'99'
  var remcat = document.getElementById(nd);
  remcat.classList.remove('btn-select');
  };

//clear page
function clearPage() {

  //get elements
  var lSearch = document.getElementById('mapLegend');
  var parSearch = document.getElementById('parLegend');
  var msoaSearch = document.getElementById('msoaLegend');
  var foreHist = document.getElementById('ForeNamesHist');
  var foreCont = document.getElementById('ForeNamesCont');
  var hLegend = document.getElementById('foreHistLegend');
  var cLegend = document.getElementById('foreContLegend');
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
  var parLegend = document.createElement('div');
  var msoaLegend = document.createElement('div');
  var foreHistLegend = document.createElement('div');
  var foreContLegend = document.createElement('div');
  var foreNamesHist = document.createElement('ul');
  var foreNamesCont = document.createElement('ul');
  var topPar = document.createElement('ul');
  var topOA = document.createElement('ul');
  var sgDiv = document.createElement('div');
  var gDiv = document.createElement('div');
  var hrFreq = document.createElement('table');
  var crFreq = document.createElement('table');
  var iuc = document.createElement('div');
  var crvul = document.createElement('div');

  //set elements
  mapLegend.id = 'mapLegend'
  parLegend.id = 'parLegend'
  msoaLegend.id = 'msoaLegend'
  foreNamesHist.id = 'ForeNamesHist';
  foreNamesCont.id = 'ForeNamesCont';
  foreHistLegend.id = 'foreHistLegend';
  foreContLegend.id = 'foreContLegend';
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
  parSearch.replaceWith(parLegend);
  msoaSearch.replaceWith(msoaLegend);
  foreHist.replaceWith(foreNamesHist);
  foreCont.replaceWith(foreNamesCont);
  hLegend.replaceWith(foreHistLegend);
  cLegend.replaceWith(foreContLegend);
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

  //remove previous map layers if exist
  if (control != undefined) {
      cmap.removeControl(control);
      cmap.removeLayer(layer_rm);
    };
  if (adminlayer != undefined) {
      cmap.removeLayer(adminlayer);
  };
};
