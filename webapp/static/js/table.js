//surname frequency table
function renderTable(surname,freqs) {

  //years
  var yearshr = ['1851','1861','1881','1891','1901','1911'];
  var yearscr = ['1997','1998','1999','2000','2001','2002','2003','2004','2005','2006','2007','2008','2009','2010','2011','2012','2013','2014','2015','2016'];

  //get elements
  var tableHR = document.getElementById('tableHR');
  var tableCR = document.getElementById('tableCR');

  //create elements
  var hrfreq = populateTable(yearshr,surname,freqs.slice(0,6),);
  var crfreq = populateTable(yearscr,surname,freqs.slice(6,27),);

  //set elements
  hrfreq.id = 'tableHR';
  crfreq.id = 'tableCR';

  //replace
  tableHR.replaceWith(hrfreq);
  tableCR.replaceWith(crfreq);
};

function populateTable(years,surname,freqs) {

  //create elements
  var table = document.createElement('table');
  var caption = document.createElement('caption');
  var head = document.createElement('thead');
  var body = document.createElement('tbody');
  var row1 = document.createElement('tr');
  var row2 = document.createElement('tr');

  //set elements
  table.className = 'table table-sm m-0';
  caption.className = 'py-0 mt-2';
  if (years[0] == 1851) {
    caption.innerHTML = 'Number of bearers of <strong>'+surname.toUpperCase()+'</strong>.';
  } else {
    caption.innerHTML = 'Number of adult bearers of <strong>'+surname.toUpperCase()+'</strong>.';
  }
  row1.className = 'text-center';
  row2.className = 'text-center';

  //table header
  for (var i = 0; i < freqs.length; ++i) {
    var yr = document.createElement('th');
    yr.innerHTML = years[i];
    row1.appendChild(yr);
  };

  //table data
  for (var i = 0; i < freqs.length; ++i) {
    var th = document.createElement('td');
    th.innerHTML = freqs[i].toLocaleString('en');
    row2.appendChild(th);
  };

  //append
  head.appendChild(row1);
  body.appendChild(row2);
  table.appendChild(caption);
  table.appendChild(head);
  table.appendChild(body);

  //return
  return(table);
};
