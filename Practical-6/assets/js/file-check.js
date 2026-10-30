// Classic (non-module) script: it still runs when the page is opened by double-clicking (file://),
// where browsers block ES modules and fetch(). It explains how to open the page correctly.
document.addEventListener('DOMContentLoaded', function () {
    if (window.location.protocol !== 'file:') return;
    document.getElementById('file-warning').hidden = false;
    document.getElementById('app').hidden = true;
});
