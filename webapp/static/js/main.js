// jQuery
var $j = jQuery.noConflict();

// User select
var strYear = $j('#year_search :selected').val();

// Invoke change on load
$j(function () {
    $j("#year_search").change();
});

// Detect change in year
$j('#year_search').on('change', function(event){
    var selYear = $j('#year_search :selected').val();
    change_year(selYear);
});

// // Autoplay
// var autoPlay = document.getElementById("autoplay");
//
// autoPlay.addEventListener( 'change', function() {
//     if(this.checked) {
//         console.log('on');
//     } else {
//         console.log('off');
//     }
// });

// Detect autoplay in year
// $j('#autoplay').on('change', function(event){
//      var allYear = document.getElementById("year").options.length;
//      console.log(allYear);
//      var button = $j('#autoplay :selected').val();
//      console.log(button);
//      strYear = parseInt(strYear) + 1;
//      change_year(strYear);
//      // function toggleOffByInput() {
//      //   $('#autoplay').prop('checked', false).change()
//      // }
//      // toggleOffByInput();
// });

// Update map

// AJAX for POST
function change_year(selYear) {
    var surName = $j('#name_search').val();
    $j.ajax({
      method: 'POST',
      url: "../search/",
      data: {y: selYear,
             q: surName,
             csrfmiddlewaretoken:$('input[name=csrfmiddlewaretoken]').val()
            },
      success: function (data) {
        renderHTML(data);
      }
    })
  };

// Render HTML
function renderHTML(data) {

// Render contours on map
  contourGroup.clearLayers();
  var contour = new L.polygon([data.contourprj], {

    color: 'red',
    fillColor: '#f03',

    });
  contour.addTo(kdemap);
  contour.addTo(contourGroup);
}
