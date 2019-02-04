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
  renderChartHr(hr_freq,'load_abs');
  renderChartCr(cr_freq,'load_abs');
  setGeo('London')
});

//geography -- on load
$j(document).ready(function() {
  var selLoc = document.getElementById('selLoc').value;
  showGeography(selLoc);
});
