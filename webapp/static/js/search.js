//jQuery
var $j = jQuery.noConflict();

//update map -- search
$j(document).on('submit', '#searchSur', function(e){
  e.preventDefault();
  var q = document.getElementById('surname').value;
  var y = -1;
  get_data(q,y,'search');
});

//update map -- change
// $j(document).on('change', '#searchYear', function(e){
//   e.preventDefault();
//   var q = document.getElementById('surname').value;
//   var y = document.getElementById('searchYear').value;
//   get_data(q,y,'change');
// });

//search surname -- new search
function get_data(selName,selYear,source) {
    var max_y = 60000;
    $j.ajax({
      method: 'POST',
      //url: '../udl-namekde/search/',
      url: '../search/',
      data: {q: selName,
             y: selYear,
             csrfmiddlewaretoken: csrftoken
            },
      success: function (data) {
        // no data entered
        if (data.source==='Empty search'){
          renderNone(data);
          renderChartHr(hr_freq,'load_abs',max_y);
          renderChartCr(cr_freq,'load_abs',max_y);
          return;
        // no data found
        } else if (data.source==='Not in db'){
          renderNotFound(data);
          renderChartHr(hr_freq,'load_abs',max_y);
          renderChartCr(cr_freq,'load_abs',max_y);
          return;
        // data found
        } else if (source==='search') {
          renderHTML(data);
          renderSlider(map,data);
          renderMap(map,data);
          renderChartHr(data.hr_freq,'');
          renderChartCr(data.cr_freq,'');
          return;
        } else {
          return data;
        }
      }
    })
};

//search surname
async function get_update_data(selName,selYear,source) {

    // No new search
    var data = await $j.ajax({
      method: 'POST',
      //url: '../udl-namekde/search/',
      url: '../search/',
      data: {q: selName,
             y: selYear,
             csrfmiddlewaretoken: csrftoken
            },
      success: function (data) {
        return data;
        }
      });

      //create GeoJSON
      var contour = {
        "type": "Feature",
        "geometry": {
          "type": "MultiPolygon",
          "coordinates": [data.contourprj]
          }
      };

      //define style
      var contour_style = {
        color: 'red',
        fillColor: '#f03'
        };

      //prepare for Leaflet
      var contourJSON = L.geoJSON(contour, {style: contour_style});
      return contourJSON;
};
