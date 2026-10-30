<?php
// StudentHub – Campus Data Explorer (Practical 6 integrated): the sample JSON datasets in data/ (students, events, FAQs) are
// loaded with the Fetch API by assets/js/data.js and shown with search, filter, sorting and pagination. The live portal
// records are in the Directory (students) and the Event Finder (events); these files demonstrate client-side rendering.
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
$current_user = require_permission("portal.view");
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campus Data Explorer – StudentHub</title>
    <link rel="stylesheet" href="assets/css/global.css?v=11">
    <script src="assets/js/theme.js"></script>
    <script src="assets/js/data.js?v=2" defer></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-filetype-json"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Campus</p>
            <h1>Campus Data Explorer</h1>
            <p>Students, events and FAQs loaded from JSON files with the Fetch API – search, filter, sort and page through them.</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <section aria-labelledby="explorer-title">
            <h2 id="explorer-title"><i class="bi bi-table" aria-hidden="true"></i> JSON datasets</h2>
            <p class="section-note"><span class="badge badge-sample"><i class="bi bi-info-circle" aria-hidden="true"></i> Sample data</span> These records come from the files in <code>data/</code> (Practical 6). The live student and event records are in the <a href="directory.php">Directory</a> and the <a href="events_live.php">Event Finder</a>.</p>
            <div class="explorer-tabs" role="group" aria-label="Dataset">
                <button type="button" class="tab-btn active" data-type="students">Students</button>
                <button type="button" class="tab-btn" data-type="events">Events</button>
                <button type="button" class="tab-btn" data-type="faqs">FAQs</button>
            </div>
            <div class="live-toolbar explorer-toolbar">
                <div><label for="searchInput">Search</label><input type="search" id="searchInput" placeholder="Search all fields" autocomplete="off"></div>
                <div><label for="filterSelect">Filter</label><select id="filterSelect"><option value="all">All Categories/Branches</option></select></div>
                <div><label for="sortSelect">Sort</label>
                    <select id="sortSelect"><option value="default">Default order</option><option value="name_asc">Name A–Z</option><option value="name_desc">Name Z–A</option></select></div>
            </div>
            <div id="status-container" aria-live="polite"></div>
            <div id="data-table-container"></div>
            <div id="pagination-container" class="pagination-bar"></div>
            <noscript><p class="alert-error">The Data Explorer needs JavaScript.</p></noscript>
        </section>
    </main>

    <footer>
        <p>&copy; <time datetime="2026">2026</time> StudentHub – CSPIT, CHARUSAT. All rights reserved.</p>
    </footer>
</div>

</body>
</html>
