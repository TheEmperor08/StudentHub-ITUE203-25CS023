<?php
// StudentHub – Practical 7: student inquiry form. The form posts to this same file (POST),
// the data is sanitised and validated on the server, and valid records are stored in a JSON file.
declare(strict_types=1);

require __DIR__ . '/includes/functions.php';
require __DIR__ . '/includes/storage.php';

date_default_timezone_set('Asia/Kolkata');
session_start();

$values = ['name' => '', 'email' => '', 'category' => '', 'message' => ''];
$errors = [];
$formError = '';
$success = $_SESSION['flash'] ?? null;                 // set after a successful POST, shown once
unset($_SESSION['flash']);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $values = sanitize_submission($_POST);

    if (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
        http_response_code(400);
        $formError = 'Your form session has expired or the request was not sent from this form. Please check your details and submit again.';
    } else {
        $errors = validate_submission($values, $_POST);
        if ($errors) {
            http_response_code(422);
        } else {
            try {
                $saved = append_submission([
                    'submitted_at' => date('c'),
                    'name'         => $values['name'],
                    'email'        => $values['email'],
                    'category'     => $values['category'],
                    'message'      => $values['message'],
                ]);
                $_SESSION['flash'] = ['id' => $saved['id'], 'name' => $saved['name']];
                unset($_SESSION['csrf_token']);         // a new token for the next form
                // Post/Redirect/Get: refreshing the success page cannot submit the form twice
                header('Location: index.php?status=sent', true, 303);
                exit;
            } catch (RuntimeException | JsonException $exception) {
                error_log('Practical 7 storage error: ' . $exception->getMessage());
                http_response_code(500);
                $formError = 'Sorry, your inquiry could not be saved because of a server problem. Please try again later.';
            }
        }
    }
}

$token = csrf_token();

// Error message and ARIA attributes for one field
$fieldError = function (string $field) use ($errors): string {
    return isset($errors[$field]) ? '<p class="error-msg" id="' . $field . '-error">' . e($errors[$field]) . '</p>' : '';
};
$fieldAria = function (string $field, string $hint = '') use ($errors): string {
    $describedBy = trim($hint . (isset($errors[$field]) ? " $field-error" : ''));
    return ($describedBy !== '' ? ' aria-describedby="' . $describedBy . '"' : '')
        . (isset($errors[$field]) ? ' aria-invalid="true"' : '');
};
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Inquiry Form - StudentHub</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <p class="brand">StudentHub</p>
            <h1>Student Inquiry Form</h1>
            <p class="subtitle">Send a question to the CSE department helpdesk. Processed with PHP on the server.</p>
        </div>
    </header>

    <main class="container" id="main-content">
        <nav class="page-nav" aria-label="Practical 7 pages">
            <a href="index.php" aria-current="page">Inquiry form</a>
            <a href="records.php">Stored submissions (JSON)</a>
        </nav>

<?php if ($success): ?>
        <div class="alert alert-success" role="status">
            <h2>Inquiry submitted successfully</h2>
            <p>Thank you, <strong><?= e((string) $success['name']) ?></strong>. Your inquiry has been saved with reference <strong><?= e((string) $success['id']) ?></strong>.</p>
            <p><a href="records.php">View the stored submissions</a></p>
        </div>
<?php endif; ?>

<?php if ($formError !== ''): ?>
        <div class="alert alert-error" role="alert">
            <h2>The form could not be submitted</h2>
            <p><?= e($formError) ?></p>
        </div>
<?php elseif ($errors): ?>
        <div class="alert alert-error" role="alert" id="error-summary">
            <h2>Please correct <?= count($errors) ?> <?= count($errors) === 1 ? 'field' : 'fields' ?></h2>
            <ul>
<?php foreach ($errors as $field => $message): ?>
                <li><a href="#<?= e($field) ?>"><?= e($message) ?></a></li>
<?php endforeach; ?>
            </ul>
        </div>
<?php endif; ?>

        <section class="card" aria-labelledby="form-title">
            <h2 id="form-title">Send an inquiry</h2>
            <p class="intro">All fields are required. The form is checked by PHP on the server (the browser's own checks are switched off with <code>novalidate</code> so the server-side validation can be seen).</p>

            <form action="index.php" method="post" novalidate>
                <input type="hidden" name="csrf_token" value="<?= e($token) ?>">

                <div class="form-row">
                    <div class="form-group<?= isset($errors['name']) ? ' has-error' : '' ?>">
                        <label for="name">Full name</label>
                        <input type="text" id="name" name="name" value="<?= e($values['name']) ?>" maxlength="<?= NAME_MAX ?>"
                               autocomplete="name" required<?= $fieldAria('name', 'name-hint') ?>>
                        <p class="hint" id="name-hint">Letters, spaces, dots, apostrophes and hyphens (2–<?= NAME_MAX ?> characters).</p>
                        <?= $fieldError('name') ?>
                    </div>
                    <div class="form-group<?= isset($errors['email']) ? ' has-error' : '' ?>">
                        <label for="email">Email address</label>
                        <input type="email" id="email" name="email" value="<?= e($values['email']) ?>" maxlength="<?= EMAIL_MAX ?>"
                               autocomplete="email" required<?= $fieldAria('email') ?>>
                        <?= $fieldError('email') ?>
                    </div>
                </div>

                <div class="form-group<?= isset($errors['category']) ? ' has-error' : '' ?>">
                    <label for="category">Category</label>
                    <select id="category" name="category" required<?= $fieldAria('category') ?>>
                        <option value="">-- Choose a category --</option>
<?php foreach (CATEGORIES as $key => $label): ?>
                        <option value="<?= e($key) ?>"<?= $values['category'] === $key ? ' selected' : '' ?>><?= e($label) ?></option>
<?php endforeach; ?>
                    </select>
                    <?= $fieldError('category') ?>
                </div>

                <div class="form-group<?= isset($errors['message']) ? ' has-error' : '' ?>">
                    <label for="message">Message</label>
                    <textarea id="message" name="message" rows="5" maxlength="<?= MESSAGE_MAX ?>" required<?= $fieldAria('message', 'message-hint') ?>><?= e($values['message']) ?></textarea>
                    <p class="hint" id="message-hint"><?= MESSAGE_MIN ?>–<?= MESSAGE_MAX ?> characters.</p>
                    <?= $fieldError('message') ?>
                </div>

                <div class="form-actions">
                    <button type="submit" class="btn-primary">Submit inquiry</button>
                    <a class="btn-secondary" href="index.php">Clear form</a>
                </div>
            </form>
        </section>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 7 by Shreyas (25CS023). Submissions are stored locally in a JSON file.</p>
        </div>
    </footer>
</body>
</html>
