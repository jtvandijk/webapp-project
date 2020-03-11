//update map -- search on load
$j(document).on('submit','#initSur',function(e) {
  e.preventDefault();
  initSearch(document.getElementById('init_surname').value);
});

//update map -- search menu
$j(document).on('submit','#searchSur',function(e) {
  e.preventDefault();
  initSearch(document.getElementById('surname').value);
});

//initiate search
function initSearch(surname) {

  //remove jumbotron
  jumbotron.style.display = 'none';

  //lay out
  var cards = [...document.getElementsByClassName('collapse')];
  show(cards);
  scroll(0,0);

  //execute search
  searchSurname(surname);
};

//search surname
function searchSurname(surname) {
  startMapLoad();
  $j.ajax({
    method: 'POST',
    url: '../gbnames/search/',
    data: {surname: surname,
           csrfmiddlewaretoken: csrftoken
          },
    success: function (data) {
      //no data entered
      if (data.surname==='empty') {
        renderNone();
        return;
      //no data found
      } else if (data.surname==='none') {
        renderNotFound(data.surname);
        return;
      //data found
      } else {

        //render main
        renderHTML(data.surname);
        //renderMap(data.surname,data.years,map);

        //render names
        renderTable(data.surname,data.freqs);
        renderForenames(data.stats[0],data.stats[1],data.stats[2],data.stats[3]);
        renderParish(data.stats[4]);
        renderOA(data.stats[5]);
        renderCAT(data.stats[6]);

        //render consumer statistics
        renderHealth(data.stats[7]);
        renderIMD(data.stats[8]);
        renderBBAND(data.stats[9]);
        renderIUC(data.stats[10]);

        //stop map loading indicator
        stopMapLoad();

        //return
        return;
      }
    }
  })
};

//show top administrative areas
function searchLocation(id,all,sr) {

  //post
  $j.ajax({
    method: 'POST',
    url: '../gbnames/location/',
    data: {id: id,
           all: all,
           sr: sr,
           csrfmiddlewaretoken: csrftoken
        },
    success: function (data) {
      mapAdmin(data.sel,data.all,data.sr)
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
