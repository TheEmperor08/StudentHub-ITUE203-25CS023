<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once __DIR__ . "/includes/student_management.php";
require_once "audit_logger.php";

// 1-2. Signed in, not timed out, account still exists, role holds 'admin.console' – otherwise login page or HTTP 403
$current_user = require_permission("admin.console");

// Confirmation text for a delete button: JSON-encoded (quotes become \u0027) and then HTML-escaped for the attribute
function confirm_js(string $text): string
{
    return e("return confirm(" . json_encode($text, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP) . ");");
}

// Student form helpers: Bootstrap error class, ARIA attributes and the message under a field
function student_field_class(array $form, string $field): string
{
    return isset($form["errors"][$field]) ? " is-invalid" : "";
}

function student_field_aria(array $form, string $field, string $help_id = ""): string
{
    $ids = trim((isset($form["errors"][$field]) ? "$field-error " : "") . $help_id);
    return (isset($form["errors"][$field]) ? ' aria-invalid="true"' : "") . ($ids !== "" ? ' aria-describedby="' . $ids . '"' : "");
}

function student_field_error(array $form, string $field): string
{
    return isset($form["errors"][$field]) ? '<div class="invalid-feedback d-block" id="' . $field . '-error">' . e($form["errors"][$field]) . "</div>" : "";
}

// Student list options (search, course, semester, status, page) – shared by the table and the CSV export
$student_courses = student_courses($conn);
$student_filters = student_filters($_GET, $student_courses);

// 3. CSV export of the filtered student records (read-only; admins only)
if (($_GET["export"] ?? "") === "csv") {
    require_permission("students.manage");
    $export_rows = student_list($conn, $student_filters);
    log_audit($conn, $current_user["id"], $current_user["username"], "EXPORT_CSV",
        "Exported " . count($export_rows) . " student records to CSV (course: " . ($student_filters["course"] ?: "all")
        . ", semester: " . ($student_filters["semester"] ?: "all") . ", status: " . ($student_filters["status"] ?: "all")
        . ($student_filters["q"] !== "" ? ", with a search" : "") . ").", "SUCCESS");
    send_students_csv($export_rows);
    exit();
}

$flash       = take_flash();
$success_msg = ($flash && $flash["type"] === "success") ? $flash["message"] : "";
$error_msg   = ($flash && $flash["type"] === "error") ? $flash["message"] : "";
$current_tab = $_GET["tab"] ?? "overview";
$student_form    = null;   // add/edit form in the Student Records tab: mode, id, record, values, errors
$student_confirm = null;   // record waiting for the deactivation confirmation

// 4. Handle POST Actions (Add Student, Add Event) – every POST must carry the CSRF token
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    $action = $_POST["action"] ?? "";

    // Student records (Practical 11): add, edit, soft delete and reactivation – admins only (students.manage)
    if (in_array($action, ["add_student", "update_student", "deactivate_student", "reactivate_student"], true)) {
        require_permission("students.manage");
        $current_tab = "students";
        $target_id = student_id_from($_POST["id"] ?? "");
        $record    = $target_id > 0 ? find_student_record($conn, $target_id) : null;
        if ($action !== "add_student" && $record === null) {
            flash("error", "That student record was not found."); redirect("admin_dashboard.php?tab=students");
        }
        if ($action === "add_student" || $action === "update_student") {
            $existing = $action === "update_student" ? $record : null;
            [$clean, $errors] = check_student_record($conn, $_POST, $student_courses, $existing, $existing ? $target_id : 0);
            $result = $errors ? ["errors" => $errors] : save_student_record($conn, $clean, $existing ? $target_id : null);
            if (isset($result["errors"])) {
                http_response_code(422);
                $student_form = ["mode" => $existing ? "edit" : "add", "id" => $target_id, "record" => $existing, "errors" => $result["errors"],
                                 "values" => array_map(fn ($field) => is_string($_POST[$field] ?? null) ? $_POST[$field] : "", array_combine(STUDENT_FIELDS, STUDENT_FIELDS))];
            } else {
                $number = $result["enrollment_no"] ?? "no enrollment number";
                log_audit($conn, $current_user["id"], $current_user["username"], $existing ? "UPDATE_STUDENT" : "CREATE_STUDENT",
                    ($existing ? "Updated" : "Added") . " student record ID {$result["id"]} ($number)", "SUCCESS");
                flash("success", $existing ? "Student “{$clean["name"]}” ($number) was updated."
                                           : "Student “{$clean["name"]}” was added with enrollment number $number.");
                redirect("admin_dashboard.php?tab=students");
            }
        } else {
            $activate = $action === "reactivate_student";
            $label    = "“{$record["name"]}” (" . ($record["enrollment_no"] ?: "no enrollment number") . ")";
            if (set_student_status($conn, $target_id, $activate)) {
                log_audit($conn, $current_user["id"], $current_user["username"], $activate ? "REACTIVATE_STUDENT" : "DEACTIVATE_STUDENT",
                    ($activate ? "Reactivated" : "Deactivated (soft delete)") . " student record ID $target_id (" . ($record["enrollment_no"] ?: "no enrollment number") . ")", "SUCCESS");
                flash("success", $activate ? "Student $label was reactivated."
                                           : "Student $label was deactivated. The record, its account link and its event registrations are kept; a linked student account can no longer sign in.");
            } else {
                flash("error", "Student $label is already " . ($activate ? "active." : "inactive."));
            }
            redirect("admin_dashboard.php?tab=students");
        }
    }

    if ($action === "add_event") {
        $title       = trim($_POST["title"] ?? "");
        $category    = trim($_POST["category"] ?? "Academic");
        $event_date  = trim($_POST["event_date"] ?? date("Y-m-d"));
        $location    = trim($_POST["location"] ?? "Campus Auditorium");
        $description = trim($_POST["description"] ?? "");
        $poster_path = null;

        // Poster upload handling
        if (isset($_FILES["poster"]) && $_FILES["poster"]["error"] === UPLOAD_ERR_OK) {
            $file_tmp  = $_FILES["poster"]["tmp_name"];
            $file_name = basename($_FILES["poster"]["name"]);
            $file_size = $_FILES["poster"]["size"];
            $file_ext  = strtolower(pathinfo($file_name, PATHINFO_EXTENSION));
            $allowed   = ["jpg", "jpeg", "png", "webp", "gif"];

            if (!in_array($file_ext, $allowed)) {
                flash("error", "Invalid image format. Allowed: JPG, PNG, WEBP."); redirect("admin_dashboard.php?tab=events");
            } elseif ($file_size > 2 * 1024 * 1024) {
                flash("error", "File exceeds 2MB limit."); redirect("admin_dashboard.php?tab=events");
            } else {
                $upload_dir = __DIR__ . "/uploads/";
                if (!is_dir($upload_dir)) {
                    mkdir($upload_dir, 0777, true);
                }
                $new_filename = "event_" . time() . "_" . bin2hex(random_bytes(4)) . "." . $file_ext;
                $destination  = $upload_dir . $new_filename;
                if (move_uploaded_file($file_tmp, $destination)) {
                    $poster_path = "uploads/" . $new_filename;
                }
            }
        }

        if (empty($title)) {
            flash("error", "Event title is required."); redirect("admin_dashboard.php?tab=events");
        } else {
            $stmt = $conn->prepare("INSERT INTO events (title, category, event_date, location, description, poster) VALUES (?, ?, ?, ?, ?, ?)");
            if ($stmt) {
                $stmt->bind_param("ssssss", $title, $category, $event_date, $location, $description, $poster_path);
                try {
                    $saved = $stmt->execute();
                } catch (mysqli_sql_exception $e) {
                    error_log("StudentHub admin add_event failed: [" . $e->getCode() . "] " . $e->getMessage());
                    flash("error", "The event could not be saved."); redirect("admin_dashboard.php?tab=events");
                }
                if ($saved) {
                    log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "CREATE_EVENT", "Created campus event: $title", "SUCCESS");
                    flash("success", "Campus event published successfully."); redirect("admin_dashboard.php?tab=events");
                } else {
                    flash("error", "The event could not be saved."); redirect("admin_dashboard.php?tab=events");
                }
            }
        }
    }
}

// 5. Delete Event / User – POST only (CSRF token checked above); a GET link can no longer delete anything.
//    Student records are never deleted: they are deactivated instead (soft delete, see above).
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["action"])) {
    $get_action = is_string($_POST["action"]) ? $_POST["action"] : "";
    $target_id  = (int)($_POST["id"] ?? 0);

    if ($get_action === "delete_event" && $target_id > 0) {
        // Fetch poster file to unlink
        $p_stmt = $conn->prepare("SELECT poster FROM events WHERE id = ?");
        if ($p_stmt) {
            $p_stmt->bind_param("i", $target_id);
            $p_stmt->execute();
            $res = $p_stmt->get_result();
            if ($row = $res->fetch_assoc()) {
                if (!empty($row["poster"]) && file_exists(__DIR__ . "/" . $row["poster"])) {
                    @unlink(__DIR__ . "/" . $row["poster"]);
                }
            }
            $p_stmt->close();
        }

        $stmt = $conn->prepare("DELETE FROM events WHERE id = ?");
        if ($stmt) {
            $stmt->bind_param("i", $target_id);
            $stmt->execute();
            log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "DELETE_EVENT", "Deleted event ID: $target_id", "SUCCESS");
            flash("success", "Event deleted successfully."); redirect("admin_dashboard.php?tab=events");
        }
    }

    if ($get_action === "delete_user" && $target_id > 0) {
        if ($target_id === (int)$_SESSION["user_id"]) {
            flash("error", "You cannot delete your own active administrator account."); redirect("admin_dashboard.php?tab=users");
        }
        $stmt = $conn->prepare("DELETE FROM users WHERE id = ?");
        if ($stmt) {
            $stmt->bind_param("i", $target_id);
            $stmt->execute();
            log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "DELETE_USER", "Deleted user ID: $target_id", "SUCCESS");
            flash("success", "User account deleted."); redirect("admin_dashboard.php?tab=users");
        }
    }
}

// 6. Dynamic Metrics Counters
$total_users = 0;
$res = $conn->query("SELECT COUNT(*) as cnt FROM users");
if ($res) { $total_users = (int)$res->fetch_assoc()["cnt"]; }

$total_students = 0;
$res = $conn->query("SELECT COUNT(*) as cnt FROM students");
if ($res) { $total_students = (int)$res->fetch_assoc()["cnt"]; }

$total_events = 0;
$res = $conn->query("SELECT COUNT(*) as cnt FROM events");
if ($res) { $total_events = (int)$res->fetch_assoc()["cnt"]; }

$total_audits = 0;
$res = $conn->query("SELECT COUNT(*) as cnt FROM audit_logs");
if ($res) { $total_audits = (int)$res->fetch_assoc()["cnt"]; }

// 7. Dynamic Menu Items
$menu_items = [];
$m_res = $conn->query("SELECT title, link, icon FROM menu_items WHERE min_role IN ('user', 'editor', 'admin') ORDER BY id ASC");
if ($m_res) {
    while ($m = $m_res->fetch_assoc()) {
        $menu_items[] = $m;
    }
}

// 8. Student Records tab: add/edit form and deactivation confirmation (GET only shows them; nothing is changed)
$student_view = is_string($_GET["view"] ?? null) ? $_GET["view"] : "";
if ($student_form === null && $current_tab === "students" && $student_view === "add") {
    $student_form = ["mode" => "add", "id" => 0, "record" => null, "errors" => [], "values" => array_fill_keys(STUDENT_FIELDS, "")];
} elseif ($student_form === null && $current_tab === "students" && in_array($student_view, ["edit", "deactivate"], true)) {
    $target_id = student_id_from($_GET["id"] ?? "");
    $record    = $target_id > 0 ? find_student_record($conn, $target_id) : null;
    if ($record === null) {
        flash("error", "That student record was not found."); redirect("admin_dashboard.php?tab=students");
    }
    if ($student_view === "edit") {
        $student_form = ["mode" => "edit", "id" => $target_id, "record" => $record, "errors" => [],
                         "values" => array_map(fn ($value) => (string) ($value ?? ""), array_intersect_key($record, array_flip(STUDENT_FIELDS)))];
    } elseif (student_is_active($record)) {
        $student_confirm = $record + ["registrations" => student_registration_count($conn, $target_id)];
    } else {
        flash("error", "Student “{$record["name"]}” is already inactive."); redirect("admin_dashboard.php?tab=students");
    }
}
if ($student_form !== null && $student_form["record"] !== null) {
    $student_form["registrations"] = student_registration_count($conn, $student_form["id"]);
}

// Student list: search + filters + pagination (the same WHERE clause as the CSV export)
$student_total    = student_count($conn, $student_filters);
$student_pages    = max(1, (int) ceil($student_total / STUDENTS_PER_PAGE));
$student_page     = min($student_filters["page"], $student_pages);
$students_list    = student_list($conn, $student_filters, STUDENTS_PER_PAGE, ($student_page - 1) * STUDENTS_PER_PAGE);
$student_counts   = student_status_counts($conn);
$student_filtered = $student_filters["q"] !== "" || $student_filters["course"] !== "" || $student_filters["semester"] !== "" || $student_filters["status"] !== "";

// 9. Events List
$events_list = [];
$ev_res = $conn->query("SELECT * FROM events ORDER BY event_date ASC");
if ($ev_res) {
    while ($ev = $ev_res->fetch_assoc()) { $events_list[] = $ev; }
}

// 10. Users List
$users_list = [];
$u_res = $conn->query("SELECT id, username, email, role, last_login, created_at FROM users ORDER BY id DESC");
if ($u_res) {
    while ($u = $u_res->fetch_assoc()) { $users_list[] = $u; }
}

// 11. Recent Audit Logs
$audit_list = [];
$a_res = $conn->query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50");
if ($a_res) {
    while ($a = $a_res->fetch_assoc()) { $audit_list[] = $a; }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Management Console - StudentHub Portal</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <link rel="stylesheet" href="assets/css/bootstrap-theme.css?v=2">
    <script src="assets/js/theme.js"></script>
    <style>
        :root {
            --primary: #4f46e5;
            --primary-dark: #3730a3;
            --primary-light: #818cf8;
            --secondary: #0f766e;
            --surface: var(--sh-surface);
            --background: var(--sh-page-bg);
            --text-main: var(--bs-body-color);
            --text-muted: var(--bs-secondary-color);
            --border: var(--bs-border-color);
        }
        body {
            background-color: var(--background);
            color: var(--text-main);
            padding-bottom: 50px;
        }
        .main-container {
            max-width: 1200px;
            margin: 28px auto;
            padding: 0 16px;
        }
        .navbar-custom {
            color: #e0e7ff;
            background:
                radial-gradient(60% 140% at 100% 0%, rgba(124, 58, 237, 0.40), transparent 60%),
                linear-gradient(135deg, #121d4a 0%, #0b1437 100%);
            padding: 18px 24px;
            border-radius: 18px;
            box-shadow: 0 18px 40px rgba(11, 20, 55, 0.18);
            margin-bottom: 24px;
        }
        .navbar-custom .text-body { color: #fff !important; }
        .navbar-custom .text-muted { color: rgba(199, 210, 254, 0.78) !important; }
        .navbar-custom .bg-light { background: rgba(255, 255, 255, 0.1) !important; border-color: rgba(255, 255, 255, 0.2) !important; color: #fff; }
        .navbar-custom .btn-outline-primary { --bs-btn-color: #e0e7ff; --bs-btn-border-color: rgba(255, 255, 255, 0.3); --bs-btn-hover-bg: rgba(255, 255, 255, 0.12); --bs-btn-hover-border-color: rgba(255, 255, 255, 0.45); --bs-btn-hover-color: #fff; --bs-btn-active-bg: rgba(255, 255, 255, 0.2); }
        .navbar-custom .btn-outline-danger { --bs-btn-color: #fecaca; --bs-btn-border-color: rgba(254, 202, 202, 0.5); --bs-btn-hover-bg: rgba(239, 68, 68, 0.3); --bs-btn-hover-border-color: #fca5a5; --bs-btn-hover-color: #fff; }
        .admin-brand-mark {
            width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
            color: #fff; font-size: 1.2rem; background: linear-gradient(135deg, #4f46e5, #7c3aed);
            box-shadow: 0 6px 16px rgba(124, 58, 237, 0.35);
        }
        .stat-card {
            background: var(--sh-surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 6px 20px rgba(15, 23, 42, 0.06);
        }
        .stat-icon {
            width: 50px;
            height: 50px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }
        .nav-tabs .nav-link {
            font-weight: 600;
            color: var(--text-muted);
            border: none;
            border-bottom: 3px solid transparent;
            padding: 12px 20px;
        }
        .nav-tabs .nav-link.active {
            color: var(--primary);
            border-bottom: 3px solid #7c3aed;
            background: transparent;
        }
        .tab-content {
            background: var(--sh-surface);
            border: 1px solid var(--border);
            border-top: none;
            border-radius: 0 0 12px 12px;
            padding: 24px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        }
        .badge-role-admin {
            background-color: #fee2e2;
            color: #991b1b;
            font-weight: 700;
        }
        .badge-role-student {
            background-color: #dbeafe;
            color: #1e40af;
            font-weight: 700;
        }
        .badge-role-editor {
            background-color: #fef3c7;
            color: #92400e;
            font-weight: 700;
        }
        .table > :not(caption) > * > * {
            vertical-align: middle;
            padding: 12px 16px;
        }
        .event-poster-thumb {
            width: 50px;
            height: 50px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .student-inactive {
            --bs-table-bg: var(--bs-tertiary-bg);
            --bs-table-color: var(--bs-secondary-color);
        }
        .student-form-card {
            border: 1px solid var(--bs-primary-border-subtle);
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.08);
        }
        .modal-header {
            background: var(--bs-tertiary-bg);
            border-bottom: 1px solid var(--border);
        }
    </style>
</head>
<body>

<div class="main-container">
    <!-- Top Navigation Bar -->
    <div class="navbar-custom d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
            <div class="d-flex align-items-center gap-2">
                <span class="admin-brand-mark" aria-hidden="true"><i class="bi bi-mortarboard-fill"></i></span>
                <span class="fs-4 fw-bold text-body">StudentHub <span class="badge bg-primary text-uppercase" style="font-size: 11px;">Admin Console</span></span>
            </div>
            <p class="text-muted small mb-0">CSPIT - CHARUSAT | Unified Administration & Resource Management (Practical 15)</p>
        </div>
        <div class="d-flex align-items-center gap-3">
            <a href="student_dashboard.php" class="btn btn-outline-primary btn-sm d-flex align-items-center gap-1">
                <i class="bi bi-person-workspace"></i> Student View
            </a>
            <div class="d-flex align-items-center gap-2 bg-light px-3 py-1 rounded-pill border">
                <i class="bi bi-shield-check text-primary"></i>
                <span class="small fw-semibold"><?= htmlspecialchars($_SESSION["username"]) ?></span>
                <span class="badge bg-danger" style="font-size: 10px;">ADMIN</span>
            </div>
            <?= logout_button("btn btn-outline-danger btn-sm", "Logout") ?>
        </div>
    </div>

    <!-- Alert Notifications -->
    <?php if (!empty($success_msg)): ?>
        <div class="alert alert-success alert-dismissible fade show d-flex align-items-center gap-2" role="alert">
            <i class="bi bi-check-circle-fill fs-5"></i>
            <div><?= htmlspecialchars($success_msg) ?></div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    <?php endif; ?>
    <?php if (!empty($error_msg)): ?>
        <div class="alert alert-danger alert-dismissible fade show d-flex align-items-center gap-2" role="alert">
            <i class="bi bi-exclamation-triangle-fill fs-5"></i>
            <div><?= htmlspecialchars($error_msg) ?></div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    <?php endif; ?>

    <!-- Dynamic Metric Stat Cards (Practicals 11 & 14) -->
    <div class="row g-3 mb-4">
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <div>
                    <span class="text-muted small fw-bold">TOTAL USERS</span>
                    <h2 class="fw-bold mb-0 text-primary"><?= $total_users ?></h2>
                </div>
                <div class="stat-icon bg-primary-subtle text-primary">
                    <i class="bi bi-people-fill"></i>
                </div>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <div>
                    <span class="text-muted small fw-bold">STUDENT RECORDS</span>
                    <h2 class="fw-bold mb-0 text-success"><?= $total_students ?></h2>
                </div>
                <div class="stat-icon bg-success-subtle text-success">
                    <i class="bi bi-mortarboard-fill"></i>
                </div>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <div>
                    <span class="text-muted small fw-bold">CAMPUS EVENTS</span>
                    <h2 class="fw-bold mb-0 text-warning"><?= $total_events ?></h2>
                </div>
                <div class="stat-icon bg-warning-subtle text-warning">
                    <i class="bi bi-calendar-event-fill"></i>
                </div>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <div>
                    <span class="text-muted small fw-bold">AUDIT LOGS</span>
                    <h2 class="fw-bold mb-0 text-danger"><?= $total_audits ?></h2>
                </div>
                <div class="stat-icon bg-danger-subtle text-danger">
                    <i class="bi bi-shield-shaded"></i>
                </div>
            </div>
        </div>
    </div>

    <!-- Dynamic RBAC Navigation Bar (Practical 14) -->
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-body p-3">
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                <span class="small fw-bold text-muted text-uppercase"><i class="bi bi-compass me-1"></i> RBAC Dynamic Directory:</span>
                <div class="d-flex flex-wrap gap-2">
                    <?php foreach ($menu_items as $item): ?>
                        <a href="<?= htmlspecialchars($item['link']) ?>" class="btn btn-sm btn-light border d-flex align-items-center gap-1 text-secondary" style="font-size: 12.5px;">
                            <i class="<?= htmlspecialchars($item['icon']) ?>"></i> <?= htmlspecialchars($item['title']) ?>
                        </a>
                    <?php endforeach; ?>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabbed Management Workspaces -->
    <ul class="nav nav-tabs" id="adminTabs" role="tablist">
        <li class="nav-item">
            <button class="nav-link <?= ($current_tab === 'overview') ? 'active' : '' ?>" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button"><i class="bi bi-grid-1x2 me-1"></i> Overview</button>
        </li>
        <li class="nav-item">
            <button class="nav-link <?= ($current_tab === 'students') ? 'active' : '' ?>" id="students-tab" data-bs-toggle="tab" data-bs-target="#students" type="button"><i class="bi bi-mortarboard me-1"></i> Student Records (CRUD)</button>
        </li>
        <li class="nav-item">
            <button class="nav-link <?= ($current_tab === 'events') ? 'active' : '' ?>" id="events-tab" data-bs-toggle="tab" data-bs-target="#events" type="button"><i class="bi bi-calendar-check me-1"></i> Campus Events</button>
        </li>
        <li class="nav-item">
            <button class="nav-link <?= ($current_tab === 'users') ? 'active' : '' ?>" id="users-tab" data-bs-toggle="tab" data-bs-target="#users" type="button"><i class="bi bi-person-gear me-1"></i> User Accounts</button>
        </li>
        <li class="nav-item">
            <button class="nav-link <?= ($current_tab === 'audits') ? 'active' : '' ?>" id="audits-tab" data-bs-toggle="tab" data-bs-target="#audits" type="button"><i class="bi bi-shield-check me-1"></i> Security Audit Trail</button>
        </li>
    </ul>

    <div class="tab-content" id="adminTabsContent">
        <!-- 1. OVERVIEW TAB -->
        <div class="tab-pane fade <?= ($current_tab === 'overview') ? 'show active' : '' ?>" id="overview" role="tabpanel">
            <div class="row g-4">
                <div class="col-lg-7">
                    <h5 class="fw-bold mb-3"><i class="bi bi-activity text-primary me-2"></i>Recent System Activity</h5>
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">
                            <thead class="">
                                <tr>
                                    <th>User</th>
                                    <th>Action</th>
                                    <th>Status</th>
                                    <th>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach (array_slice($audit_list, 0, 6) as $a): ?>
                                    <tr>
                                        <td class="fw-semibold"><?= htmlspecialchars($a['username']) ?></td>
                                        <td><code><?= htmlspecialchars($a['action']) ?></code></td>
                                        <td>
                                            <span class="badge bg-<?= ($a['status'] === 'SUCCESS') ? 'success' : 'danger' ?>-subtle text-<?= ($a['status'] === 'SUCCESS') ? 'success' : 'danger' ?>">
                                                <?= htmlspecialchars($a['status']) ?>
                                            </span>
                                        </td>
                                        <td class="small text-muted"><?= htmlspecialchars(substr($a['created_at'], 11, 8)) ?></td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="col-lg-5">
                    <h5 class="fw-bold mb-3"><i class="bi bi-info-circle text-primary me-2"></i>Platform Specifications</h5>
                    <div class="card border bg-light">
                        <div class="card-body">
                            <ul class="list-unstyled mb-0 small">
                                <li class="mb-2"><strong>Architecture:</strong> Monolithic PHP & MySQL (PDO/MySQLi Dual Driver)</li>
                                <li class="mb-2"><strong>Authentication:</strong> Bcrypt (Cost 10) + Session Fingerprinting</li>
                                <li class="mb-2"><strong>RBAC Enforcement:</strong> 403 Barrier with Audit Trail</li>
                                <li class="mb-2"><strong>Export Formats:</strong> CSV Stream Generator (`fputcsv`)</li>
                                <li class="mb-2"><strong>Database:</strong> <code>studenthub_db</code> (UTF8mb4)</li>
                                <li><strong>Environment:</strong> Local / Cloud Ready (Docker/Render/Heroku/cPanel)</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 2. STUDENT RECORDS TAB (Practical 11: add, edit, search, filter, soft delete, CSV export) -->
        <div class="tab-pane fade <?= ($current_tab === 'students') ? 'show active' : '' ?>" id="students" role="tabpanel">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
                <div>
                    <h5 class="fw-bold mb-1">Student Records</h5>
                    <p class="text-muted small mb-0">Add, edit, search and deactivate student records. Deactivated records are kept with their account link and event registrations.</p>
                </div>
                <div class="d-flex gap-2">
                    <a href="<?= e(student_list_url($student_filters, ["export" => "csv"])) ?>" id="export-students" class="btn btn-outline-success btn-sm d-flex align-items-center gap-1">
                        <i class="bi bi-file-earmark-spreadsheet"></i> Export CSV<?= $student_filtered ? " (filtered)" : "" ?>
                    </a>
                    <a href="admin_dashboard.php?tab=students&amp;view=add#student-form" id="add-student" class="btn btn-primary btn-sm d-flex align-items-center gap-1">
                        <i class="bi bi-person-plus-fill"></i> Add Student
                    </a>
                </div>
            </div>

            <?php if ($student_form !== null): $sf = $student_form; $editing = $sf["mode"] === "edit"; ?>
                <section class="card student-form-card mb-4" id="student-form" aria-labelledby="student-form-title">
                    <div class="card-body">
                        <h6 class="fw-bold mb-1" id="student-form-title"><i class="bi bi-<?= $editing ? "pencil-square" : "person-plus" ?> text-primary me-2"></i><?= $editing ? "Edit student record" : "Add a student record" ?></h6>
                        <p class="text-muted small mb-3">
                            <?php if ($editing): ?>
                                Record #<?= (int) $sf["id"] ?> · <?= student_is_active($sf["record"]) ? "Active" : "Inactive" ?> · <?= $sf["record"]["user_id"] !== null ? "linked to a login account" : "no login account" ?> · <?= (int) $sf["registrations"] ?> event registration(s). Saving changes only the fields below; the status, the account link and the registrations stay as they are.
                            <?php else: ?>
                                Creates the student record only – no login account is created. All fields are checked on the server.
                            <?php endif; ?>
                        </p>
                        <?php if ($sf["errors"]): ?>
                            <div class="alert alert-danger py-2 small" role="alert"><i class="bi bi-exclamation-triangle-fill me-1"></i> Please correct the highlighted fields. Nothing was saved.</div>
                        <?php endif; ?>
                        <form method="post" action="admin_dashboard.php?tab=students#student-form" novalidate>
                            <?= csrf_field() ?>
                            <input type="hidden" name="action" value="<?= $editing ? "update_student" : "add_student" ?>">
                            <?php if ($editing): ?><input type="hidden" name="id" value="<?= (int) $sf["id"] ?>"><?php endif; ?>
                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label for="enrollment_no" class="form-label small fw-bold">Enrollment number</label>
                                    <input type="text" id="enrollment_no" name="enrollment_no" maxlength="20" autocomplete="off" placeholder="e.g. 26IT004"
                                           class="form-control<?= student_field_class($sf, "enrollment_no") ?>" value="<?= e($sf["values"]["enrollment_no"]) ?>"<?= student_field_aria($sf, "enrollment_no", "enrollment_no-help") ?>>
                                    <?= student_field_error($sf, "enrollment_no") ?>
                                    <div class="form-text" id="enrollment_no-help"><?= $editing ? "Format: 2 digits, 2 letters, 3 digits (e.g. 25CS011)." : "Leave empty to assign the next free number (admission year from the semester + course code)." ?></div>
                                </div>
                                <div class="col-md-8">
                                    <label for="name" class="form-label small fw-bold">Full name</label>
                                    <input type="text" id="name" name="name" maxlength="100" autocomplete="off"
                                           class="form-control<?= student_field_class($sf, "name") ?>" value="<?= e($sf["values"]["name"]) ?>"<?= student_field_aria($sf, "name") ?>>
                                    <?= student_field_error($sf, "name") ?>
                                </div>
                                <div class="col-md-6">
                                    <label for="email" class="form-label small fw-bold">Email address</label>
                                    <input type="email" id="email" name="email" maxlength="100" autocomplete="off"
                                           class="form-control<?= student_field_class($sf, "email") ?>" value="<?= e($sf["values"]["email"]) ?>"<?= student_field_aria($sf, "email") ?>>
                                    <?= student_field_error($sf, "email") ?>
                                </div>
                                <div class="col-md-6">
                                    <label for="course" class="form-label small fw-bold">Course</label>
                                    <select id="course" name="course" class="form-select<?= student_field_class($sf, "course") ?>"<?= student_field_aria($sf, "course") ?>>
                                        <option value="">Select a course</option>
                                        <?php foreach ($student_courses as $course): ?>
                                            <option value="<?= e($course) ?>"<?= $sf["values"]["course"] === $course ? " selected" : "" ?>><?= e($course) ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                    <?= student_field_error($sf, "course") ?>
                                </div>
                                <div class="col-md-3">
                                    <label for="semester" class="form-label small fw-bold">Semester</label>
                                    <select id="semester" name="semester" class="form-select<?= student_field_class($sf, "semester") ?>"<?= student_field_aria($sf, "semester") ?>>
                                        <option value="">Select</option>
                                        <?php for ($sem = 1; $sem <= 8; $sem++): ?>
                                            <option value="<?= $sem ?>"<?= $sf["values"]["semester"] === (string) $sem ? " selected" : "" ?>>Semester <?= $sem ?></option>
                                        <?php endfor; ?>
                                    </select>
                                    <?= student_field_error($sf, "semester") ?>
                                </div>
                                <fieldset class="col-md-9"<?= student_field_aria($sf, "gender") ?>>
                                    <legend class="form-label small fw-bold mb-2">Gender</legend>
                                    <?php
                                    $genders = REGISTRATION_GENDERS;
                                    if ($editing && $sf["record"]["gender"] !== "" && !in_array($sf["record"]["gender"], $genders, true)) {
                                        $genders[] = $sf["record"]["gender"];             // legacy value, kept as it is
                                    }
                                    foreach ($genders as $i => $gender): ?>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input<?= student_field_class($sf, "gender") ?>" type="radio" name="gender" id="gender-<?= $i ?>" value="<?= e($gender) ?>"<?= $sf["values"]["gender"] === $gender ? " checked" : "" ?>>
                                            <label class="form-check-label" for="gender-<?= $i ?>"><?= e($gender) ?></label>
                                        </div>
                                    <?php endforeach; ?>
                                    <?= student_field_error($sf, "gender") ?>
                                </fieldset>
                            </div>
                            <div class="d-flex gap-2 mt-4">
                                <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check2-circle me-1"></i><?= $editing ? "Save changes" : "Add student" ?></button>
                                <a href="admin_dashboard.php?tab=students" class="btn btn-outline-secondary btn-sm">Cancel</a>
                            </div>
                        </form>
                    </div>
                </section>
            <?php endif; ?>

            <?php if ($student_confirm !== null): $sc = $student_confirm; ?>
                <section class="card border-danger-subtle mb-4" id="student-confirm" aria-labelledby="student-confirm-title">
                    <div class="card-body">
                        <h6 class="fw-bold text-danger mb-2" id="student-confirm-title"><i class="bi bi-person-dash me-2"></i>Deactivate this student?</h6>
                        <p class="small mb-3">Are you sure you want to deactivate <strong><?= e($sc["name"]) ?></strong>? The status changes from <strong>Active</strong> to <strong>Inactive</strong>. This is a soft delete: the record stays in the database with its account link and its <?= (int) $sc["registrations"] ?> event registration(s), it still appears in this list and in the CSV export, and it can be reactivated later. Inactive students cannot sign in or register for new events; a student who is signed in loses access at the next page request.</p>
                        <dl class="row small mb-3">
                            <dt class="col-sm-3">Enrollment number</dt><dd class="col-sm-9"><?= e($sc["enrollment_no"] ?: "—") ?></dd>
                            <dt class="col-sm-3">Email</dt><dd class="col-sm-9"><?= e($sc["email"]) ?></dd>
                            <dt class="col-sm-3">Course / semester</dt><dd class="col-sm-9"><?= e($sc["course"]) ?> · <?= $sc["semester"] !== null ? "Semester " . (int) $sc["semester"] : "—" ?></dd>
                            <dt class="col-sm-3">Login account</dt><dd class="col-sm-9"><?= $sc["user_id"] !== null ? "Linked (kept)" : "None" ?></dd>
                        </dl>
                        <form method="post" action="admin_dashboard.php?tab=students" class="d-flex gap-2">
                            <?= csrf_field() ?>
                            <input type="hidden" name="action" value="deactivate_student">
                            <input type="hidden" name="id" value="<?= (int) $sc["id"] ?>">
                            <button type="submit" class="btn btn-danger btn-sm"><i class="bi bi-person-dash me-1"></i>Yes, deactivate student</button>
                            <a href="admin_dashboard.php?tab=students" class="btn btn-outline-secondary btn-sm">Cancel</a>
                        </form>
                    </div>
                </section>
            <?php endif; ?>

            <!-- Search and filters (combined; GET, so the result can be bookmarked and exported) -->
            <form method="get" action="admin_dashboard.php" class="row g-2 mb-3" role="search" aria-label="Search and filter student records">
                <input type="hidden" name="tab" value="students">
                <div class="col-lg-4 col-md-6">
                    <label for="student-q" class="visually-hidden">Search</label>
                    <input type="search" id="student-q" name="q" maxlength="100" class="form-control form-control-sm" placeholder="Search name, email or enrollment no." value="<?= e($student_filters["q"]) ?>">
                </div>
                <div class="col-lg-3 col-md-6">
                    <label for="student-course" class="visually-hidden">Course</label>
                    <select id="student-course" name="course" class="form-select form-select-sm">
                        <option value="">All courses</option>
                        <?php foreach ($student_courses as $course): ?>
                            <option value="<?= e($course) ?>"<?= $student_filters["course"] === $course ? " selected" : "" ?>><?= e($course) ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-lg-2 col-md-4">
                    <label for="student-semester" class="visually-hidden">Semester</label>
                    <select id="student-semester" name="semester" class="form-select form-select-sm">
                        <option value="">All semesters</option>
                        <?php for ($sem = 1; $sem <= 8; $sem++): ?>
                            <option value="<?= $sem ?>"<?= $student_filters["semester"] === (string) $sem ? " selected" : "" ?>>Semester <?= $sem ?></option>
                        <?php endfor; ?>
                    </select>
                </div>
                <div class="col-lg-2 col-md-4">
                    <label for="student-status" class="visually-hidden">Status</label>
                    <select id="student-status" name="status" class="form-select form-select-sm">
                        <option value="">All statuses</option>
                        <?php foreach (STUDENT_STATUSES as $status): ?>
                            <option value="<?= $status ?>"<?= $student_filters["status"] === $status ? " selected" : "" ?>><?= $status ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-lg-1 col-md-4 d-grid">
                    <button type="submit" class="btn btn-secondary btn-sm"><i class="bi bi-search"></i> Filter</button>
                </div>
            </form>

            <div class="d-flex flex-wrap justify-content-between align-items-center small text-muted mb-2 gap-2">
                <span id="student-summary">
                    <?php if ($student_total > 0): ?>
                        Showing <?= ($student_page - 1) * STUDENTS_PER_PAGE + 1 ?>–<?= ($student_page - 1) * STUDENTS_PER_PAGE + count($students_list) ?> of <?= $student_total ?> <?= $student_filtered ? "matching " : "" ?>record<?= $student_total === 1 ? "" : "s" ?>
                    <?php else: ?>
                        No records shown
                    <?php endif; ?>
                    · <?= $student_counts["Active"] ?> active, <?= $student_counts["Inactive"] ?> inactive in total
                </span>
                <?php if ($student_filtered): ?>
                    <a href="admin_dashboard.php?tab=students" class="link-secondary">Reset filters</a>
                <?php endif; ?>
            </div>

            <div class="table-responsive">
                <table class="table table-hover table-bordered align-middle" id="student-table">
                    <caption class="visually-hidden">Student records</caption>
                    <thead>
                        <tr>
                            <th scope="col">Enrollment</th>
                            <th scope="col">Name</th>
                            <th scope="col">Email</th>
                            <th scope="col">Course</th>
                            <th scope="col">Sem</th>
                            <th scope="col">Status</th>
                            <th scope="col">Account</th>
                            <th scope="col" class="text-center">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (empty($students_list)): ?>
                            <tr><td colspan="8" class="text-center py-4 text-muted">
                                <?php if ($student_filtered): ?>
                                    No student records match these filters. <a href="admin_dashboard.php?tab=students">Show all records</a>
                                <?php else: ?>
                                    No student records yet. <a href="admin_dashboard.php?tab=students&amp;view=add#student-form">Add the first student</a>
                                <?php endif; ?>
                            </td></tr>
                        <?php else: ?>
                            <?php foreach ($students_list as $st): $active = student_is_active($st); ?>
                                <tr<?= $active ? "" : ' class="student-inactive"' ?>>
                                    <td><span class="badge bg-light text-dark border"><?= e($st["enrollment_no"] ?: "—") ?></span></td>
                                    <td class="fw-semibold"><?= e($st["name"]) ?></td>
                                    <td class="small"><?= e($st["email"]) ?></td>
                                    <td><span class="badge bg-primary-subtle text-primary"><?= e($st["course"]) ?></span></td>
                                    <td><?= $st["semester"] !== null ? (int) $st["semester"] : "—" ?></td>
                                    <td>
                                        <?php if ($active): ?>
                                            <span class="badge bg-success-subtle text-success">Active</span>
                                        <?php else: ?>
                                            <span class="badge bg-danger-subtle text-danger">Inactive</span>
                                        <?php endif; ?>
                                    </td>
                                    <td class="small">
                                        <?php if ($st["user_id"] !== null): ?>
                                            <span class="badge bg-info-subtle text-info-emphasis"><i class="bi bi-link-45deg"></i> Linked</span>
                                        <?php else: ?>
                                            <span class="text-muted">None</span>
                                        <?php endif; ?>
                                    </td>
                                    <td class="text-center text-nowrap">
                                        <a href="admin_dashboard.php?tab=students&amp;view=edit&amp;id=<?= (int) $st["id"] ?>#student-form" class="btn btn-outline-primary btn-sm py-0 px-2" aria-label="Edit <?= e($st["name"]) ?>"><i class="bi bi-pencil"></i> Edit</a>
                                        <?php if ($active): ?>
                                            <a href="admin_dashboard.php?tab=students&amp;view=deactivate&amp;id=<?= (int) $st["id"] ?>#student-confirm" class="btn btn-outline-danger btn-sm py-0 px-2" aria-label="Deactivate <?= e($st["name"]) ?>"><i class="bi bi-person-dash"></i> Deactivate</a>
                                        <?php else: ?>
                                            <form method="post" action="admin_dashboard.php?tab=students" class="d-inline"><?= csrf_field() ?><input type="hidden" name="action" value="reactivate_student"><input type="hidden" name="id" value="<?= (int) $st["id"] ?>"><button type="submit" class="btn btn-outline-success btn-sm py-0 px-2" aria-label="Reactivate <?= e($st["name"]) ?>"><i class="bi bi-arrow-counterclockwise"></i> Reactivate</button></form>
                                        <?php endif; ?>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>

            <?php if ($student_pages > 1): ?>
                <nav aria-label="Student record pages">
                    <ul class="pagination pagination-sm justify-content-center mb-0">
                        <li class="page-item<?= $student_page <= 1 ? " disabled" : "" ?>"><a class="page-link" href="<?= e(student_list_url($student_filters, ["page" => max(1, $student_page - 1)])) ?>">Previous</a></li>
                        <?php for ($pg = 1; $pg <= $student_pages; $pg++): ?>
                            <li class="page-item<?= $pg === $student_page ? " active" : "" ?>"><a class="page-link" href="<?= e(student_list_url($student_filters, ["page" => $pg])) ?>"<?= $pg === $student_page ? ' aria-current="page"' : "" ?>><?= $pg ?></a></li>
                        <?php endfor; ?>
                        <li class="page-item<?= $student_page >= $student_pages ? " disabled" : "" ?>"><a class="page-link" href="<?= e(student_list_url($student_filters, ["page" => min($student_pages, $student_page + 1)])) ?>">Next</a></li>
                    </ul>
                </nav>
            <?php endif; ?>
        </div>

        <!-- 3. CAMPUS EVENTS TAB (Practical 12) -->
        <div class="tab-pane fade <?= ($current_tab === 'events') ? 'show active' : '' ?>" id="events" role="tabpanel">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
                <div>
                    <h5 class="fw-bold mb-1">Campus Events Management</h5>
                    <p class="text-muted small mb-0">Publish technical symposia, hackathons, and cultural campus events with poster uploads.</p>
                </div>
                <button class="btn btn-warning btn-sm d-flex align-items-center gap-1 text-body fw-bold" data-bs-toggle="modal" data-bs-target="#addEventModal">
                    <i class="bi bi-calendar-plus-fill"></i> Add New Event
                </button>
            </div>

            <div class="table-responsive">
                <table class="table table-hover table-bordered align-middle">
                    <thead class="">
                        <tr>
                            <th>Poster</th>
                            <th>Event Title</th>
                            <th>Category</th>
                            <th>Event Date</th>
                            <th>Location</th>
                            <th>Description</th>
                            <th class="text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (empty($events_list)): ?>
                            <tr><td colspan="7" class="text-center py-4 text-muted">No campus events published yet.</td></tr>
                        <?php else: ?>
                            <?php foreach ($events_list as $ev): ?>
                                <tr>
                                    <td>
                                        <?php if (!empty($ev['poster']) && file_exists(__DIR__ . "/" . $ev['poster'])): ?>
                                            <img src="<?= htmlspecialchars($ev['poster']) ?>" alt="Poster" class="event-poster-thumb">
                                        <?php else: ?>
                                            <div class="event-poster-thumb bg-light d-flex align-items-center justify-content-center text-muted">
                                                <i class="bi bi-image"></i>
                                            </div>
                                        <?php endif; ?>
                                    </td>
                                    <td class="fw-bold text-body"><?= htmlspecialchars($ev['title']) ?></td>
                                    <td><span class="badge bg-secondary-subtle text-secondary"><?= htmlspecialchars($ev['category']) ?></span></td>
                                    <td class="small fw-semibold"><?= htmlspecialchars($ev['event_date']) ?></td>
                                    <td class="small text-muted"><i class="bi bi-geo-alt-fill text-danger me-1"></i><?= htmlspecialchars($ev['location']) ?></td>
                                    <td class="small text-muted" style="max-width: 250px;"><?= htmlspecialchars(substr($ev['description'] ?? '', 0, 80)) ?>...</td>
                                    <td class="text-center">
                                        <form method="post" action="admin_dashboard.php?tab=events" class="d-inline" onsubmit="<?= confirm_js('Delete event ' . $ev['title'] . ' and its poster image?') ?>"><?= csrf_field() ?><input type="hidden" name="action" value="delete_event"><input type="hidden" name="id" value="<?= (int) $ev['id'] ?>"><button type="submit" class="btn btn-outline-danger btn-sm py-0 px-2"><i class="bi bi-trash"></i> Delete</button></form>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 4. USERS TAB (Practicals 9 & 10) -->
        <div class="tab-pane fade <?= ($current_tab === 'users') ? 'show active' : '' ?>" id="users" role="tabpanel">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
                <div>
                    <h5 class="fw-bold mb-1">User Accounts & Role Management</h5>
                    <p class="text-muted small mb-0">RBAC accounts with encrypted Bcrypt credentials and authentication tracking.</p>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover table-bordered align-middle">
                    <thead class="">
                        <tr>
                            <th>#ID</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Assigned Role</th>
                            <th>Last Login</th>
                            <th>Registered On</th>
                            <th class="text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($users_list as $u): ?>
                            <tr>
                                <td><span class="text-muted fw-bold">#<?= $u['id'] ?></span></td>
                                <td class="fw-semibold">
                                    <i class="bi bi-person-circle me-1 text-secondary"></i>
                                    <?= htmlspecialchars($u['username']) ?>
                                </td>
                                <td class="small"><?= htmlspecialchars($u['email']) ?></td>
                                <td>
                                    <?php if ($u['role'] === 'admin'): ?>
                                        <span class="badge badge-role-admin px-2 py-1"><i class="bi bi-shield-fill me-1"></i>Admin</span>
                                    <?php elseif ($u['role'] === 'editor'): ?>
                                        <span class="badge badge-role-editor px-2 py-1"><i class="bi bi-pen-fill me-1"></i>Editor</span>
                                    <?php else: ?>
                                        <span class="badge badge-role-student px-2 py-1"><i class="bi bi-person-fill me-1"></i>Student</span>
                                    <?php endif; ?>
                                </td>
                                <td class="small text-muted"><?= htmlspecialchars($u['last_login'] ?? 'Never') ?></td>
                                <td class="small text-muted"><?= htmlspecialchars($u['created_at']) ?></td>
                                <td class="text-center">
                                    <?php if ($u['id'] != $_SESSION["user_id"]): ?>
                                        <form method="post" action="admin_dashboard.php?tab=users" class="d-inline" onsubmit="<?= confirm_js('Delete user ' . $u['username'] . '?') ?>"><?= csrf_field() ?><input type="hidden" name="action" value="delete_user"><input type="hidden" name="id" value="<?= (int) $u['id'] ?>"><button type="submit" class="btn btn-outline-danger btn-sm py-0 px-2"><i class="bi bi-trash"></i> Delete</button></form>
                                    <?php else: ?>
                                        <span class="badge bg-secondary-subtle text-secondary">Current Session</span>
                                    <?php endif; ?>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 5. AUDIT LOGS TAB (Practical 14) -->
        <div class="tab-pane fade <?= ($current_tab === 'audits') ? 'show active' : '' ?>" id="audits" role="tabpanel">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
                <div>
                    <h5 class="fw-bold mb-1">Live Security & Operational Audit Trail</h5>
                    <p class="text-muted small mb-0">Tamper-evident system logs recording logins, CRUD events, exports, and 403 blocks.</p>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover table-bordered align-middle">
                    <thead class="">
                        <tr>
                            <th>#ID</th>
                            <th>Timestamp</th>
                            <th>Username</th>
                            <th>Action Type</th>
                            <th>Details</th>
                            <th>Client IP</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($audit_list as $log): ?>
                            <tr>
                                <td><span class="text-muted fw-bold">#<?= $log['id'] ?></span></td>
                                <td class="small text-muted"><?= htmlspecialchars($log['created_at']) ?></td>
                                <td class="fw-semibold"><?= htmlspecialchars($log['username']) ?></td>
                                <td>
                                    <?php
                                    $act = $log['action'];
                                    $badge_class = "bg-primary-subtle text-primary";
                                    if (strpos($act, "LOGIN") !== false) $badge_class = "bg-info-subtle text-info";
                                    if (strpos($act, "DELETE") !== false) $badge_class = "bg-danger-subtle text-danger";
                                    if (strpos($act, "CREATE") !== false) $badge_class = "bg-success-subtle text-success";
                                    if (strpos($act, "DENIED") !== false) $badge_class = "bg-danger text-white";
                                    ?>
                                    <span class="badge <?= $badge_class ?>"><code><?= htmlspecialchars($act) ?></code></span>
                                </td>
                                <td class="small"><?= htmlspecialchars($log['details']) ?></td>
                                <td class="small text-muted"><code><?= htmlspecialchars($log['ip_address']) ?></code></td>
                                <td>
                                    <?php if ($log['status'] === 'SUCCESS'): ?>
                                        <span class="badge bg-success-subtle text-success"><i class="bi bi-check me-1"></i>SUCCESS</span>
                                    <?php else: ?>
                                        <span class="badge bg-danger-subtle text-danger"><i class="bi bi-x me-1"></i><?= htmlspecialchars($log['status']) ?></span>
                                    <?php endif; ?>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Modal: Add Campus Event -->
<div class="modal fade" id="addEventModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog">
        <form method="POST" action="admin_dashboard.php?tab=events" enctype="multipart/form-data" class="modal-content">
            <?= csrf_field() ?>
            <input type="hidden" name="action" value="add_event">
            <div class="modal-header">
                <h5 class="modal-title fw-bold"><i class="bi bi-calendar-plus text-warning me-2"></i>Publish Campus Event</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label small fw-bold">Event Title</label>
                    <input type="text" name="title" class="form-control" placeholder="e.g., National Hackathon 2026" required>
                </div>
                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <label class="form-label small fw-bold">Category</label>
                        <select name="category" class="form-select" required>
                            <option value="Technical">Technical</option>
                            <option value="Cultural">Cultural</option>
                            <option value="Sports">Sports</option>
                            <option value="Workshop">Workshop</option>
                            <option value="Seminar">Seminar</option>
                        </select>
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold">Event Date</label>
                        <input type="date" name="event_date" class="form-control" value="<?= date('Y-m-d') ?>" required>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label small fw-bold">Venue / Location</label>
                    <input type="text" name="location" class="form-control" placeholder="e.g., CSPIT Auditorium, Room 506" required>
                </div>
                <div class="mb-3">
                    <label class="form-label small fw-bold">Event Description</label>
                    <textarea name="description" class="form-control" rows="3" placeholder="Brief event description..."></textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label small fw-bold">Event Poster (Optional, Max 2MB)</label>
                    <input type="file" name="poster" class="form-control" accept="image/*">
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-warning btn-sm text-body fw-bold">Publish Event</button>
            </div>
        </form>
    </div>
</div>

<!-- Bootstrap 5 Bundle JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
