<?php
// StudentHub – Practical 12: secure poster upload. Every check happens on the server; the browser's accept
// attribute is only a convenience. The original file name is never used for storage.
//
//  1. PHP upload error code          5. Fileinfo MIME type (of the content) must be JPEG/PNG/WebP AND match the extension
//  2. is_uploaded_file()             6. getimagesize must read a JPEG/PNG/WebP of the same type, 1–6000 px
//  3. size 1 byte – 2 MB             7. the file structure must be complete (not truncated or damaged)
//  4. extension .jpg/.jpeg/.png/.webp 8. the file must not contain PHP code (<?php)
//
// Accepted files get a random name (32 hex characters + extension chosen from the detected type) and are moved into
// the upload folder, which is not reachable over HTTP; posters are delivered only by poster.php.
declare(strict_types=1);

const POSTER_MAX_BYTES = 2 * 1024 * 1024;
const POSTER_MAX_PIXELS = 6000;
const POSTER_EXTENSIONS = ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'];
const POSTER_IMAGE_TYPES = [IMAGETYPE_JPEG => 'jpg', IMAGETYPE_PNG => 'png', IMAGETYPE_WEBP => 'webp'];
const POSTER_NAME_PATTERN = '/^[a-f0-9]{32}\.(jpg|png|webp)$/';

function upload_dir(): string
{
    return rtrim((string) app_config()['upload_dir'], '\\/');
}

// Checks one entry of $_FILES. Returns ['ok' => true, 'tmp' => path, 'ext' => jpg|png|webp] or
// ['ok' => false, 'error' => message]. 'none' => true when no file was chosen.
function validate_poster(mixed $file): array
{
    if (!is_array($file) || !isset($file['error']) || is_array($file['error'])) {
        return ['ok' => false, 'none' => true, 'error' => 'Please choose a poster image.'];
    }
    switch ((int) $file['error']) {
        case UPLOAD_ERR_OK:
            break;
        case UPLOAD_ERR_NO_FILE:
            return ['ok' => false, 'none' => true, 'error' => 'Please choose a poster image.'];
        case UPLOAD_ERR_INI_SIZE:
        case UPLOAD_ERR_FORM_SIZE:
            return ['ok' => false, 'error' => 'The poster is too large for the server. The maximum size is 2 MB.'];
        case UPLOAD_ERR_PARTIAL:
            return ['ok' => false, 'error' => 'The poster was only partly uploaded. Please try again.'];
        default:                                                     // no temp folder, cannot write, blocked by an extension
            error_log('Practical 12 upload error code ' . (int) $file['error']);
            return ['ok' => false, 'error' => 'The server could not receive the poster. Please try again later.'];
    }
    $tmp = (string) ($file['tmp_name'] ?? '');
    if ($tmp === '' || !is_uploaded_file($tmp)) {
        return ['ok' => false, 'error' => 'The poster upload was not valid.'];
    }

    $size = filesize($tmp);
    if ($size === false || $size === 0) {
        return ['ok' => false, 'error' => 'The poster file is empty.'];
    }
    if ($size > POSTER_MAX_BYTES) {
        return ['ok' => false, 'error' => sprintf('The poster is %.1f MB. The maximum size is 2 MB.', $size / 1048576)];
    }

    $extension = strtolower(pathinfo((string) ($file['name'] ?? ''), PATHINFO_EXTENSION));
    if (!isset(POSTER_EXTENSIONS[$extension])) {
        return ['ok' => false, 'error' => 'Invalid file type. Only JPEG, PNG and WebP images (.jpg, .jpeg, .png, .webp) are allowed.'];
    }

    // The file is read once and every content check works on these bytes. Reading can fail when security software
    // on the server blocks a malicious upload; that file is simply rejected.
    $content = @file_get_contents($tmp);
    if ($content === false || strlen($content) !== $size) {
        error_log('Practical 12: an uploaded file could not be read (blocked or removed)');
        return ['ok' => false, 'error' => 'Invalid file type. The file could not be read as an image.'];
    }

    $mime = (new finfo(FILEINFO_MIME_TYPE))->buffer($content);
    if (!in_array($mime, POSTER_EXTENSIONS, true)) {
        return ['ok' => false, 'error' => 'Invalid file type. The file content is not a JPEG, PNG or WebP image.'];
    }
    if ($mime !== POSTER_EXTENSIONS[$extension]) {
        return ['ok' => false, 'error' => 'The file extension does not match its content (.' . $extension . ' file containing ' . $mime . ').'];
    }

    $info = @getimagesizefromstring($content);
    if ($info === false || !isset(POSTER_IMAGE_TYPES[$info[2]]) || image_type_to_mime_type($info[2]) !== $mime
        || !image_structure_ok($content, POSTER_IMAGE_TYPES[$info[2]])) {
        return ['ok' => false, 'error' => 'The poster is not a valid image or is damaged.'];
    }
    if ($info[0] < 1 || $info[1] < 1 || $info[0] > POSTER_MAX_PIXELS || $info[1] > POSTER_MAX_PIXELS) {
        return ['ok' => false, 'error' => 'The poster must be between 1 and ' . POSTER_MAX_PIXELS . ' pixels wide and high.'];
    }

    if (stripos($content, '<?php') !== false) {
        return ['ok' => false, 'error' => 'The poster was rejected because it contains embedded code.'];
    }
    return ['ok' => true, 'tmp' => $tmp, 'ext' => POSTER_IMAGE_TYPES[$info[2]]];
}

// getimagesize() reads only the header, so a truncated or damaged file can still report a size. Without the GD
// extension the structure is checked here: PNG – every chunk up to IEND with a correct CRC; JPEG – start and
// end-of-image markers; WebP – the RIFF length matches the file.
function image_structure_ok(string $data, string $ext): bool
{
    $length = strlen($data);
    if ($ext === 'png') {
        $pos = 8;
        while ($pos + 12 <= $length) {
            $chunk_length = unpack('N', substr($data, $pos, 4))[1];
            $type = substr($data, $pos + 4, 4);
            if ($chunk_length > $length - $pos - 12) {
                return false;                                       // chunk runs past the end of the file
            }
            $crc = unpack('N', substr($data, $pos + 8 + $chunk_length, 4))[1];
            if (crc32($type . substr($data, $pos + 8, $chunk_length)) !== $crc) {
                return false;
            }
            if ($type === 'IEND') {
                return true;
            }
            $pos += 12 + $chunk_length;
        }
        return false;                                               // no IEND chunk: truncated
    }
    if ($ext === 'jpg') {
        return strncmp($data, "\xFF\xD8\xFF", 3) === 0 && strrpos($data, "\xFF\xD9") > 2;
    }
    if ($ext === 'webp') {
        $riff = unpack('V', substr($data, 4, 4))[1] ?? 0;
        return strncmp($data, 'RIFF', 4) === 0 && substr($data, 8, 4) === 'WEBP' && $riff >= 12 && $riff + 8 <= $length;
    }
    return false;
}

// Moves a validated upload into the upload folder under a new random name. Returns the name or null.
function store_poster(array $valid): ?string
{
    $dir = upload_dir();
    if (!is_dir($dir) && !mkdir($dir, 0755, true)) {
        error_log('Practical 12: upload folder missing and could not be created');
        return null;
    }
    do {
        $name = bin2hex(random_bytes(16)) . '.' . $valid['ext'];
    } while (file_exists($dir . DIRECTORY_SEPARATOR . $name));
    if (!move_uploaded_file($valid['tmp'], $dir . DIRECTORY_SEPARATOR . $name)) {
        error_log('Practical 12: move_uploaded_file failed');
        return null;
    }
    @chmod($dir . DIRECTORY_SEPARATOR . $name, 0644);
    return $name;
}

// Full path of a stored poster, or null if the name is not exactly "<32 hex>.<jpg|png|webp>" or the file is
// missing. Names such as "../db.php" can never pass, so no path outside the upload folder can be reached.
function poster_path(string $name): ?string
{
    if (!preg_match(POSTER_NAME_PATTERN, $name)) {
        return null;
    }
    $dir = realpath(upload_dir());
    $path = $dir === false ? false : realpath($dir . DIRECTORY_SEPARATOR . $name);
    if ($path === false || dirname($path) !== $dir || !is_file($path)) {
        return null;
    }
    return $path;
}

// Deletes a poster file, but only a valid name inside the upload folder that no event uses any more
// (poster_filename is also UNIQUE in MySQL, so two events can never share one file).
function delete_poster_file(mysqli $db, ?string $name): bool
{
    if ($name === null || ($path = poster_path($name)) === null) {
        return false;
    }
    $stmt = $db->prepare('SELECT COUNT(*) FROM events WHERE poster_filename = ?');
    $stmt->bind_param('s', $name);
    $stmt->execute();
    if ((int) $stmt->get_result()->fetch_row()[0] > 0) {
        return false;
    }
    return @unlink($path);
}

// Removes a freshly stored poster again when the database step failed (no event refers to it yet)
function discard_new_poster(?string $name): void
{
    if ($name !== null && ($path = poster_path($name)) !== null) {
        @unlink($path);
    }
}
