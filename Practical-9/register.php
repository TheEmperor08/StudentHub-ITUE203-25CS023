<?php
// StudentHub – Practical 9: secure user registration.
// GET shows the form; POST checks the CSRF token, validates every field on the server, checks for a
// duplicate username or email, hashes the password with password_hash() and inserts the user together
// with an audit-log entry (MySQLi prepared statements, one transaction).
declare(strict_types=1);

require __DIR__ . '/db.php';
require __DIR__ . '/includes/security.php';
require __DIR__ . '/includes/registration.php';

start_secure_session();
send_security_headers();

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$values = ['full_name' => '', 'username' => '', 'email' => '', 'terms' => false];
$errors = [];
$notice = null;          // general message above the form: ['type' => 'error', 'title' => ..., 'text' => ...]
$registered = null;      // details shown after a successful registration

if ($method === 'POST') {
    if (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
        // Missing or wrong token: nothing is validated or saved, and the submitted values are not shown again
        http_response_code(403);
        $notice = ['title' => 'The form could not be submitted',
                   'text' => 'Your session has expired or the request did not come from this form. Please fill in the form again.'];
    } else {
        [$clean, $errors] = validate_registration($_POST);
        $values = ['full_name' => $clean['full_name'], 'username' => $clean['username'],
                   'email' => $clean['email'], 'terms' => ($_POST['terms'] ?? null) === '1'];
        if (!$errors) {
            try {
                $result = register_user(get_db(), $clean);
                if (isset($result['user_id'])) {
                    session_regenerate_id(true);          // new session ID after the account is created
                    csrf_rotate();
                    $_SESSION['registered'] = ['user_id' => $result['user_id'], 'full_name' => $clean['full_name'],
                                               'username' => $clean['username'], 'email' => $clean['email']];
                    header('Location: register.php?registered=1', true, 303);   // Post/Redirect/Get: no resubmission on refresh
                    exit;
                }
                $errors = $result['errors'];
            } catch (RuntimeException $exception) {      // already logged in db.php or register_user()
                http_response_code(503);
                $notice = ['title' => 'Registration is not available right now',
                           'text' => 'Your details were not saved because of a server problem. Please try again in a few minutes.'];
            }
        }
        if ($errors) {
            http_response_code(422);
            $notice = ['title' => 'Please correct the highlighted fields',
                       'text' => count($errors) === 1 ? '1 field needs attention.' : count($errors) . ' fields need attention.'];
        }
    }
} elseif ($method !== 'GET' && $method !== 'HEAD') {
    http_response_code(405);
    header('Allow: GET, POST');
    $notice = ['title' => 'Method not allowed', 'text' => 'Please use the registration form.'];
} elseif (isset($_SESSION['registered'])) {
    $registered = $_SESSION['registered'];       // shown once; refreshing the page shows an empty form
    unset($_SESSION['registered']);
}

$token = csrf_token();

// Accessible attributes for one field: aria-invalid and aria-describedby pointing at its hint and error
function field_attrs(string $field, array $errors, bool $hasHint = false): string
{
    $ids = array_filter([$hasHint ? "$field-hint" : null, "$field-error"]);
    return ' aria-describedby="' . implode(' ', $ids) . '"' . (isset($errors[$field]) ? ' aria-invalid="true"' : '');
}

function field_error(string $field, array $errors): string
{
    return '<p class="field-error" id="' . $field . '-error">' . e($errors[$field] ?? '') . '</p>';
}

const LABELS = ['full_name' => 'Full name', 'username' => 'Username', 'email' => 'Email address', 'password' => 'Password',
                'confirm_password' => 'Confirm password', 'terms' => 'Terms and conditions'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $registered ? 'Registration successful' : 'Create your account' ?> - StudentHub Practical 9</title>
    <link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="assets/css/style.css">
    <script src="assets/js/register.js" defer></script>
</head>
<body>
    <header class="site-header">
        <div class="container">
            <p class="brand">StudentHub · Practical 9</p>
            <h1>Student Registration</h1>
            <p class="subtitle">Create your StudentHub account</p>
        </div>
    </header>

    <main class="container narrow" id="main">
<?php if ($registered): ?>
        <section class="card success-card" aria-labelledby="success-title">
            <div class="alert alert-success" role="status">
                <h2 id="success-title">Registration successful</h2>
                <p>Welcome to StudentHub, <?= e($registered['full_name']) ?>. Your account has been created.</p>
            </div>
            <dl class="details">
                <dt>User ID</dt><dd><?= e($registered['user_id']) ?></dd>
                <dt>Full name</dt><dd><?= e($registered['full_name']) ?></dd>
                <dt>Username</dt><dd><?= e($registered['username']) ?></dd>
                <dt>Email address</dt><dd><?= e($registered['email']) ?></dd>
                <dt>Role</dt><dd>student</dd>
                <dt>Password</dt><dd>stored only as a secure hash (password_hash) – never shown or saved as text</dd>
            </dl>
            <p><a class="button-link" href="register.php">Register another account</a></p>
        </section>
<?php else: ?>
        <section class="card" aria-labelledby="form-title">
            <h2 id="form-title">Create your account</h2>
            <p class="hint">All fields are required. Your password is stored only as a secure hash.</p>

<?php if ($notice): ?>
            <div class="alert alert-error" role="alert" id="form-alert" tabindex="-1">
                <h3><?= e($notice['title']) ?></h3>
                <p><?= e($notice['text']) ?></p>
<?php if ($errors): ?>
                <ul>
<?php foreach ($errors as $field => $message): ?>
                    <li><a href="#<?= e($field) ?>"><?= e(LABELS[$field] ?? $field) ?>:</a> <?= e($message) ?></li>
<?php endforeach; ?>
                </ul>
<?php endif; ?>
            </div>
<?php endif; ?>

            <form id="register-form" class="register-form" action="register.php" method="post">
                <input type="hidden" name="csrf_token" value="<?= e($token) ?>">

                <div class="field<?= isset($errors['full_name']) ? ' has-error' : '' ?>">
                    <label for="full_name">Full name</label>
                    <input type="text" id="full_name" name="full_name" value="<?= e($values['full_name']) ?>"
                           required minlength="2" maxlength="100" autocomplete="name"<?= field_attrs('full_name', $errors) ?>>
                    <?= field_error('full_name', $errors) ?>
                </div>

                <div class="field<?= isset($errors['username']) ? ' has-error' : '' ?>">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" value="<?= e($values['username']) ?>"
                           required minlength="3" maxlength="30" pattern="[A-Za-z][A-Za-z0-9_]*" autocomplete="username"
                           autocapitalize="none" spellcheck="false"<?= field_attrs('username', $errors, true) ?>>
                    <p class="field-hint" id="username-hint">3–30 characters: letters, numbers and _ , starting with a letter.</p>
                    <?= field_error('username', $errors) ?>
                </div>

                <div class="field<?= isset($errors['email']) ? ' has-error' : '' ?>">
                    <label for="email">Email address</label>
                    <input type="email" id="email" name="email" value="<?= e($values['email']) ?>"
                           required maxlength="254" autocomplete="email" spellcheck="false"<?= field_attrs('email', $errors) ?>>
                    <?= field_error('email', $errors) ?>
                </div>

                <div class="field<?= isset($errors['password']) ? ' has-error' : '' ?>">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required minlength="8" maxlength="72"
                           autocomplete="new-password"<?= field_attrs('password', $errors, true) ?>>
                    <div class="strength" id="strength" hidden>
                        <div class="strength-bar"><span id="strength-fill"></span></div>
                        <p class="strength-label" id="strength-label" aria-live="polite"></p>
                    </div>
                    <ul class="field-hint rules" id="password-hint">
                        <li data-rule="length">8–72 characters</li>
                        <li data-rule="upper">an uppercase letter</li>
                        <li data-rule="lower">a lowercase letter</li>
                        <li data-rule="number">a number</li>
                        <li data-rule="special">a special character (e.g. ! @ # ?)</li>
                    </ul>
                    <?= field_error('password', $errors) ?>
                </div>

                <div class="field<?= isset($errors['confirm_password']) ? ' has-error' : '' ?>">
                    <label for="confirm_password">Confirm password</label>
                    <input type="password" id="confirm_password" name="confirm_password" required minlength="8" maxlength="72"
                           autocomplete="new-password"<?= field_attrs('confirm_password', $errors) ?>>
                    <?= field_error('confirm_password', $errors) ?>
                </div>

                <div class="field checkbox-field<?= isset($errors['terms']) ? ' has-error' : '' ?>">
                    <input type="checkbox" id="terms" name="terms" value="1" required<?= $values['terms'] ? ' checked' : '' ?><?= field_attrs('terms', $errors) ?>>
                    <label for="terms">I accept the StudentHub terms and conditions.</label>
                    <?= field_error('terms', $errors) ?>
                </div>

                <button type="submit">Create account</button>
            </form>
        </section>
<?php endif; ?>
    </main>

    <footer class="site-footer">
        <div class="container"><p>&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 9 by Shreyas (25CS023). All sample accounts are fictional.</p></div>
    </footer>
</body>
</html>
