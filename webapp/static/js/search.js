//jQuery
var $j = jQuery.noConflict();

//update map -- search
$j(document).on('submit', '#searchSur', function(e){
  e.preventDefault();
  var q = document.getElementById('surname').value;
  var y = -1;
  get_data(q,y,'search');
});

//search surname -- new search
function get_data(selName,selYear,source) {
    var max_y = 60000;
    $j.ajax({
      method: 'POST',
      url: '../udl-namekde/search/',
      // url: '../search/',
      data: {q: selName,
             y: selYear,
             csrfmiddlewaretoken: csrftoken
            },
      success: function (data) {
        // no data entered
        if (data.source==='Empty search'){
          renderNone(data);
          return;
        // no data found
        } else if (data.source==='Not in db'){
          renderNotFound(data);
          return;
        // data found
        } else if (source==='search') {
          renderHTML(data);
          renderMap(map,data,selYear);
          renderSlider(map,data);
          renderChartHr(data.hr_freq,'',data.clean_sur);
          renderChartCr(data.cr_freq,'',data.clean_sur);
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
      url: '../udl-namekde/search/',
      // url: '../search/',
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
      if (selYear < 1997) {
        var contour_style = {
          color: 'red',
          fillColor: '#f03'
          };
      } else {
        var contour_style = {
          color: 'blue',
          fillColor: '#3273d1'
        }
      };

      //prepare for Leaflet
      var contourJSON = L.geoJSON(contour, {style: contour_style});
      return contourJSON;
};
