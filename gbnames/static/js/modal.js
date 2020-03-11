//modals
var searchmodal = document.getElementById('searchModal');
var modal = document.getElementsByClassName('modal');

//close
var clsBtns = [...document.getElementsByClassName('close')];
clsBtns.forEach(function(btn){
  btn.onclick = function() {
    var parent_modal = btn.parentElement.parentElement.parentElement.parentElement.parentElement.getAttribute('id');
    document.getElementById(parent_modal).style.display = 'none';
  }
});

var clsMdl = [...document.getElementsByClassName('close-modal')];
clsMdl.forEach(function(btn){
  btn.onclick = function() {
    var parent_modal = btn.parentElement.parentElement.parentElement.parentElement.getAttribute('id');
    document.getElementById(parent_modal).style.display = 'none';
  }
});

window.onclick = function(event){
  var clsWindow = [...document.getElementsByClassName('modal')];
  clsWindow.forEach(function(win){
    var win_modal = document.getElementById(win.getAttribute('id'));
    if (event.target == win_modal){
      win_modal.style.display = 'none';
    }
  })
};
