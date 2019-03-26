//jQuery
var $j = jQuery.noConflict();

//update map -- search on load
$j(document).on('submit','#initSur',function(e) {
    e.preventDefault();
    searchmodal.style.display = 'none';
    var q = document.getElementById('init_surname').value;
    get_data(q);
  });

//update map -- search
$j(document).on('submit','#searchSur',function(e) {
    e.preventDefault();
    var q = document.getElementById('surname').value;
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
          scroll(0,0);
          return;
        // no data found
        } else if (data.source==='none'){
          renderNotFound(data.surname);
          scroll(0,0);
          return;
        // data found
        } else if (data.source==='found') {

          //chart value
          var chartval = data.hr_freq.concat(data.cr_freq);
          var maxval = Math.max.apply(null, chartval);
          var maxy = calcMax(maxval);

          //render
          scroll(0,0);
          renderHTML(data.surname);
          renderMap(data.years,data.contours,map);
          renderChart('hr',data.hr_freq,maxy,data.surname);
          renderChart('cr',data.cr_freq,maxy,data.surname);
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
    var pSearch = document.getElementById('searchParam');
    var onLoad = document.createElement('h1');

    onLoad.id = 'searchParam';
    onLoad.innerHTML = '...';

    //replace
    pSearch.replaceWith(onLoad);
  };

//stop loading indicator
function stopMapLoad() {
    document.getElementById('mapload').style.display='none';
  };
