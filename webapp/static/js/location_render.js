//topname
function renderTopname(loclist) {

  var locdiv = document.getElementById('locTop');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var topname = document.createElement('h1');

  container.id = ('locTop');
  div.className = 'card-body p-2';
  par.className = 'card-text text-justify top mb-0';
  par.textContent = 'The most popular surname at your selected location is:';
  topname.className = 'text-center p-2';
  topname.style.color = 'rgb(77,146,184)';
  topname.innerHTML = loclist.topnames[0];

  div.appendChild(par);
  div.appendChild(topname);
  container.appendChild(div);
  locdiv.replaceWith(container);

  var noLoc = document.getElementById('noLoc');
  var parLoc = document.createElement('p');
  noLoc.replaceWith(parLoc);
  parLoc.id = 'noLoc';
};

//alpha value
function renderAlpha(loclist) {
  var alphadiv = document.getElementById('locAlpha');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var alphav = document.createElement('h1');

  container.id = ('locAlpha');
  div.className = 'card-body p-2';
  par.className = 'card-text text-justify top mb-0';
  par.textContent = 'The value below shows the probability that two individuals chosen at random share the same surname at your selected location.';
  alphav.className = 'text-center p-2';
  alphav.style.color = 'rgb(189,54,29)';
  alphav.innerHTML = loclist.alpha;

  div.appendChild(par);
  div.appendChild(alphav);
  container.appendChild(div);
  alphadiv.replaceWith(container);
};

//uniq values
function renderUniq(loclist) {
  var uniqdiv = document.getElementById('locUniq');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var surnames = document.createElement('h1');

  container.id = ('locUniq');
  div.className = 'card-body p-2';
  par.className = 'card-text text-justify top mb-0';
  par.textContent = 'There is the following number of unique surnames at your selected location:';
  surnames.className = 'text-center p-2';
  surnames.style.color = 'rgb(96,175,111)';
  surnames.innerHTML = loclist.unique;

  div.appendChild(par);
  div.appendChild(surnames);
  container.appendChild(div);
  uniqdiv.replaceWith(container);
};

//topnames
function renderLoclist(loclist) {

  //render list
  var locdiv = document.getElementById('locNames');
  var container = document.createElement('div');
  var div = document.createElement('div');
  var par = document.createElement('p');
  var ul = document.createElement('ul');

  container.id = ('locNames');
  div.className = 'card-body p-2';
  par.className = 'card-text text-justify top';
  par.textContent = 'Besides the most popular surname, the following surnames are also frequently occuring:';

  for (var i = 1; i < loclist.topnames.length; ++i) {
    var li = document.createElement('li');
    li.innerHTML = loclist.topnames[i];
    ul.appendChild(li);
  };

  div.appendChild(par);
  div.appendChild(ul);
  container.appendChild(div);
  locdiv.replaceWith(container);
};

//show all
function showAll() {
  var feedb = document.getElementById('collapseFeedback');
  var alpha = document.getElementById('collapseAlpha');
  var uniq = document.getElementById('collapseUniq');
  var toplst = document.getElementById('collapseNames');
  var toploc = document.getElementById('collapseTop');

  feedb.className = 'collapse show';
  alpha.className = 'collapse show';
  uniq.className = 'collapse show';
  toplst.className = 'collapse show';
  toploc.className = 'collapse show';
};

//topname
function renderNoLoc() {
  var noLoc = document.getElementById('noLoc');
  var parLoc = document.createElement('p');

  parLoc.id = 'noLoc';
  parLoc.className = 'card-text text-justify top pb-0 mb-0';
  parLoc.innerHTML = 'Unfortunately, we were unable to pinpoint your location. Please note that locations outside of <strong>Great Britain</strong> are not supported.';

  noLoc.replaceWith(parLoc);
};
