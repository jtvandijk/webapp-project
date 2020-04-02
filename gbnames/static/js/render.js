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
  sgDiv.className = 'card-body p-2';
  gDiv.className = 'card-body p-2';
  descDiv.className = 'text-justify pb-0 m-0 pl-4 pr-4 pt-2';

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

//render ahah distribution
function renderHealth(ahah) {

  console.log(ahah)
  };

//render imd distribution
function renderIMD(imd) {

  console.log(imd);

  //get, set, create elements
  var imdDiv = document.getElementById('IMD');
  var chartIMD = document.createElement('div');
  var canvasIMD = document.createElement('canvas');
  chartIMD.id = 'IMD';
  canvasIMD.id = 'chartIMD';
  canvasIMD.setAttribute('height','50px');
  canvasIMD.setAttribute('width','400px');
  chartIMD.appendChild(canvasIMD);
  imdDiv.replaceWith(chartIMD);

  //chart
  var ctx = document.getElementById('chartIMD');
  var myChart = new Chart(ctx, {
      type: 'horizontalBar',
      data: {datasets: [
              {label: 'Low',data: imd[0],backgroundColor: '#a50026',hoverBackgroundColor: '#a50026'},
              {label: 'Low',data: imd[1],backgroundColor: '#d73027',hoverBackgroundColor: '#d73027'},
              {label: 'Low',data: imd[2],backgroundColor: '#f46d43',hoverBackgroundColor: '#f46d43'},
              {label: 'Low',data: imd[3],backgroundColor: '#fdae61',hoverBackgroundColor: '#fdae61'},
              {label: 'Low',data: imd[4],backgroundColor: '#fee08b',hoverBackgroundColor: '#fee08b'},
              {label: 'Low',data: imd[5],backgroundColor: '#d9ef8b',hoverBackgroundColor: '#d9ef8b'},
              {label: 'Low',data: imd[6],backgroundColor: '#a6d96a',hoverBackgroundColor: '#a6d96a'},
              {label: 'Low',data: imd[7],backgroundColor: '#66bd63',hoverBackgroundColor: '#66bd63'},
              {label: 'Low',data: imd[8],backgroundColor: '#1a9850',hoverBackgroundColor: '#1a9850'},
              {label: 'Low',data: imd[9],backgroundColor: '#006837',hoverBackgroundColor: '#006837'},
              ]},
      options: {tooltips: {enabled: false},
      highlights: {enabled: false},
      scales: {xAxes: [{stacked: true,gridLines: {display: false},ticks: {display: false}}],
               yAxes: [{stacked: true,gridLines: {display: false},ticks: {display: false}}]},
      legend: {display: false,},}}
    );
  };

//render modal bbs
function renderBBAND(bbs) {

  console.log(bbs);
  };

//render modal iuc
function renderIUC(iuc) {

  //get elements
  var iucEl = document.getElementById('IUC');
  var dscDiv = document.getElementById('dscIUC')

  //create elements
  var iucDiv = document.createElement('div');
  var iucBtn = document.createElement('button');
  var descDiv = document.createElement('div')

  //set elements
  iucDiv.id = 'IUC';
  descDiv.id = 'dscIUC';
  iucDiv.className = 'card-body p-2';
  descDiv.className = 'collapse text-justify pb-0 m-0 pl-2 pr-2 pt-2';

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
  var iucDsc = document.getElementById('dscIUC')

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
  dscDiv.id = 'dscCat';
  hrFreq.id = 'tableHR';
  crFreq.id = 'tableCR';
  iuc.id = 'IUC';
  dscIUC.id = 'dscIUC';

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
