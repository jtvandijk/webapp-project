// Surname frequency chart
function renderChartCr(freqs,source) {

  //Context
  var freqSearch = document.getElementById('cardFreqHr');
  var freqDiv = document.createElement('div');
  var freqPar = document.createElement('p');
  var freqCan = document.createElement('canvas');

  freqDiv.className = "card-body p-2";
  freqDiv.id = "cardFreq";
  freqCan.id = "freqChart";
  freqCan.width = "100";
  freqCan.height = "70";
  freqPar.className = "card-text text-justify";
  if (source=="load_abs") {
    freqPar.textContent = "Number of unique surnames that are available in our database for the period 1851-1911.";
  } else {
    freqPar.textContent = "Absolute number of occurences for your search that is available in our database for the period 1851-1911.";
  };

  // Combine HTML elements
  freqDiv.appendChild(freqPar);
  freqDiv.appendChild(freqCan);
  freqSearch.replaceWith(freqDiv);

  // Chart
  var ctx = document.getElementById("freqChart");
  var fchart = new Chart (ctx, {
  type: 'line',
  data: {
    labels: ['1851','1861','1871','1881','1891','1901','191'],
      datasets: [{
        data: freqs,
        borderColor: "#3273d1",
        backgroundColor: "rgba(250,123,250,0.4)",
        pointBackgroundColor: "#000000",
        pointBorderColor: "#000000"
      }]
    },
    options: {
        legend: {
            display: false
            }
        }
  });
};


function renderChartCr(freqs,source) {

  //Context
  var freqSearch = document.getElementById('cardFreqCr');
  var freqDiv = document.createElement('div');
  var freqPar = document.createElement('p');
  var freqCan = document.createElement('canvas');

  freqDiv.className = "card-body p-2";
  freqDiv.id = "cardFreq";
  freqCan.id = "freqChart";
  freqCan.width = "100";
  freqCan.height = "70";
  freqPar.className = "card-text text-justify";
  if (source=="load_abs") {
    freqPar.textContent = "Number of unique surnames that are available in our database for the period 1997-2016.";
  } else {
    freqPar.textContent = "Absolute number of occurences for your search that is available in our database for the period 1997-2016.";
  };

  // Combine HTML elements
  freqDiv.appendChild(freqPar);
  freqDiv.appendChild(freqCan);
  freqSearch.replaceWith(freqDiv);

  // Chart
  var ctx = document.getElementById("freqChart");
  var fchart = new Chart (ctx, {
  type: 'line',
  data: {
    labels: [ '1997','1998','1999','2000','2001','2002','2003',
              '2004','2005','2006','2007','2008','2009','2010',
              '2011','2012','2013','2014','2015','2016'],
      datasets: [{
        data: freqs,
        borderColor: "#3273d1",
        backgroundColor: "rgba(0,123,250,0.4)",
        pointBackgroundColor: "#000000",
        pointBorderColor: "#000000"
      }]
    },
    options: {
        legend: {
            display: false
            }
        }
  });
};
