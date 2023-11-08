/**
 * Minified by jsDelivr using Terser v5.19.2.
 * Original file: /gh/mdartic/iso8601-js-period@master/iso8601.js
 *
 * Do NOT use SRI with dynamically generated files! More information: https://www.jsdelivr.com/using-sri-with-dynamic-files
 */
!function(e,r){"function"==typeof define&&define.amd?define([],r):"object"==typeof module&&module.exports?module.exports=r():(e.nezasa||(e.nezasa={}),e.nezasa.iso8601||(e.nezasa.iso8601=r()))}(this,(function(){var e={Period:{}};function r(e,r){var n,o=r||!1,t=[2,3,4,5,7,8,9],i=[0,0,0,0,0,0,0],a=[0,12,4,7,24,60,60];if(!(e=e.toUpperCase()))return i;if("string"!=typeof e)throw new Error("Invalid iso8601 period string '"+e+"'");if(!(n=/^P((\d+Y)?(\d+M)?(\d+W)?(\d+D)?)?(T(\d+H)?(\d+M)?(\d+S)?)?$/.exec(e)))throw new Error("String '"+e+"' is not a valid ISO8601 period.");for(var d=0;d<t.length;d++){var s=t[d];i[d]=n[s]?+n[s].replace(/[A-Za-z]+/g,""):0}if(o)for(d=i.length-1;d>0;d--)i[d]>=a[d]&&(i[d-1]=i[d-1]+Math.floor(i[d]/a[d]),i[d]=i[d]%a[d]);return i}return e.version="0.2",e.Period.parse=function(e,n){return r(e,n)},e.Period.parseToTotalSeconds=function(e){for(var n=[31104e3,2592e3,604800,86400,3600,60,1],o=r(e),t=0,i=0;i<o.length;i++)t+=o[i]*n[i];return t},e.Period.isValid=function(e){try{return r(e),!0}catch(e){return!1}},e.Period.parseToString=function(e,n,o,t){var i=["","","","","","",""],a=r(e,t);n||(n=["year","month","week","day","hour","minute","second"]),o||(o=["years","months","weeks","days","hours","minutes","seconds"]);for(var d=0;d<a.length;d++)a[d]>0&&(1==a[d]?i[d]=a[d]+" "+n[d]:i[d]=a[d]+" "+o[d]);return i.join(" ").trim().replace(/[ ]{2,}/g," ")},e}));
//# sourceMappingURL=/sm/24504ed13cd81fca61d2021541ac0c798d930ab326899831097cb74d840f660a.map