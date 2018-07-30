// Surname frequency chart
var freq = document.getElementById("cardFreq");
var fchart = new Chart (freq, {
type: 'line',
data: {
  labels: ['1998', '1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', '2009',
           '2010', '2011', '2012','2013','2014','2015','2016','2017'],
    datasets: [{
      label: 'Frequency of surname: {{ search_sur }}',
      data: '{{freqs}}',
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
