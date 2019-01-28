// //basemap
// var map = L.map('kdemap', {
//   timeDimension: true,
// }).setView([54.505, -4], 6);
// L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
//             {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors,\n' +
//             'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
//             minZoom: '6',
//           }).addTo(map);
//
// //bounds
// var southWest = L.latLng(61.0, 4.05),
//     northEast = L.latLng(50.0, -12,01),
//     bounds = L.latLngBounds(southWest, northEast);
//
// map.setMaxBounds(bounds);
//
// //ireland
// L.geoJSON(ireland, {weight: 0, fillColor: '#DCDCDC', fillOpacity: '.8'}).addTo(map);
//
// //layer group
// contourGroup = new L.FeatureGroup();


//temp for currentime
var currentTime = new Date();
currentTime.setUTCDate(1, 0, 0, 0, 0);

var map = L.map('kdemap', {
    zoom: 5,
    fullscreenControl: true,
    timeDimension: true,
    timeDimensionOptions: {
        timeInterval: "2010-01-01/" + currentTime.toISOString(),
        period: "P1M",
        currentTime: currentTime
    },
    center: [54.74, -4.0],
});

var layer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors,\n' +
            'Map tiles by &copy; <a href="https://carto.com/attributions">CARTO</a>',
//            minZoom: '6',
          });
map.addLayer(layer);

//layer group
contourGroup = new L.FeatureGroup();
