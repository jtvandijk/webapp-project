//surname frequency chart
var freqhr = document.getElementById('cardFreqHr');
var freqcr = document.getElementById('cardFreqCr');
var max_y = 60000

function renderChartHr(freqs,source,max_y) {

  //context
  var freqSearch = document.getElementById('cardFreqHr');
  var freqDiv = document.createElement('div');
  var freqPar = document.createElement('p');
  var freqCan = document.createElement('canvas');

  freqDiv.className = 'card-body p-2';
  freqDiv.id = 'cardFreqHr';
  freqCan.id = 'freqChartHr';
  freqCan.width = '100';
  freqCan.height = '70';
  freqPar.className = 'card-text text-justify';
  if (source=='load_abs') {
    freqPar.textContent = 'Number of unique surnames that are available in our database for the period 1851-1911. Data for Great Britain, with the exception of 1871 (only Scotland) and 1911 (only England and Wales). Surnames found in the Historic Censuses of Population are only included if they occur at least 30 times in our database.';
  } else {
    freqPar.textContent = 'Absolute number of occurences for your search that is available in our database for the period 1851-1911.';
  };

  //combine HTML elements
  freqDiv.appendChild(freqPar);
  freqDiv.appendChild(freqCan);
  freqSearch.replaceWith(freqDiv);

  //chart
  var ctx = document.getElementById('freqChartHr');
  var fchart = new Chart (ctx, {
  type: 'line',
  data: {
    labels: ['1851','1861','1871','1881','1891','1901','1911'],
      datasets: [{
        data: freqs,
        borderColor: '#3273d1',
        backgroundColor: 'rgba(0,123,250,0.4)',
        pointBackgroundColor: '#000000',
        pointBorderColor: '#000000'
      }]
    },
    options: {
        legend: {
            display: false
          },
        scales: {
            yAxes: [{
            ticks: {
              min: 0,
              max: max_y
            }
            }]
        }
        }
  });
};

function renderChartCr(freqs,source,max_y) {

  //context
  var freqSearch = document.getElementById('cardFreqCr');
  var freqDiv = document.createElement('div');
  var freqPar = document.createElement('p');
  var freqCan = document.createElement('canvas');

  freqDiv.className = 'card-body p-2';
  freqDiv.id = 'cardFreqCr';
  freqCan.id = 'freqChartCr';
  freqCan.width = '100';
  freqCan.height = '70';
  freqPar.className = 'card-text text-justify';
  if (source=='load_abs') {
    freqPar.textContent = 'Number of unique surnames that are available in our database for the period 1997-2016. Data for the entire United Kingdom. Surnames found in our Contemporary Consumer Registers are only included if they occur at least 50 times in our database.';
  } else {
    freqPar.textContent = 'Absolute number of occurences for your search that is available in our database for the period 1997-2016.';
  };

  //combine HTML elements
  freqDiv.appendChild(freqPar);
  freqDiv.appendChild(freqCan);
  freqSearch.replaceWith(freqDiv);

  //chart
  var ctx = document.getElementById('freqChartCr');
  var fchart = new Chart (ctx, {
  type: 'line',
  data: {
    labels: ['1997','1998','1999','2000','2001','2002','2003',
              '2004','2005','2006','2007','2008','2009','2010',
              '2011','2012','2013','2014','2015','2016'],
      datasets: [{
        data: freqs,
        borderColor: '#3273d1',
        backgroundColor: 'rgba(0,123,250,0.4)',
        pointBackgroundColor: '#000000',
        pointBorderColor: '#000000'
      }]
    },
    options: {
        legend: {
            display: false
          },
        scales: {
            yAxes: [{
            ticks: {
              min: 0,
              max: max_y
            }
            }]
        }
        }
  });
};
