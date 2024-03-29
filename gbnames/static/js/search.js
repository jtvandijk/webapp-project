//update map -- search through jumbotron
$j(document).on('submit','#initSur',function(e) {
  e.preventDefault();
  initSearch(document.getElementById('init_surname').value);
});

//update map -- search through menu
$j(document).on('submit','#searchSur',function(e) {
  e.preventDefault();
  initSearch(document.getElementById('surname').value);
});

//initiate search
function initSearch(surname) {

  //remove jumbotron
  jumbotron.style.display = 'none';

  //scroll
  scroll(0,0);

  //execute search
  searchSurname(surname);
};

//search surname
function searchSurname(surname) {

  //functions
  startMapLoad();
  clearPage();

  //search
  $j.ajax({
    method: 'POST',
    url: '../search/',
    data: {surname: surname,
           csrfmiddlewaretoken: csrftoken
          },
    //success
    success: function (data) {
      //no data entered
      if (data.surname==='empty') {
        renderNone();
        return;
      //no data found
      } else if (data.surname==='none') {
        renderNotFound(surname);
        return;
      //db entry found
      } else if (data.surname==='db') {
        renderDBFound(surname);
        return;
      //data found
      } else {

        //render main
        renderHTML(data.surname);
        renderMap(data.surname,data.years,map);

        //render names
        renderTable(data.surname,data.freqs);
        renderForenames(data.stats[0],data.stats[1],data.stats[2],data.stats[3]);
        renderParish(data.stats[4]);
        renderMSOA(data.stats[5]);

        //render consumer statistics
        renderOAC(data.stats[6]);
        renderLOAC(data.stats[7]);
        renderIUC(data.stats[8]);
        renderAHAH(data.stats[9]);
        renderIMD(data.stats[10]);
        renderBBS(data.stats[11]);
        renderEEE(data.stats[12]);
        renderSTD(data.stats[13]);

        //map load stopped in renderMap function

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
