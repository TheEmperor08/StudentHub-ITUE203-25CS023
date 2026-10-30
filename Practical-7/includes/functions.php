<?php
// StudentHub – Practical 7: helper functions for escaping output, sanitising input,
// server-side validation and the CSRF token.
declare(strict_types=1);

const CATEGORIES = [
    'portal'     => 'Portal access',
    'timetable'  => 'Timetable and schedule',
    'attendance' => 'Attendance',
    'results'    => 'Results and marks',
    'other'      => 'Other',
];
const NAME_MAX = 60;
const EMAIL_MAX = 100;
const MESSAGE_MIN = 10;
const MESSAGE_MAX = 1000;

// Escape text for HTML output. Every value shown on a page goes through this function.
function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// Reads one POST field as a string; arrays or missing fields become ''.
function post_string(array $post, string $key): string
{
    $value = $post[$key] ?? '';
    return is_string($value) ? $value : '';
}

// Sanitising: valid UTF-8 only, no control characters, trimmed, whitespace tidied, length capped.
// The cleaned text is stored as plain text; HTML is never trusted, it is escaped when displayed.
function clean_text(string $value, int $maxLength, bool $multiline = false): string
{
    if (!mb_check_encoding($value, 'UTF-8')) {
        return '';
    }
    $value = str_replace(["\r\n", "\r"], "\n", $value);
    $value = $multiline
        ? preg_replace('/[^\P{C}\n\t]/u', '', $value)       // keep new lines and tabs in the message
        : preg_replace('/\p{C}/u', ' ', $value);            // no control characters at all in one-line fields
    $value = $multiline
        ? preg_replace("/\n{3,}/", "\n\n", preg_replace('/[ \t]+/', ' ', $value))
        : preg_replace('/\s+/u', ' ', $value);
    return mb_substr(trim((string) $value), 0, $maxLength + 1);   // +1 so "too long" can still be reported
}

function sanitize_submission(array $post): array
{
    return [
        'name'     => clean_text(post_string($post, 'name'), NAME_MAX),
        'email'    => mb_strtolower(clean_text(post_string($post, 'email'), EMAIL_MAX)),
        'category' => clean_text(post_string($post, 'category'), 20),
        'message'  => clean_text(post_string($post, 'message'), MESSAGE_MAX, true),
    ];
}

// Server-side validation. Returns field => message for every problem (empty array = valid).
function validate_submission(array $data, array $raw): array
{
    $errors = [];
    foreach (['name', 'email', 'category', 'message'] as $field) {
        if (!mb_check_encoding(post_string($raw, $field), 'UTF-8')) {
            $errors[$field] = 'This field contains characters that are not allowed.';
        }
    }

    if (!isset($errors['name'])) {
        $length = mb_strlen($data['name']);
        if ($data['name'] === '') {
            $errors['name'] = 'Please enter your full name.';
        } elseif ($length < 2 || $length > NAME_MAX) {
            $errors['name'] = 'Your name must be 2–' . NAME_MAX . ' characters long.';
        } elseif (!preg_match("/^\p{L}[\p{L} .'-]*$/u", $data['name'])) {
            $errors['name'] = 'Your name can contain only letters, spaces, dots, apostrophes and hyphens.';
        }
    }

    if (!isset($errors['email'])) {
        if ($data['email'] === '') {
            $errors['email'] = 'Please enter your email address.';
        } elseif (mb_strlen($data['email']) > EMAIL_MAX || filter_var($data['email'], FILTER_VALIDATE_EMAIL) === false) {
            $errors['email'] = 'Please enter a valid email address, for example name@example.com.';
        }
    }

    if (!isset($errors['category'])) {
        if ($data['category'] === '') {
            $errors['category'] = 'Please choose a category.';
        } elseif (!array_key_exists($data['category'], CATEGORIES)) {
            $errors['category'] = 'Please choose a category from the list.';
        }
    }

    if (!isset($errors['message'])) {
        $length = mb_strlen($data['message']);
        if ($data['message'] === '') {
            $errors['message'] = 'Please enter your message.';
        } elseif ($length < MESSAGE_MIN) {
            $errors['message'] = 'Your message must be at least ' . MESSAGE_MIN . ' characters long.';
        } elseif ($length > MESSAGE_MAX) {
            $errors['message'] = 'Your message must not be longer than ' . MESSAGE_MAX . ' characters.';
        }
    }
    return $errors;
}

// CSRF protection: a random token kept in the session and sent back in a hidden field.
function csrf_token(): string
{
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function csrf_is_valid(mixed $token): bool
{
    return is_string($token) && isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token);
}
