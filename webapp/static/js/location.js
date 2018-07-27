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
        renderAlpha(loclist);
      }
    })
};

//topnames
function renderLoclist(loclist) {

  //render list
  var locdiv = document.getElementById('locList');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var ul = document.createElement('ul');
  var em = document.createElement('em');
  var foot = document.createElement('div');

  div.className = "card-body p-2";
  par.className = "card-text text-justify top";
  par.textContent = "Based on your location, the five most frequently occuring surnames in the area are:";
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

//alpha value
function renderAlpha(loclist) {
  var alphadiv = document.getElementById('locAlpha');
  var show = document.getElementById('collapseAlpha');
  var feedb = document.getElementById('collapseFeedback');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var alphav = document.createElement('h1');
  var stats = document.createElement('p');
  var foot = document.createElement('div');

  div.className = "card-body p-2";
  par.className = "card-text text-justify top mb-0";
  par.textContent = "The value below shows the probability that two individuals chosen at random share the same surname at your location.";
  alphav.className = "text-center p-2";
  alphav.style.color = "rgb(189,54,29)";
  //alphav.innerHTML = loclist.alpha;
  alphav.innerHTML = 0.04244
  stats.className = "card-text text-justify top";
  stats.innerHTML = "In addition, there are "+loclist.total+" individuals sharing a total of "+loclist.unique+" unique surnames in the area."
  foot.className = "card-footer small text-justify text-muted p-2";
  foot.textContent = "Value represents the Gini–Simpson index";

  div.appendChild(par);
  div.appendChild(alphav);
  div.appendChild(stats);
  container.appendChild(div);
  container.appendChild(foot);
  alphadiv.replaceWith(container);

  show.className = 'collapse show';
  feedb.className = 'collapse show';

};
