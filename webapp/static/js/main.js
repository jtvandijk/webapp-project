// jQuery
var $j = jQuery.noConflict();

// Update map -- Search
$j(document).on('submit', '#searchSur', function(e){
  e.preventDefault();
  var q = document.getElementById('surname').value;
  var y = -1;
  get_data(q,y,'search');
});

// Update map -- Change
$j(document).on('change', '#searchYear', function(e){
  e.preventDefault();
  var q = document.getElementById('surname').value;
  var y = document.getElementById('searchYear').value;
  get_data(q,y,'change');
});

// Chart -- On Load
$j(document).ready(function() {
  renderChart(abs_freq,'load_abs');
});

// AJAX for POST
function get_data(selName,selYear,source) {
    $j.ajax({
      method: 'POST',
      url: "../search/",
      data: {q: selName,
             y: selYear,
             csrfmiddlewaretoken:$('input[name=csrfmiddlewaretoken]').val()
            },
      success: function (data) {
        // No data entered
        if (data.clean_sur==='Empty Search'){
          renderNone(data);
          renderChart(abs_freq,'load_abs');
        // No data found
        } else if (data.clean_sur==='Not In Db'){
          renderNotFound(data);
          renderChart(abs_freq,'load_abs');
        // Data found
        } else if (source==='search') {
          renderHTML(data);
          renderMap(data);
          renderChart(data.freqs,'');
        // No new search
        } else {
          renderHTML(data);
          renderMap(data);
        }
      }
    })
};

// Render HTML
function renderHTML(data) {
    var pSearch = document.getElementById('searchParam');
    var foundPar = document.createElement('p');
    var foundForm = document.createElement('form');
    var foundList = document.createElement('select');

    foundPar.id = "searchParam";
    foundPar.className = "card-text text-justify top pt-3";
    foundPar.innerHTML = "You searched for <strong>"+data.clean_sur+"</strong>. We have data available for the following years:";

    // Set up empty select option
    foundList.id="searchYear";
    foundList.className="form-control";
    var li = document.createElement('option');
    li.textContent = "Select a year:";
    li.disabled = true;
    foundList.appendChild(li);

    // Set up select options
    for (var i = 0; i < data.data.length; ++i) {
      var li = document.createElement('option');
      li.textContent = data.data[i];
      foundList.appendChild(li);
    }

    // Combine HTML elements
    foundForm.className="my-3";
    foundForm.appendChild(foundList);
    foundPar.appendChild(foundForm);
    pSearch.replaceWith(foundPar);

    // Update value selector
    setSelect(data.year_sel);
};

// Render Map
function renderMap(data) {
  contourGroup.clearLayers();
  var contour = new L.polygon([data.contourprj], {

    color: 'red',
    fillColor: '#f03',

    });
  contour.addTo(kdemap);
  contour.addTo(contourGroup);
};

// Render None
function renderNone(data) {
  contourGroup.clearLayers();

  var pSearch = document.getElementById('searchParam');
  var noText = document.createElement('p');

  noText.className = "card-text text-justify top pt-3";
  noText.id = "searchParam";
  noText.textContent = "Please type in a surname before hitting submit.";

  pSearch.replaceWith(noText);

};

// Render Not Found
function renderNotFound(data) {
  contourGroup.clearLayers();

  var pSearch = document.getElementById('searchParam');
  var notFound = document.createElement('p');

  notFound.className = "card-text text-justify top pt-3";
  notFound.id = "searchParam";
  notFound.innerHTML = "Unfortunately, <strong>"+data.search_sur+"</strong> is not in our database. Are you sure you did not make a typo?";

  pSearch.replaceWith(notFound);
};

// Set value selector
function setSelect(selYear) {
  document.getElementById('searchYear').value = selYear;
}
