//render none
function renderNone() {

  //functions
  stopMapLoad();

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

  //get elements
  var pSearch = document.getElementById('searchParam');

  //create elements
  var notFound = document.createElement('p');

  //set elements
  notFound.className = 'p-3 mb-3 bg-orange text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, your search for <strong>'+surname.toUpperCase()+'</strong> did not match any of our available records.'

  //replace
  pSearch.replaceWith(notFound);
};

//render not found
function renderDBFound(surname) {

  //functions
  stopMapLoad();

  //get elements
  var pSearch = document.getElementById('searchParam');

  //create elements
  var notFound = document.createElement('p');

  //set elements
  notFound.className = 'p-3 mb-3 bg-notes text-dark';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'We do have records available for your search for <strong>'+surname.toUpperCase()+'</strong>. Unfortunately, \
                        this name does not have more than 100 bearers at any point in time and therefore no data are shown. This \
                        thresholds is used to avoid disclosing information about indivduals.';

  //replace
  pSearch.replaceWith(notFound);
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
  foundPar.className = 'mt-3';
  foundPar.innerHTML = surname.toUpperCase();

  mapLegend.id = 'mapLegend';
  mapLegend.className = 'card-footer small text-muted text-justify p-3';
  mapLegend.innerHTML = 'The blue contours enclose areas where bearers of the name were most concentrated, measured as where \
                         the population-weighted density of the surname is highest. Use the slider bar to see where the name \
                         was found over historical (1851, 1861 and 1881-1911) and more recent (1997-2016) time periods.';

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
  foreContLegend.innerHTML = 'Most common female and male forenames for your search over the period 1997-2016.';

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

  //get elements
  var pPar = document.getElementById('topPar');

  //create elements
  var topPar = document.createElement('table');
  var head = document.createElement('thead');
  var body = document.createElement('tbody');

  //set elements
  topPar.id = 'topPar';
  topPar.className = 'table table-sm m-0';

  //table header
  var row = document.createElement('tr');
  var ds = document.createElement('th');
  var nm = document.createElement('th');
  ds.innerHTML = 'District name';
  nm.innerHTML = 'Parish name';
  row.appendChild(ds);
  row.appendChild(nm);
  head.appendChild(row);

  //table rows
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

  //set elements
  var pMSOA = document.getElementById('topMSOA');

  //create elements
  var topMSOA = document.createElement('table');
  var head = document.createElement('thead');
  var body = document.createElement('tbody');

  //set elements
  topMSOA.id = 'topMSOA';
  topMSOA.className = 'table table-sm m-0';

  //table header
  var row = document.createElement('tr');
  var ds = document.createElement('th');
  var ms = document.createElement('th');
  ds.innerHTML ='District name';
  ms.innerHTML = 'Area name';
  row.appendChild(ds);
  row.appendChild(ms);
  head.appendChild(row);

  //table rows
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

//render modal oac
function renderOAC(oac) {

  //get elements
  var sgButton = document.getElementById('sgCat');
  var gButton = document.getElementById('gCat');
  var dscDiv = document.getElementById('dscCat')

  //create elements
  var sgDiv = document.createElement('div');
  var gDiv = document.createElement('div');
  var sgDivbtn = document.createElement('button');
  var gDivbtn = document.createElement('button');
  var descDiv = document.createElement('div')

  //set elements
  sgDiv.id = 'sgCat';
  gDiv.id = 'gCat';
  descDiv.id = 'dscCat';
  sgDiv.className = 'card-body p-0';
  gDiv.className = 'card-body p-0';
  descDiv.className = 'text-justify pb-0 m-0 pl-3 pr-3 pt-3';

  //classname and text
  if (oac[4] == 99) {
    var cls = 99;
  } else {
    var cls = oac[4].slice(0,1);

    //supergroup
    var sgTxt = document.createElement('div');
    sgTxt.id = 'sgTxt';
    sgTxt.className = 'collapse text-justify pb-2 mb-2'
    sgTxt.innerHTML = '<strong>' + oac[0].toUpperCase() + '</strong> ' + oac[2];
    descDiv.appendChild(sgTxt);

    //group
    var gTxt = document.createElement('div');
    gTxt.id = 'gTxt';
    gTxt.className = 'collapse text-justify pb-2 mb-0'
    gTxt.innerHTML = '<strong>' + oac[1].toUpperCase() + '</strong> ' + oac[3];
    descDiv.appendChild(gTxt);
  };

  //values and attributes
  sgDivbtn.className = 'btn btn-g'+cls+' btn-lg btn-block';
  gDivbtn.className = 'btn btn-g'+cls+' sub btn-lg btn-block';
  sgDivbtn.setAttribute('data-toggle','collapse');
  sgDivbtn.setAttribute('data-target','#sgTxt');
  sgDivbtn.setAttribute('aria-expanded','false');
  sgDivbtn.setAttribute('aria-controls','sgTxt');
  gDivbtn.setAttribute('data-toggle','collapse');
  gDivbtn.setAttribute('data-target','#gTxt');
  gDivbtn.setAttribute('aria-expanded','false');
  gDivbtn.setAttribute('aria-controls','sTxt');
  sgDivbtn.innerHTML = oac[0] + '<span class="fas fa-angle-double-down fa-md p-2 float-right"></span>' +
                                '<span class="fas fa-angle-double-up fa-md p-2 float-right id="test1"></span>';
  gDivbtn.innerHTML = oac[1] +  '<span class="fas fa-angle-double-down p-2 float-right"></span>' +
                                '<span class="fas fa-angle-double-up fa-md p-2 float-right"></span>';
  sgDiv.appendChild(sgDivbtn);
  gDiv.appendChild(gDivbtn);

  //replace
  sgButton.replaceWith(sgDiv);
  gButton.replaceWith(gDiv);
  dscDiv.replaceWith(descDiv);
};

//render modal ahah
function renderAHAH(ahah) {

  //remove select
  removeSelect('ahah');

  //get elements
  var dscDiv = document.getElementById('dscAHAH');

  //create elements
  var descDiv = document.createElement('div');

  //set elements
  descDiv.id = 'dscAHAH';
  descDiv.className = 'text-justify pt-4 px-3 mb-0';

  //colour ramp
  document.getElementById('AHAH').style.display='block';
  if (ahah != 'No data') {

    //selection
    var ahahsel = document.getElementById('ahah' + ahah);
    var decile = document.createTextNode(ahah);
    ahahsel.className = 'ramp a'+ ahah + ' mode-select';
    ahahsel.appendChild(decile);

    //text
    descDiv.innerHTML = 'Your selected surname occurs most frequently in decile number <strong>' + ahah + '</strong> of the Access to Healthy \
                         Assets and Hazards index. The first decile is the worst performing decile wereas the tenth decile is the best performing decile.';

  } else {

    //text
    descDiv.innerHTML = '<strong>No data</strong> found for your search.';

  };

  //replace
  dscDiv.replaceWith(descDiv);
};

//render modal imd
function renderIMD(imd) {

  //remove select
  removeSelect('imd');

  //get elements
  var dscDiv = document.getElementById('dscIMD');

  //create elements
  var descDiv = document.createElement('div');

  //set elements
  descDiv.id = 'dscIMD';
  descDiv.className = 'text-justify pt-3 px-0 mb-0';

  //colour ramp
  document.getElementById('IMD').style.display='block';
  if (imd != 'No data') {

    //selection
    var imdsel = document.getElementById('imd' + imd);
    var decile = document.createTextNode(imd);
    imdsel.className = 'ramp i'+ imd + ' mode-select';
    imdsel.appendChild(decile);

    //text
    descDiv.innerHTML = 'Your selected surname occurs most frequently in decile number <strong>' + imd + '</strong> of the Index of Multiple Deprivation. \
                         The first decile is the worst performing decile wereas the tenth decile is the best performing decile.';

  } else {

    //text
    descDiv.innerHTML = '<strong>No data</strong> found for your search.';

  };

  //replace
  dscDiv.replaceWith(descDiv);
};

//render modal bbs
function renderBBS(bbs) {

  //remove select
  removeSelect('bbs');

  //get elements
  var dscDiv = document.getElementById('dscBBS');

  //create elements
  var descDiv = document.createElement('div');

  //set elements
  descDiv.id = 'dscBBS';
  descDiv.className = 'text-justify pt-3 px-0 mb-0';

  //colour ramp
  document.getElementById('BBS').style.display='block';
  if (bbs[0] != 99) {

    //selection
    var bbssel = document.getElementById('bbs' + bbs[0]);
    var decile = document.createTextNode(bbs[0]);
    bbssel.className = 'ramp b'+ bbs[0] + ' mode-select';
    bbssel.appendChild(decile);

    //text
    descDiv.innerHTML = 'Your selected surname surname falls in group <strong>' + bbs[0] + '</strong>, which suggests \
                         a modal fixed broadband download speed of <strong>' + bbs[1] + '</strong>.';

  } else {

    //text
    descDiv.innerHTML = '<strong>No data</strong> found for your search.';

  };

  //replace
  dscDiv.replaceWith(descDiv);
};

//render modal iuc
function renderIUC(iuc) {

  //get elements
  var iucEl = document.getElementById('IUC');
  var dscDiv = document.getElementById('dscIUC');

  //create elements
  var iucDiv = document.createElement('div');
  var iucBtn = document.createElement('button');
  var descDiv = document.createElement('div');

  //set elements
  iucDiv.id = 'IUC';
  descDiv.id = 'dscIUC';
  iucDiv.className = 'card-body px-0 py-0 pb-3';
  descDiv.className = 'collapse text-justify pb-0 m-0 px-0 pt-1';

  //classname and text
  if (iuc[0] != 99) {

    //iuc text
    var iucTxt = document.createElement('div');
    iucTxt.className = 'text-justify pb-2 mb-2';
    iucTxt.innerHTML = '<strong>' + iuc[1].toUpperCase() + '</strong> ' + iuc[2];
    descDiv.appendChild(iucTxt);
  };

  //classname
  cls = iuc[0];

  //values and attributes
  iucBtn.className = 'btn btn-iuc'+cls+' btn-lg btn-block';
  iucBtn.setAttribute('data-toggle','collapse');
  iucBtn.setAttribute('data-target','#dscIUC');
  iucBtn.setAttribute('aria-expanded','false');
  iucBtn.setAttribute('aria-controls','dscIUC');
  iucBtn.innerHTML = iuc[1] + '<span class="fas fa-angle-double-down fa-md p-2 float-right"></span>' +
                              '<span class="fas fa-angle-double-up fa-md p-2 float-right"></span>';
  iucDiv.appendChild(iucBtn);

  //replace
  iucEl.replaceWith(iucDiv);
  dscDiv.replaceWith(descDiv);
};

//remove select
function removeSelect(rem) {

  //loop
  for (var i = 1; i < 11; ++i) {
    var id = rem+i.toString();
    var remcat = document.getElementById(id);
    remcat.classList.remove('mode-select');
    remcat.innerHTML = '';
    };
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
  var dscCat = document.getElementById('dscCat');
  var tableHR = document.getElementById('tableHR');
  var tableCR = document.getElementById('tableCR');
  var iucEl = document.getElementById('IUC');
  var iucDsc = document.getElementById('dscIUC');
  var imdDsc = document.getElementById('dscIMD');
  var ahahDsc = document.getElementById('dscAHAH');
  var bbsDsc = document.getElementById('dscBBS');

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
  var dscDiv = document.createElement('div');
  var hrFreq = document.createElement('table');
  var crFreq = document.createElement('table');
  var iuc = document.createElement('div');
  var dscIUC = document.createElement('div');
  var dscIMD = document.createElement('div');
  var dscAHAH = document.createElement('div');
  var dscBBS = document.createElement('div');

  //set elements
  mapLegend.id = 'mapLegend';
  foreNamesHist.id = 'ForeNamesHist';
  foreNamesCont.id = 'ForeNamesCont';
  foreHistLegend.id = 'foreHistLegend';
  foreContLegend.id = 'foreContLegend';
  topPar.id = 'topPar';
  topMSOA.id = 'topMSOA';
  sgDiv.id = 'sgCat';
  gDiv.id = 'gCat';
  dscDiv.id = 'dscCat';
  hrFreq.id = 'tableHR';
  crFreq.id = 'tableCR';
  iuc.id = 'IUC';
  dscIUC.id = 'dscIUC';
  dscIMD.id = 'dscIMD';
  dscAHAH.id = 'dscAHAH';
  dscBBS.id = 'dscBBS';

  //pretty
  foreNamesHist.className= 'p-2';
  foreNamesCont.className= 'p-2';

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
  dscCat.replaceWith(dscDiv);
  tableHR.replaceWith(hrFreq);
  tableCR.replaceWith(crFreq);
  iucEl.replaceWith(iuc);
  iucDsc.replaceWith(dscIUC);
  imdDsc.replaceWith(dscIMD);
  ahahDsc.replaceWith(dscAHAH);
  bbsDsc.replaceWith(dscBBS);

  //hide
  document.getElementById('AHAH').style.display='none';
  document.getElementById('IMD').style.display='none';
  document.getElementById('BBS').style.display='none';

  //remove previous map layers if exist
  if (mapcontrol != undefined) {
      map.removeControl(mapcontrol);
      map.removeLayer(maplayer);
    };
};
