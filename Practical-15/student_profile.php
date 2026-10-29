<?php
// Shared Student Profile Helper: resolves the logged-in student's academic record
// Looks up the students table by session email; falls back to the portal owner's details

const DEFAULT_STUDENT_NAME  = "Shreyas";
const DEFAULT_ENROLLMENT_NO = "25CS023";
const DEFAULT_STUDENT_EMAIL = "25cs023@charusat.edu.in";

function get_student_profile($conn) {
    $session_email = $_SESSION["email"] ?? "";

    $profile = [
        "name"          => DEFAULT_STUDENT_NAME,
        "enrollment_no" => DEFAULT_ENROLLMENT_NO,
        "email"         => $session_email ?: DEFAULT_STUDENT_EMAIL,
        "course"        => "",
        "semester"      => 3,
        "gender"        => "",
        "linked"        => false,
    ];

    if (!$conn || $session_email === "") {
        return $profile;
    }

    $stmt = $conn->prepare("SELECT enrollment_no, name, email, course, semester, gender FROM students WHERE email = ? LIMIT 1");
    if ($stmt) {
        $stmt->bind_param("s", $session_email);
        $stmt->execute();
        $row = $stmt->get_result()->fetch_assoc();
        if ($row) {
            // Linked record: never borrow the owner's roll number for another student
            $profile["name"]          = $row["name"] ?: $profile["name"];
            $profile["enrollment_no"] = $row["enrollment_no"] ?: "—";
            $profile["email"]         = $row["email"];
            $profile["course"]        = $row["course"] ?? "";
            $profile["semester"]      = (int)($row["semester"] ?: 3);
            $profile["gender"]        = $row["gender"] ?? "";
            $profile["linked"]        = true;
        }
        $stmt->close();
    }

    return $profile;
}

// Formats 1 → "1st", 2 → "2nd", 3 → "3rd", 5 → "5th", 11 → "11th"
function ordinal_suffix($number) {
    $number = (int)$number;
    if (in_array($number % 100, [11, 12, 13], true)) {
        return $number . "th";
    }
    switch ($number % 10) {
        case 1:  return $number . "st";
        case 2:  return $number . "nd";
        case 3:  return $number . "rd";
        default: return $number . "th";
    }
}
?>
