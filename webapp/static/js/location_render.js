//global
var parlayer
var oalayer

//icons
var blue = new L.Icon({
  iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

var red = new L.Icon({
  iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

//top parish
function mapParish(parsel,parall) {

  //remove
  if (oalayer != undefined) {
      amap.removeLayer(oalayer);
  };
  if (parlayer != undefined) {
      amap.removeLayer(parlayer);
  };

  //render parishes
  var par_markers = new L.featureGroup();
  var parishes = JSON.parse(parall);
  for (var i=0; i < parishes.features.length; ++i) {
    var p = parishes.features[i].geometry.coordinates;
    var pname = parishes.features[i].properties.parish;
    var regcnty = parishes.features[i].properties.regcnty;
    var cnty = parishes.features[i].properties.cnty;
    var id = parishes.features[i].properties.id;
    var info = '<strong>'+pname+'</strong><br>'+regcnty+' ('+cnty+')'
    var mrkr = L.marker([p[1],p[0]], {icon:red, id: id}).bindPopup(info);

    //group
    mrkr.addTo(par_markers);
    };

  //move to location tablist
  $j('#nav-tab a[href="#location"]').tab('show');
  scroll(0,0);

  //map
  parlayer = par_markers;
  parlayer.addTo(amap);
  amap.fitBounds(parlayer.getBounds().pad(0.1));
  parlayer.eachLayer(function (layer) {
    if (parsel == layer.options.id) {
      layer.openPopup();
    };
  });
};

//top oa
function mapOA(oasel,oaall) {

  //remove
  if (oalayer != undefined) {
      amap.removeLayer(oalayer);
  };
  if (parlayer != undefined) {
      amap.removeLayer(parlayer);
  };

  //render oa
  var oas_markers = new L.featureGroup();
  var oas = JSON.parse(oaall);
  for (var i=0; i < oas.features.length; ++i) {
    var o = oas.features[i].geometry.coordinates;
    var ladname = oas.features[i].properties.ladnm;
    var oaname = oas.features[i].properties.id;
    var info = '<strong>'+ladname+'</strong><br>'+oaname
    var mrkr = L.marker([o[1],o[0]], {icon:blue, id: oaname}).bindPopup(info);

    //group
    mrkr.addTo(oas_markers);
    };

  //move to location tablist
  $j('#nav-tab a[href="#location"]').tab('show');
  scroll(0,0);

  //map
  oalayer = oas_markers;
  oalayer.addTo(amap);
  amap.fitBounds(oalayer.getBounds().pad(0.1));
  oalayer.eachLayer(function (layer) {
    if(oasel == layer.options.id) {
      layer.openPopup();
    };
  });
};
