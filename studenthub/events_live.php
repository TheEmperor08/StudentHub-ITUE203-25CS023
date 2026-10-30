<?php
// StudentHub – Event Finder (Practical 13 integrated): events are listed, searched (with debounce) and – depending on the
// role – registered for or managed WITHOUT reloading the page, through the Fetch API and the JSON API api/events.php.
// The server still decides everything: the page only shows what the API returns and sends the CSRF token in a header.
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once __DIR__ . "/includes/event_management.php";
require_once __DIR__ . "/includes/event_registration.php";
$current_user = require_permission("portal.view");
$can_manage   = role_can($current_user["role"], "events.manage");
$can_register = $current_user["role"] === "student" && linked_student($conn, $current_user["id"]) !== null;
$categories   = event_categories($conn);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="<?= e(csrf_token()) ?>">
    <title>Event Finder – StudentHub</title>
    <link rel="stylesheet" href="assets/css/global.css?v=10">
    <script src="assets/js/theme.js"></script>
    <script src="assets/js/events-live.js?v=1" defer></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-lightning-charge"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Campus</p>
            <h1>Event Finder</h1>
            <p>Search campus events instantly<?= $can_manage ? ", publish and edit them" : ($can_register ? " and register" : "") ?> – without reloading the page.</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content" data-can-manage="<?= $can_manage ? "1" : "0" ?>" data-can-register="<?= $can_register ? "1" : "0" ?>">
        <section aria-labelledby="finder-title">
            <h2 id="finder-title"><i class="bi bi-search" aria-hidden="true"></i> Find events</h2>
            <form class="live-toolbar" id="event-filters" role="search" aria-label="Search and filter events" novalidate>
                <div>
                    <label for="live-q">Search</label>
                    <input type="search" id="live-q" name="q" maxlength="100" placeholder="Title, location or description" autocomplete="off">
                </div>
                <div>
                    <label for="live-category">Category</label>
                    <select id="live-category" name="category">
                        <option value="">All categories</option>
                        <?php foreach ($categories as $category): ?>
                            <option value="<?= e($category) ?>"><?= e($category) ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div>
                    <label for="live-status">Registration</label>
                    <select id="live-status" name="status">
                        <option value="">Any status</option>
                        <?php foreach (EVENT_STATUSES as $value => $label): ?>
                            <option value="<?= $value ?>"><?= $label ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div>
                    <label for="live-when">Date</label>
                    <select id="live-when" name="when">
                        <option value="upcoming" selected>Upcoming</option>
                        <option value="past">Past</option>
                        <option value="">All dates</option>
                    </select>
                </div>
                <?php if ($can_manage): ?>
                    <div class="live-toolbar__action"><button type="button" id="new-event"><i class="bi bi-calendar-plus" aria-hidden="true"></i> New event</button></div>
                <?php endif; ?>
            </form>

            <div id="live-message" class="live-message" role="status" aria-live="polite" hidden></div>
            <p id="live-summary" class="section-note" aria-live="polite"></p>
            <div id="live-loading" class="live-loading" hidden><span class="spinner" aria-hidden="true"></span> Loading events…</div>
            <div id="event-results" class="notice-list" aria-busy="false" aria-describedby="live-summary"></div>
            <noscript><p class="alert-error">The Event Finder needs JavaScript. The <a href="notifications.php">Campus Events page</a> works without it.</p></noscript>
        </section>

        <?php if ($can_manage): ?>
            <dialog id="event-dialog" aria-labelledby="event-dialog-title">
                <form id="event-form" method="dialog" novalidate>
                    <h2 id="event-dialog-title">New event</h2>
                    <input type="hidden" name="id" value="">
                    <div class="dialog-grid">
                        <p class="span-2"><label for="f-title">Title</label><input type="text" id="f-title" name="title" maxlength="150"><span class="field-error" id="f-title-error"></span></p>
                        <p><label for="f-category">Category</label>
                            <select id="f-category" name="category"><option value="">Select a category</option>
                                <?php foreach ($categories as $category): ?><option value="<?= e($category) ?>"><?= e($category) ?></option><?php endforeach; ?>
                            </select><span class="field-error" id="f-category-error"></span></p>
                        <p><label for="f-status">Registration</label>
                            <select id="f-status" name="status"><?php foreach (EVENT_STATUSES as $value => $label): ?><option value="<?= $value ?>"><?= $label ?></option><?php endforeach; ?></select>
                            <span class="field-error" id="f-status-error"></span></p>
                        <p><label for="f-event_date">Date</label><input type="date" id="f-event_date" name="event_date"><span class="field-error" id="f-event_date-error"></span></p>
                        <p><label for="f-event_time">Start time (optional)</label><input type="time" id="f-event_time" name="event_time"><span class="field-error" id="f-event_time-error"></span></p>
                        <p><label for="f-location">Location</label><input type="text" id="f-location" name="location" maxlength="150"><span class="field-error" id="f-location-error"></span></p>
                        <p><label for="f-capacity">Capacity (empty = no limit)</label><input type="number" id="f-capacity" name="capacity" min="1" max="65535"><span class="field-error" id="f-capacity-error"></span></p>
                        <p class="span-2"><label for="f-description">Description (optional)</label><textarea id="f-description" name="description" rows="3" maxlength="2000"></textarea><span class="field-error" id="f-description-error"></span></p>
                    </div>
                    <p class="dialog-note">Posters are uploaded in the Admin Console (Campus Events tab).</p>
                    <div class="dialog-actions">
                        <button type="submit" id="event-save">Save event</button>
                        <button type="button" class="btn-secondary" id="event-cancel">Cancel</button>
                    </div>
                </form>
            </dialog>
        <?php endif; ?>
    </main>

    <footer>
        <p>&copy; <time datetime="2026">2026</time> StudentHub – CSPIT, CHARUSAT. All rights reserved.</p>
    </footer>
</div>

</body>
</html>
