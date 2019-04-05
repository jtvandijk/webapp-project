//global
var adminlayer

//icons
var hist = new L.Icon({
  iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

var cont = new L.Icon({
  iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

//top admin areas
function mapAdmin(sel,all,sr) {

  //remove
  if (adminlayer != undefined) {
      amap.removeLayer(adminlayer);
  };

  //render admin
  var markers = new L.featureGroup();
  var admin = JSON.parse(all);
  for (var i=0; i < admin.features.length; ++i) {
    var aa = admin.features[i].geometry.coordinates;
    var id = admin.features[i].properties.id;
    if (sr == 'hr') {
      var name = admin.features[i].properties.parish;
      var regcnty = admin.features[i].properties.regcnty;
      var cnty = admin.features[i].properties.cnty;
      var info = '<strong>'+name+'</strong><br>'+regcnty+' ('+cnty+')'
      icon = hist;
    } else if (sr == 'cr') {
      var name = admin.features[i].properties.ladnm;
      var info = '<strong>'+name+'</strong><br>'+id;
      var icon = cont;
    };
    var mrkr = L.marker([aa[1],aa[0]], {icon: icon, id: id}).bindPopup(info);
    mrkr.addTo(markers);
    };

  //move to location tablist
  $j('#nav-tab a[href="#location"]').tab('show');
  scroll(0,0);

  //map
  adminlayer = markers;
  markers.addTo(amap);
  amap.fitBounds(markers.getBounds().pad(0.1));
  markers.eachLayer(function (layer) {
    if (sel == layer.options.id) {
      layer.openPopup();
    };
  });
};
