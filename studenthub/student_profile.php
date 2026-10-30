<?php
// Shared student profile helper: the academic record linked to the logged-in account.
// The record is found through students.user_id (migration 001 – Practical 8) – never by guessing from the e-mail
// address. An account without a linked record (admins, editors, accounts created before the link existed) sees its own
// username and no enrollment number; nobody is shown another person's details. Guests get an empty profile.

function get_student_profile($conn) {
    $user_id = (int) ($_SESSION["user_id"] ?? 0);

    $profile = [
        "name"          => (string) ($_SESSION["username"] ?? ""),
        "enrollment_no" => "—",
        "email"         => (string) ($_SESSION["email"] ?? ""),
        "course"        => "",
        "semester"      => 3,          // display default for the sample academic pages
        "gender"        => "",
        "linked"        => false,
    ];

    if (!$conn || $user_id <= 0) {
        return $profile;
    }

    $stmt = $conn->prepare("SELECT enrollment_no, name, email, course, semester, gender FROM students WHERE user_id = ? LIMIT 1");
    if ($stmt) {
        $stmt->bind_param("i", $user_id);
        $stmt->execute();
        $row = $stmt->get_result()->fetch_assoc();
        if ($row) {
            $profile["name"]          = $row["name"] ?: $profile["name"];
            $profile["enrollment_no"] = $row["enrollment_no"] ?: "—";
            $profile["email"]         = $row["email"];
            $profile["course"]        = $row["course"] ?? "";
            $profile["semester"]      = (int) ($row["semester"] ?: 3);
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
