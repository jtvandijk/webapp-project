//surname frequency chart
function renderChart(database,freqs,maxy,surname) {

  //context
  var freqDiv = document.createElement('div');
  var freqPar = document.createElement('p');
  var freqCan = document.createElement('canvas');

  freqDiv.className = 'card-body p-2';
  freqCan.width = '100';
  freqCan.height = '70';
  freqPar.className = 'card-text text-justify';

  //render historic or consumer chart
  if (database === 'hr') {
    freqs.splice(2,0,NaN);
    var freqSearch = document.getElementById('cardFreqHr');
    var labels = ['1851','1861','1871','1881','1891','1901','1911'];
    var bordercolor = '#FA2600';
    var backgroundcolor = 'rgba(250,38,0,0.4)';
    freqDiv.id = 'cardFreqHr';
    freqCan.id = 'freqChartHr';
  } else if (database === 'cr') {
    var freqSearch = document.getElementById('cardFreqCr');
    var labels = ['1997','1998','1999','2000','2001','2002','2003',
                  '2004','2005','2006','2007','2008','2009','2010',
                  '2011','2012','2013','2014','2015','2016'];
    var bordercolor = '#3273d1';
    var backgroundcolor = 'rgba(50,115,209,0.4)';
    freqDiv.id = 'cardFreqCr';
    freqCan.id = 'freqChartCr';
  }

  //render absolute or surname chart
  if (surname == null && database === 'hr') {
    var maxy = 60000;
    freqPar.innerHTML = 'This shows the frequency of distinct surnames available in the historic data'
  } else if (surname == null && database === 'cr') {
    freqPar.innerHTML = 'This shows the frequency of distinct surnames available in recent years';
  } else if (surname != null && database === 'hr') {
    freqPar.innerHTML = 'This shows the number of adult and child bearers of <strong>'+surname+'</strong> in historic data.';
  } else if (surname != null && database === 'cr'){
    freqPar.innerHTML = 'This shows the number of adult (only) bearers of <strong>'+surname+'</strong> in recent years.';
  };

  //combine HTML elements
  freqDiv.appendChild(freqPar);
  freqDiv.appendChild(freqCan);
  freqSearch.replaceWith(freqDiv);

  //chart config
  var config = {
  type: 'line',
  data: {
    labels: labels,
      datasets: [{
        data: freqs,
        borderColor: bordercolor,
        backgroundColor: backgroundcolor,
        pointBackgroundColor: '#000000',
        pointBorderColor: '#000000',
        pointRadius: 5,
        spanGaps: true,
      }]},
    options: {legend: { display: false},
        scales: {yAxes: [{ticks: {min: 0, max: maxy}}]}
      }};

  //chart
  if (database === 'hr') {
    var ctx = document.getElementById('freqChartHr');
    var fchart = new Chart (ctx, config)
  } else if (database === 'cr') {
    var ctx = document.getElementById('freqChartCr');
    var fchart = new Chart (ctx, config)
  };

};
