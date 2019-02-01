//settings modal
var modal = document.getElementById('acknowledgements_modal');
var link = document.getElementById('acknowledgements');
var span = document.getElementsByClassName('close')[0];

link.onclick = function() {
    modal.style.display = 'block';
}

span.onclick = function() {
    modal.style.display = 'none';
}

window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}
