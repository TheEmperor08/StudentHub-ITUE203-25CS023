<?php
session_start();
header("Content-Type: application/json; charset=UTF-8");

require_once 'db.php';

// Authorization comes only from the server-side login session (Practical-10/login.php).
// Any "role" sent by the browser is ignored.
if (!isset($_SESSION['user_id'])) {
    http_response_code(401);
    echo json_encode(['status' => 'error', 'message' => 'Please log in first via Practical-10/login.php.']);
    exit();
}
$session_role = $_SESSION['role'] ?? 'student';
$role = ($session_role === 'admin') ? 'admin' : (($session_role === 'editor') ? 'editor' : 'user');

$action = $_GET['action'] ?? '';
$type   = $_GET['type'] ?? 'students'; // default to StudentHub students
$input  = json_decode(file_get_contents('php://input'), true) ?? [];

// Duplicate emails (UNIQUE constraint) become a clean JSON error instead of a PHP fatal
set_exception_handler(function ($e) {
    $duplicate = ($e instanceof PDOException && $e->getCode() === '23000');
    http_response_code($duplicate ? 409 : 500);
    echo json_encode(['status' => 'error', 'message' => $duplicate ? 'A record with that email already exists.' : 'Server error.']);
});

switch ($action) {
    // -------------------------------------------------------------
    // CURRENT SESSION IDENTITY (used by the UI to show the real role)
    // -------------------------------------------------------------
    case 'whoami':
        echo json_encode([
            'status'   => 'success',
            'username' => $_SESSION['username'] ?? '',
            'role'     => $role
        ]);
        break;

    // -------------------------------------------------------------
    // DYNAMIC MENU WITH ROLE-BASED ACCESS CONTROL (RBAC)
    // -------------------------------------------------------------
    case 'get_menu':
        $rolesAllowed = ['user'];
        if ($role === 'editor') {
            $rolesAllowed = ['user', 'editor'];
        } elseif ($role === 'admin') {
            $rolesAllowed = ['user', 'editor', 'admin'];
        }

        $placeholders = implode(',', array_fill(0, count($rolesAllowed), '?'));
        $stmt = $pdo->prepare("SELECT title, link FROM menu_items WHERE min_role IN ($placeholders)");
        $stmt->execute($rolesAllowed);

        echo json_encode([
            'status' => 'success',
            'role'   => $role,
            'data'   => $stmt->fetchAll()
        ]);
        break;

    // -------------------------------------------------------------
    // CRUD: READ ALL RECORDS (Students or Items)
    // -------------------------------------------------------------
    case 'read':
        if ($type === 'items') {
            $stmt = $pdo->query("SELECT * FROM items ORDER BY id DESC");
        } else {
            $stmt = $pdo->query("SELECT id, name, email, course, gender, status, created_at FROM students ORDER BY id DESC");
        }
        echo json_encode([
            'status' => 'success',
            'type'   => $type,
            'role'   => $role,
            'data'   => $stmt->fetchAll()
        ]);
        break;

    // -------------------------------------------------------------
    // CRUD: CREATE NEW RECORD (Role Enforced)
    // -------------------------------------------------------------
    case 'create':
        // Enforce RBAC: Students cannot create records
        if ($role === 'user') {
            http_response_code(403);
            echo json_encode([
                'status'  => 'error',
                'message' => 'Access Denied: Students do not have permission to add new records.'
            ]);
            break;
        }

        if ($type === 'items' || (isset($input['price']) && !isset($input['email']))) {
            if (!empty($input['name']) && !empty($input['category']) && isset($input['price'])) {
                $stmt = $pdo->prepare("INSERT INTO items (name, category, price) VALUES (?, ?, ?)");
                $stmt->execute([$input['name'], $input['category'], $input['price']]);
                echo json_encode(['status' => 'success', 'message' => 'Campus resource item created successfully']);
            } else {
                echo json_encode(['status' => 'error', 'message' => 'Missing required fields for item']);
            }
        } else {
            // StudentHub Student Creation
            if (!empty($input['name']) && !empty($input['email']) && !empty($input['course']) && !empty($input['gender'])) {
                $stmt = $pdo->prepare("INSERT INTO students (name, email, course, gender, status) VALUES (?, ?, ?, ?, 'Active')");
                $stmt->execute([$input['name'], $input['email'], $input['course'], $input['gender']]);
                echo json_encode(['status' => 'success', 'message' => 'Student record created successfully!']);
            } else {
                echo json_encode(['status' => 'error', 'message' => 'Missing required student fields (Name, Email, Course, Gender)']);
            }
        }
        break;

    // -------------------------------------------------------------
    // CRUD: UPDATE EXISTING RECORD (Role Enforced)
    // -------------------------------------------------------------
    case 'update':
        // Enforce RBAC: Students cannot update records
        if ($role === 'user') {
            http_response_code(403);
            echo json_encode([
                'status'  => 'error',
                'message' => 'Access Denied: Students cannot modify student records. Faculty or Admin access required.'
            ]);
            break;
        }

        if ($type === 'items' || (isset($input['price']) && !isset($input['email']))) {
            if (!empty($input['id']) && !empty($input['name']) && !empty($input['category']) && isset($input['price'])) {
                $stmt = $pdo->prepare("UPDATE items SET name = ?, category = ?, price = ? WHERE id = ?");
                $stmt->execute([$input['name'], $input['category'], $input['price'], $input['id']]);
                echo json_encode(['status' => 'success', 'message' => 'Item updated successfully']);
            } else {
                echo json_encode(['status' => 'error', 'message' => 'Invalid or missing data for update']);
            }
        } else {
            // StudentHub Student Update
            if (!empty($input['id']) && !empty($input['name']) && !empty($input['email']) && !empty($input['course']) && !empty($input['gender'])) {
                $stmt = $pdo->prepare("UPDATE students SET name = ?, email = ?, course = ?, gender = ? WHERE id = ?");
                $stmt->execute([$input['name'], $input['email'], $input['course'], $input['gender'], $input['id']]);
                echo json_encode(['status' => 'success', 'message' => 'Student record updated successfully!']);
            } else {
                echo json_encode(['status' => 'error', 'message' => 'Invalid or missing data for student update']);
            }
        }
        break;

    // -------------------------------------------------------------
    // CRUD: DELETE RECORD (Role Enforced: Only Admin can delete)
    // -------------------------------------------------------------
    case 'delete':
        // Enforce RBAC: Only Admin can delete records
        if ($role !== 'admin') {
            http_response_code(403);
            echo json_encode([
                'status'  => 'error',
                'message' => 'Access Denied: Only Administrators can permanently delete student records.'
            ]);
            break;
        }

        if (!empty($input['id'])) {
            if ($type === 'items') {
                $stmt = $pdo->prepare("DELETE FROM items WHERE id = ?");
            } else {
                $stmt = $pdo->prepare("DELETE FROM students WHERE id = ?");
            }
            $stmt->execute([$input['id']]);
            echo json_encode([
                'status'  => 'success',
                'message' => ($type === 'items' ? 'Item' : 'Student record') . ' deleted successfully!'
            ]);
        } else {
            echo json_encode(['status' => 'error', 'message' => 'Record ID is required for deletion']);
        }
        break;

    default:
        echo json_encode(['status' => 'error', 'message' => 'Invalid action']);
        break;
}
