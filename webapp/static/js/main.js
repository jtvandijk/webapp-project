//jQuery
var $j = jQuery.noConflict();

//csrf
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};
var csrftoken = getCookie('csrftoken');

//update map -- search
$j(document).on('submit', '#searchSur', function(e){
  e.preventDefault();
  var q = document.getElementById('surname').value;
  var y = -1;
  get_data(q,y,'search');
});

//update map -- change
$j(document).on('change', '#searchYear', function(e){
  e.preventDefault();
  var q = document.getElementById('surname').value;
  var y = document.getElementById('searchYear').value;
  get_data(q,y,'change');
});

//chart / location -- on load
$j(document).ready(function() {
  renderChartHr(hr_freq,'load_abs');
  renderChartCr(cr_freq,'load_abs');
  setGeo('London')
});

//AJAX for POST
function get_data(selName,selYear,source) {
    var max_y = 60000;
    $j.ajax({
      method: 'POST',
      url: '../udl-namekde/search/',
      //url: '../udl-namekde/search/',
      data: {q: selName,
             y: selYear,
             csrfmiddlewaretoken: csrftoken
            },
      success: function (data) {
        // No data entered
        if (data.clean_sur==='Empty Search'){
          renderNone(data);
          renderChartHr(hr_freq,'load_abs',max_y);
          renderChartCr(cr_freq,'load_abs',max_y);
        // No data found
        } else if (data.clean_sur==='Not In Db'){
          renderNotFound(data);
          renderChartHr(hr_freq,'load_abs',max_y);
          renderChartCr(cr_freq,'load_abs',max_y);
        // Data found
        } else if (source==='search') {
          renderHTML(data);
          renderMap(data);
          renderChartHr(data.hr_freq,'');
          renderChartCr(data.cr_freq,'');
        // No new search
        } else {
          renderHTML(data);
          renderMap(data);
        }
      }
    })
};

//render HTML
function renderHTML(data) {
    var pSearch = document.getElementById('searchParam');
    var foundPar = document.createElement('p');
    var foundForm = document.createElement('form');
    var foundList = document.createElement('select');

    foundPar.id = 'searchParam';
    foundPar.className = 'card-text text-justify top pt-3';
    foundPar.innerHTML = 'You searched for <strong>'+data.clean_sur+'</strong>. We have data available for the following years:';

    //set up empty select option
    foundList.id='searchYear';
    foundList.className='form-control';
    var li = document.createElement('option');
    li.textContent = 'Select a year:';
    li.disabled = true;
    foundList.appendChild(li);

    //set up select options
    for (var i = 0; i < data.data.length; ++i) {
      var li = document.createElement('option');
      li.textContent = data.data[i];
      foundList.appendChild(li);
    };

    //combine HTML elements
    foundForm.className='my-3';
    foundForm.appendChild(foundList);
    foundPar.appendChild(foundForm);
    pSearch.replaceWith(foundPar);

    //update value selector
    setSelect(data.year_sel);
};

//render map
function renderMap(data) {
  contourGroup.clearLayers();
  var contour = new L.polygon([data.contourprj], {

    color: 'red',
    fillColor: '#f03',

    });
  contour.addTo(kdemap);
  contour.addTo(contourGroup);
};

//render none
function renderNone(data) {
  contourGroup.clearLayers();

  var pSearch = document.getElementById('searchParam');
  var noText = document.createElement('p');

  noText.className = 'card-text text-justify top pt-3';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';

  pSearch.replaceWith(noText);
};

//render not found
function renderNotFound(data) {
  contourGroup.clearLayers();

  var pSearch = document.getElementById('searchParam');
  var notFound = document.createElement('p');

  notFound.className = 'card-text text-justify top pt-3';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+data.search_sur+'</strong> is not in our database. Are you sure you did not make a typo?';

  pSearch.replaceWith(notFound);
};

//set value selector
function setSelect(selYear) {
  document.getElementById('searchYear').value = selYear;
}

//set geography selector
function setGeo(geo) {
  document.getElementById('selLoc').value = geo;
}
