// Map of UK
var kdemap = L.map('kdemap').setView([54.505, -4], 6);
L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}',
            {attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors,\n'  +
            '<a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>,\n'  +
            'Imagery © <a href="https://www.mapbox.com/">Mapbox</a>\n',
            id: 'mapbox.streets',
            minZoom: '5',
            accessToken: 'pk.eyJ1IjoianVzdGludHljaG8iLCJhIjoiY2poMXZ1bG15MDVsZzMzcG14cWVwd2c2YSJ9.An09BWSFACRauEwrVyEl5w'
            }).addTo(kdemap);

var contourGroup = L.layerGroup().addTo(kdemap);
