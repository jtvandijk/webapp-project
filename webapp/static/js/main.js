//jQuery
var $j = jQuery.noConflict();
var jumboBtn = document.getElementById('clsJumbo');

//jumbotron onclick
jumboBtn.onclick = function() {
  jumbotron.style.display = 'none';
};

//onload
$j(document).ready(function() {
  scroll(0,0);
});

//show
function show(cards) {
  cards.splice(0,1);
  cards.forEach(function(card){
  card.classList.add('show');
})};

//popovers
$j(function () {
  $j('[data-toggle="popover"]').popover()
})

//csrf
function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie != '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
          var cookie = jQuery.trim(cookies[i]);
          if (cookie.substring(0,name.length + 1) == (name + '=')) {
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
  beforeSend: function(xhr,settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken",csrftoken);
        }
    }
});
