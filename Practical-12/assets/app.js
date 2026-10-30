// StudentHub – Practical 12: shows a preview of the poster chosen in the add/edit form before it is uploaded.
// Only a convenience – the server validates every file again.
document.addEventListener('change', function (event) {
    var input = event.target;
    if (input.id !== 'poster' || !input.files || !input.files[0]) {
        return;
    }
    var preview = document.getElementById('poster-preview');
    var label = document.getElementById('poster-preview-label');
    var file = input.files[0];
    if (/^image\/(jpeg|png|webp)$/.test(file.type)) {
        preview.src = URL.createObjectURL(file);
        preview.classList.remove('d-none');
        label.textContent = 'Selected: ' + file.name + ' (' + (file.size / 1048576).toFixed(2) + ' MB)';
    } else {
        preview.classList.add('d-none');
        label.textContent = 'Selected: ' + file.name + ' – no preview (not a JPEG, PNG or WebP image)';
    }
});
