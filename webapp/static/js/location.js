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
        renderUniq(loclist);
        showAll();
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
  var topname = document.createElement('h1');
  var foot = document.createElement('div');

  div.className = "card-body p-2";
  par.className = "card-text text-justify top mb-0";
  par.textContent = "Based on your location, the most frequently occuring surname in the area is:";
  topname.className = "text-center p-2";
  topname.style.color = "rgb(77,146,184)";
  topname.innerHTML = loclist.topnames[0];
  foot.className = "card-footer small text-justify text-muted p-2";
  foot.textContent = "Please note that these data are aggregated to LSOA-level for privacy reasons.";

  //var ul = document.createElement('ul');
  // for (var i = 0; i < loclist.topnames.length; ++i) {
  //   var li = document.createElement('li');
  //   li.innerHTML = loclist.topnames[i];
  //   ul.appendChild(li);
  // }
  // div.appendChild(ul);

  div.appendChild(par);
  div.appendChild(topname);
  container.appendChild(div);
  container.appendChild(foot);
  locdiv.replaceWith(container);
};

//alpha value
function renderAlpha(loclist) {
  var alphadiv = document.getElementById('locAlpha');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var alphav = document.createElement('h1');
  var foot = document.createElement('div');

  div.className = "card-body p-2";
  par.className = "card-text text-justify top mb-0";
  par.textContent = "The value below shows the probability that two individuals chosen at random share the same surname at your location.";
  alphav.className = "text-center p-2";
  alphav.style.color = "rgb(189,54,29)";
  alphav.innerHTML = loclist.alpha;
  foot.className = "card-footer small text-justify text-muted p-2";
  foot.textContent = "Value represents the Gini–Simpson Index.";

  div.appendChild(par);
  div.appendChild(alphav);
  container.appendChild(div);
  container.appendChild(foot);
  alphadiv.replaceWith(container);
};

//uniq values
function renderUniq(loclist) {
  var uniqdiv = document.getElementById('locUniq');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var surnames = document.createElement('h1');
  var foot = document.createElement('div');

  div.className = "card-body p-2";
  par.className = "card-text text-justify top mb-0";
  par.textContent = "There is the following number of unique surnames in the area:";
  surnames.className = "text-center p-2";
  surnames.style.color = "rgb(96,175,111)";
  surnames.innerHTML = loclist.unique;
  foot.className = "card-footer small text-justify text-muted p-2";
  foot.textContent = "Please note that these data are aggregated to LSOA-level for privacy reasons.";

  div.appendChild(par);
  div.appendChild(surnames);
  container.appendChild(div);
  container.appendChild(foot);
  uniqdiv .replaceWith(container);
};

//show all
function showAll() {
  var feedb = document.getElementById('collapseFeedback');
  var alpha = document.getElementById('collapseAlpha');
  var uniq = document.getElementById('collapseUniq');
  feedb.className = 'collapse show';
  alpha.className = 'collapse show';
  uniq.className = 'collapse show';
}
