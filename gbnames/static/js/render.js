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
  noText.textContent = 'Please type in a surname.';

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
  notFound.innerHTML = 'Unfortunately, your search for <strong>'+surname.toUpperCase()+'</strong> did not yield any results.';

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

  //create elements
  var foundPar = document.createElement('h1');
  var mapLegend = document.createElement('div');

  //set elements
  foundPar.id = 'searchParam';
  foundPar.className = 'mt-3';
  foundPar.innerHTML = surname.toUpperCase();

  mapLegend.id = 'mapLegend';
  mapLegend.className = 'card-footer small text-muted text-justify p-3';
  mapLegend.innerHTML = 'The blue contours enclose areas where the population-weighted density of the surname is highest.';

  //replace
  pSearch.replaceWith(foundPar);
  lSearch.replaceWith(mapLegend);
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
  foreHistLegend.innerHTML = 'Most common female and male forenames for your search over the period 1851-1911.';
  foreContLegend.id = 'foreContLegend';
  foreContLegend.className = 'card-footer small text-muted text-justify p-3';
  foreContLegend.innerHTML = 'Most common female and male forenames for your search over the period 1997-2016.';;

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

  //create elements
  var pPar = document.getElementById('topPar');
  var topPar = document.createElement('table');
  var head = document.createElement('thead');
  var body = document.createElement('tbody');

  //set elements
  topPar.id = 'topPar';
  topPar.className = 'table table-sm m-0';

  //header
  var row = document.createElement('tr');
  var ds = document.createElement('th');
  var nm = document.createElement('th');
  ds.innerHTML = 'District name';
  nm.innerHTML = 'Parish name';
  row.appendChild(ds);
  row.appendChild(nm);
  head.appendChild(row);

  //rows
  for (var i = 0; i < partop.length; ++i) {
    var row = document.createElement('tr');
    var ds = document.createElement('td');
    var nm = document.createElement('td');
    ds.innerHTML = partop[i][0];
    nm.innerHTML = partop[i][1];
    row.appendChild(ds);
    row.appendChild(nm);
    body.appendChild(row);
  };

  //append
  topPar.appendChild(head);
  topPar.appendChild(body);

  //replace
  pPar.replaceWith(topPar);

};

//render top oa
function renderMSOA(msoatop) {

  //create elements
  var pMSOA = document.getElementById('topMSOA');
  var topMSOA = document.createElement('table');
  var head = document.createElement('thead');
  var body = document.createElement('tbody');

  //set elements
  topMSOA.id = 'topMSOA';
  topMSOA.className = 'table table-sm m-0';

  //header
  var row = document.createElement('tr');
  var ds = document.createElement('th');
  var ms = document.createElement('th');
  ds.innerHTML ='District name';
  ms.innerHTML = 'Area name';
  row.appendChild(ds);
  row.appendChild(ms);
  head.appendChild(row);

  //rows
  for (var i = 0; i < msoatop.length; ++i) {
    var row = document.createElement('tr');
    var ds = document.createElement('td');
    var ms = document.createElement('td');
    ds.innerHTML = msoatop[i][0];
    ms.innerHTML = msoatop[i][1];
    row.appendChild(ds);
    row.appendChild(ms);
    body.appendChild(row);
  };

  //append
  topMSOA.appendChild(head);
  topMSOA.appendChild(body);

  //replace
  pMSOA.replaceWith(topMSOA);

  };

//render modal oa cat
function renderOAC(oac) {

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
  if (oac[2] == 99) {
    var cls = 99;
  } else {
    var cls = oac[2].slice(0,1);
  };

  //values
  sgDivbtn.className = 'btn btn-g'+cls+' btn-lg btn-block';
  gDivbtn.className = 'btn btn-g'+cls+' sub btn-lg btn-block';
  sgDivbtn.innerHTML = oac[0];
  gDivbtn.innerHTML = oac[1];
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
  var foreHist = document.getElementById('ForeNamesHist');
  var foreCont = document.getElementById('ForeNamesCont');
  var hLegend = document.getElementById('foreHistLegend');
  var cLegend = document.getElementById('foreContLegend');
  var pPar = document.getElementById('topPar');
  var pMSOA = document.getElementById('topMSOA');
  var sgCat = document.getElementById('sgCat');
  var gCat = document.getElementById('gCat');
  var tableHR = document.getElementById('tableHR');
  var tableCR = document.getElementById('tableCR');
  var iucEl = document.getElementById('IUC');

  //create elements
  var mapLegend = document.createElement('div');
  var foreHistLegend = document.createElement('div');
  var foreContLegend = document.createElement('div');
  var foreNamesHist = document.createElement('ul');
  var foreNamesCont = document.createElement('ul');
  var topPar = document.createElement('table');
  var topMSOA = document.createElement('table');
  var sgDiv = document.createElement('div');
  var gDiv = document.createElement('div');
  var hrFreq = document.createElement('table');
  var crFreq = document.createElement('table');
  var iuc = document.createElement('div');

  //set elements
  mapLegend.id = 'mapLegend'
  foreNamesHist.id = 'ForeNamesHist';
  foreNamesCont.id = 'ForeNamesCont';
  foreHistLegend.id = 'foreHistLegend';
  foreContLegend.id = 'foreContLegend';
  topPar.id = 'topPar';
  topMSOA.id = 'topMSOA';
  sgDiv.id = 'sgCat';
  gDiv.id = 'gCat';
  hrFreq.id = 'tableHR';
  crFreq.id = 'tableCR';
  iuc.id = 'IUC';

  //replace
  lSearch.replaceWith(mapLegend);
  foreHist.replaceWith(foreNamesHist);
  foreCont.replaceWith(foreNamesCont);
  hLegend.replaceWith(foreHistLegend);
  cLegend.replaceWith(foreContLegend);
  pPar.replaceWith(topPar);
  pMSOA.replaceWith(topMSOA);
  sgCat.replaceWith(sgDiv);
  gCat.replaceWith(gDiv);
  tableHR.replaceWith(hrFreq);
  tableCR.replaceWith(crFreq);
  iucEl.replaceWith(iuc);

  //hide
  document.getElementById('AHAH').style.display='none';
  document.getElementById('IMD').style.display='none';
  document.getElementById('BBAND').style.display='none';

  //remove previous map layers if exist
  if (mapcontrol != undefined) {
      map.removeControl(mapcontrol);
      map.removeLayer(maplayer);
    };
};
