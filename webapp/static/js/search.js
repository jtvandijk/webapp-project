//update map -- search on load
$j(document).on('submit','#initSur',function(e) {
  e.preventDefault();
  initSearch(document.getElementById('init_surname').value);
});

//update map -- search
$j(document).on('submit','#searchSur',function(e) {
  e.preventDefault();
  initSearch(document.getElementById('surname').value);
});

//initiate search
function initSearch(q) {

  //remove jumbotron
  jumbotron.style.display = 'none';

  //lay out
  var c = [...document.getElementsByClassName('collapse')];
  show(c);
  scroll(0,0);

  //execute search
  get_data(q);
};

//search surname
function get_data(q) {
  startMapLoad();
  $j.ajax({
    method: 'POST',
    url: '../udl-namekde/search/',
    // url: '../search/',
    data: {q: q,
           csrfmiddlewaretoken: csrftoken
          },
    success: function (data) {
      // no data entered
      if (data.source==='empty') {
        renderNone();
        return;
      // no data found
      } else if (data.source==='none') {
        renderNotFound(data.surname);
        return;
      // data found
      } else if (data.source==='found') {

        //render main
        renderHTML(data.surname);
        renderMap(data.years,data.contours,cmap);

        //render names
        renderTable(data.hr_freq,data.cr_freq,data.surname);
        renderForenames(data.foremh,data.forefh,data.foremc,data.forefc);
        renderParish(data.partop);
        renderOA(data.oatop);
        renderCAT(data.oacat);

        //render consumer statistics
        renderHealth(data.oahlth);
        renderIMD(data.oaimd);
        renderBBAND(data.bband);
        renderIUC(data.iuc);
        renderCRVUL(data.crvul);

        //stop map loading indicator
        stopMapLoad();

        //return
        return;
      }
    }
  })
};

//start map loading indicator
function startMapLoad() {

  //start map loading indicator
  document.getElementById('mapload').style.display='flex';

  //get elements
  var pSearch = document.getElementById('searchParam');
  var sName = document.createElement('h1');

  //create elements
  sName.id = 'searchParam';
  sName.className = 'mt-3';
  sName.innerHTML = '...';

  //replace
  pSearch.replaceWith(sName);
};

//stop loading indicator
function stopMapLoad() {
  document.getElementById('mapload').style.display='none';
};
