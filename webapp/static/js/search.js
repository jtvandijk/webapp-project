//jQuery
var $j = jQuery.noConflict();

//update map -- search
$j(document).on('submit','#searchSur',function(e) {
    e.preventDefault();
    var q = document.getElementById('surname').value;
    get_data(q);
  });

//search surname -- new search
function get_data(q) {
    startMapLoad();
    $j.ajax({
      method: 'POST',
      url: '../udl-namekde/search/',
      //url: '../search/',
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
          renderHTML(data.surname);
          renderMap(data.years,data.contours,map);
          renderChart('hr',data.hr_freq,data.surname);
          renderChart('cr',data.cr_freq,data.surname);
          stopMapLoad();
          return;
        }
      }
    })
  };

//start map loading indicator
function startMapLoad() {

    document.getElementById('mapload').style.display='flex';
    var pSearch = document.getElementById('searchParam');
    var foundExt = document.getElementById('searchExtra');
    var onLoad = document.createElement('p');
    var searchExt = document.createElement('p');

    onLoad.className = 'card-text text-center top pt-3';
    onLoad.id = 'searchParam';
    onLoad.innerHTML = '<br /><strong>LOADING ... </strong><br /><br />This may take up to 30 seconds.';
    searchExt.id = 'searchExtra';

    pSearch.replaceWith(onLoad);
    foundExt.replaceWith(searchExt);

  };

//stop loading indicator
function stopMapLoad() {
    document.getElementById('mapload').style.display='none';
  };
