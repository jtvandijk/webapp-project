//show parishes
function showAdmin(id,all,sr) {

  //post
  $j.ajax({
    method: 'POST',
    // url: '../udl-namekde/location/',
    //url: '../gbnames/location/',
    url: '../location/',
    data: {id: id,
           all: all,
           sr: sr,
           csrfmiddlewaretoken: csrftoken
        },
    success: function (data) {
      mapAdmin(data.sel,data.all,data.sr)
    }
  })
};
