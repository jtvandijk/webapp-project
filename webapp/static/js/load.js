// jQuery
var $j = jQuery.noConflict();

//event listener
$j(document).on('submit', '#locTop', function(e){
  startLoad();
});

//loading indicator
function startLoad() {
  $j(document).ajaxSend(function(event, request, settings) {
    $j('#share-loc').hide();
    $j('#loading-indicator').show();
  });
}
