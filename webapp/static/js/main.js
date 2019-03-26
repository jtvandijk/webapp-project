//jQuery
var $j = jQuery.noConflict();

//csrf
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};
var csrftoken = getCookie('csrftoken');
function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$j.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
          }
      }
});

//chart / geography -- on load
$j(document).ready(function() {
  renderChart('hr',hr_freq);
  renderChart('cr',cr_freq);
});

//chart / max value
function calcMax(maxval) {
  if (maxval < 100) {
    var maxy = 100 * Math.ceil(maxval / 100);
  } else if (maxval < 300) {
    var maxy = 300 * Math.ceil(maxval / 300);
  } else if (maxval < 600) {
    var maxy = 600 * Math.ceil(maxval / 600);
  } else if (maxval < 1000) {
    var maxy = 1000 * Math.ceil(maxval / 1000);
  } else if (maxval < 3000) {
    var maxy = 3000 * Math.ceil(maxval / 3000);
  } else if (maxval < 5000) {
    var maxy = 5000 * Math.ceil(maxval / 5000);
  } else {
    var maxy = 10000 * Math.ceil(maxval / 10000);
  };
  return maxy;
};
