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
      // url: '../udl-namekde/search/',
      url: '../search/',
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

          //chart value
          var chartval = data.hr_freq.concat(data.cr_freq);
          var maxval = Math.max.apply(null, chartval)
          if (maxval < 100) {
            var maxy = 100 * Math.ceil(maxval / 100);
          } else if (maxval < 1000) {
            var maxy = 1000 * Math.ceil(maxval / 1000);
          } else if (maxval < 5000) {
            var maxy = 5000 * Math.ceil(maxval / 5000);
          } else {
            var maxy = 10000 * Math.ceil(maxval / 10000);
          }

          //render
          renderHTML(data.surname);
          renderMap(data.years,data.contours,map);
          renderChart('hr',data.hr_freq,maxy,data.surname);
          renderChart('cr',data.cr_freq,maxy,data.surname);
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
