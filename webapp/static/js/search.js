//jQuery
var $j = jQuery.noConflict();

//update map -- search on load
$j(document).on('submit','#initSur',function(e) {
    e.preventDefault();
    searchmodal.style.display = 'none';
    var q = document.getElementById('init_surname').value;
    scroll(0,0);
    get_data(q);
  });

//update map -- search
$j(document).on('submit','#searchSur',function(e) {
    e.preventDefault();
    var q = document.getElementById('surname').value;
    scroll(0,0);
    get_data(q);
  });

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
        if (data.source==='empty'){
          renderNone();
          return;
        // no data found
        } else if (data.source==='none'){
          renderNotFound(data.surname);
          return;
        // data found
        } else if (data.source==='found') {

          //render
          renderHTML(data.surname);
          renderMap(data.years,data.contours,map);
          renderTable(data.hr_freq,data.cr_freq,data.surname);
          renderForenames(data.foremh,data.forefh,data.foremc,data.forefc);
          renderParish(data.partop);
          renderOA(data.oatop);
          renderCAT(data.oacat);
          stopMapLoad();
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
      var pLocation = document.getElementById('locParam');
      var sName = document.createElement('h1');
      var sLoc = document.createElement('h1');

      //create elements
      sName.id = 'searchParam';
      sName.innerHTML = '...';
      sLoc.id = 'locParam';
      sLoc.innerHTML = '...';

      //replace
      pSearch.replaceWith(sName);
      pLocation.replaceWith(sLoc);
    };

//stop loading indicator
function stopMapLoad() {
    document.getElementById('mapload').style.display='none';
  };
