// jQuery
var $j = jQuery.noConflict();

//event listener
  $j(document).on('submit', '#locTop', function(e){
  e.preventDefault();
  startLoad();
  getLocation();
});

//start loading indicator
function startLoad() {
  document.getElementById('share-loc').style.display='none';
  document.getElementById('loading-indicator').style.display='inline';
};

//stop loading indicator
function stopLoad() {
  document.getElementById('loading-indicator').style.display='none';
};

//xy through https request
function getLocation() {

    //get location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showPosition);
    }
};

//post xy to django backend
function showPosition(position) {
    var lat = position.coords.latitude;
    var lon = position.coords.longitude;

    $j.ajax({
      method: 'POST',
      url: "../location/",
      data: {latitude: lat,
            longitude: lon,
            csrfmiddlewaretoken:$('input[name=csrfmiddlewaretoken]').val()
            },
      success: function (loclist) {
        stopLoad();
        renderLoclist(loclist);
        renderPieChart(loclist);
      }
    })
};

//list
function renderLoclist(loclist) {

  //render list
  var ul = document.createElement('ul');
  var locdiv = document.getElementById('locList');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var em = document.createElement('em');
  var foot = document.createElement('div');

  div.className = "card-body p-2";
  par.className = "card-text text-justify top";
  par.textContent = "Based on your location, the five most frequently occuring surnames in 2017 in your area are:";
  foot.className = "card-footer small text-justify text-muted p-2";
  foot.textContent = "Please note that these data are aggregated to LSOA-level for privacy reasons.";

  for (var i = 0; i < loclist.topnames.length; ++i) {
    var li = document.createElement('li');
    li.innerHTML = loclist.topnames[i];
    ul.appendChild(li);
  }
  div.appendChild(par);
  div.appendChild(ul);
  container.appendChild(div);
  container.appendChild(foot);
  locdiv.replaceWith(container);
};

//render pie chart
function renderPieChart(loclist) {
  console.log(loclist)
  var show = document.getElementById('collapseArea');
  var feedb = document.getElementById('collapseFeedback');
  var piediv = document.getElementById('pieDiv');
  var pietxt = document.getElementById('pieTxt');
  var par = document.createElement('p');

  par.className = "card-text text-justify top";
  par.textContent = "'Percentage unique' shows the number of unique surnames as a percentage of all individuals at your current location.";
  pietxt.replaceWith(par);
  show.className = 'collapse show';
  feedb.className = 'collapse show';

  var unique = Math.round((loclist.unique / loclist.total)*100);
  var total = Math.round(100-unique);
  var pchart = new Chart(piediv, {
  type: 'pie',
  data: {
    labels: ["Percentage unique"],
    datasets: [{
      data: [total, unique],
      backgroundColor: ["rgb(255, 99, 132)", "rgb(255,205,86)"]
    }]
  }
})};
