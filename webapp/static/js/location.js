//show parishes
function showParish(parid,allid) {

  //post
  $j.ajax({
    method: 'POST',
    url: '../udl-namekde/parish/',
    // url: '../parish/',
    data: {parid: parid,
           allid: allid ,
          csrfmiddlewaretoken: csrftoken
        },
    success: function (data) {
      mapParish(data.parsel,data.parishes)
    }
  })
};

//show oa
function showOA(oaid,alloa) {

  //post
  $j.ajax({
    method: 'POST',
    url: '../udl-namekde/oas/',
    // url: '../oas/',
    data: {oaid: oaid,
           alloa: alloa ,
          csrfmiddlewaretoken: csrftoken
        },
    success: function (data) {
      mapOA(data.oasel,data.oas)
    }
  })
};
