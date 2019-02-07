//render none
async function renderNone() {

  //delay
  let promise = new Promise((resolve, reject) => {
    setTimeout(() => resolve(""), 700)
  });
  await promise;
  stopMapLoad();

  var pSearch = document.getElementById('searchParam');
  var foundExt = document.getElementById('searchExtra');
  var noText = document.createElement('p');
  var searchExt = document.createElement('p');

  noText.className = 'card-text text-justify top pt-3';
  noText.id = 'searchParam';
  noText.textContent = 'Please type in a surname before hitting submit.';
  searchExt.id = 'searchExtra';

  pSearch.replaceWith(noText);
  foundExt.replaceWith(searchExt);
};

//render not found
async function renderNotFound(surname) {

  //delay
  let promise = new Promise((resolve, reject) => {
    setTimeout(() => resolve(""), 1200)
  });
  await promise;
  stopMapLoad();

  var pSearch = document.getElementById('searchParam');
  var foundExt = document.getElementById('searchExtra');
  var notFound = document.createElement('p');
  var searchExt = document.createElement('p');

  notFound.className = 'card-text text-justify top pt-3';
  notFound.id = 'searchParam';
  notFound.innerHTML = 'Unfortunately, <strong>'+surname+'</strong> is not in our database. Are you sure you did not make a typo?';
  searchExt.id = 'searchExtra';

  pSearch.replaceWith(notFound);
  foundExt.replaceWith(searchExt);
};

//render found
function renderHTML(surname) {

  var pSearch = document.getElementById('searchParam');
  var foundExt = document.getElementById('searchExtra');
  var foundPar = document.createElement('p');
  var foundPar2 = document.createElement('p');

  foundPar.id = 'searchParam';
  foundPar.className = 'card-text text-justify top pt-3';
  foundPar.innerHTML = 'You searched for <strong>'+surname+'</strong>. Use the slider navigation on the map to switch between the years that are available for your search.';
  foundPar2.id = 'searchExtra';
  foundPar2.className = 'card-text text-justify top';
  foundPar2.innerHTML = 'The polygons on the map indicate the areas in which more than 50 per cent of the surname&#39;s population is concentrated. Note that the differences in sizes of the polygons between consecutive years can be minimal.';

  pSearch.replaceWith(foundPar);
  foundExt.replaceWith(foundPar2);
};
