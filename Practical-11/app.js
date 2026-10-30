// StudentHub – Practical 11: disables the submit button once a valid form is sent, so a double click cannot
// submit it twice (the server also refuses a reused form token). Not needed for the application to work.
document.addEventListener('submit', function (event) {
    var button = event.target.querySelector('button[type="submit"]');
    if (button && !event.defaultPrevented) {
        setTimeout(function () { button.disabled = true; button.textContent = 'Saving…'; }, 0);
    }
});
