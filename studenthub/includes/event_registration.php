<?php
// StudentHub - Practical 8 foundation: registering a student for an event without overbooking.
//
// The registrations table (database/migrations/001_practical8_foundation.sql) stops duplicate registrations with
// UNIQUE (student_id, event_id). The capacity rule is enforced here, inside one transaction:
//   1. SELECT ... FOR UPDATE locks the event row, so concurrent registrations for the same event wait for each other;
//   2. the seats taken (registrations that are not 'cancelled') are counted only after the lock is held;
//   3. the registration is inserted - or a cancelled one reactivated - and the transaction commits.
// events.capacity NULL means "no limit set" (existing events have no capacity). Inactive students cannot register.
//
// Not used by any page yet: the registration interface is built with the event module in a later practical.
// Requires mysqli in exception mode (the PHP 8.1+ default).

class EventRegistrationException extends RuntimeException
{
    public const EVENT_NOT_FOUND   = 'event_not_found';
    public const STUDENT_NOT_FOUND = 'student_not_found';
    public const STUDENT_INACTIVE  = 'student_inactive';
    public const DUPLICATE         = 'duplicate';
    public const EVENT_FULL        = 'event_full';

    private const MESSAGES = [
        self::EVENT_NOT_FOUND   => 'The event does not exist.',
        self::STUDENT_NOT_FOUND => 'The student record does not exist.',
        self::STUDENT_INACTIVE  => 'Inactive students cannot register for events.',
        self::DUPLICATE         => 'The student is already registered for this event.',
        self::EVENT_FULL        => 'The event is full.',
    ];

    public function __construct(public string $reason)
    {
        parent::__construct(self::MESSAGES[$reason] ?? 'Registration failed.');
    }
}

// Registers the student for the event and returns the registration_id.
// Throws EventRegistrationException with one of the reasons above; other database errors are re-thrown unchanged.
function register_student_for_event(mysqli $db, int $student_id, int $event_id): int
{
    $db->begin_transaction();
    try {
        $stmt = $db->prepare('SELECT capacity FROM events WHERE id = ? FOR UPDATE');
        $stmt->bind_param('i', $event_id);
        $stmt->execute();
        $event = $stmt->get_result()->fetch_assoc();
        if ($event === null) {
            throw new EventRegistrationException(EventRegistrationException::EVENT_NOT_FOUND);
        }

        $stmt = $db->prepare('SELECT status FROM students WHERE id = ? LOCK IN SHARE MODE');
        $stmt->bind_param('i', $student_id);
        $stmt->execute();
        $student = $stmt->get_result()->fetch_assoc();
        if ($student === null) {
            throw new EventRegistrationException(EventRegistrationException::STUDENT_NOT_FOUND);
        }
        if (strcasecmp(trim((string) $student['status']), 'Inactive') === 0) {
            throw new EventRegistrationException(EventRegistrationException::STUDENT_INACTIVE);
        }

        $stmt = $db->prepare('SELECT registration_id, status FROM registrations WHERE student_id = ? AND event_id = ? FOR UPDATE');
        $stmt->bind_param('ii', $student_id, $event_id);
        $stmt->execute();
        $existing = $stmt->get_result()->fetch_assoc();
        if ($existing !== null && $existing['status'] !== 'cancelled') {
            throw new EventRegistrationException(EventRegistrationException::DUPLICATE);
        }

        if ($event['capacity'] !== null) {
            // locking read: always counts the latest committed rows
            $stmt = $db->prepare("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status <> 'cancelled' LOCK IN SHARE MODE");
            $stmt->bind_param('i', $event_id);
            $stmt->execute();
            if ((int) $stmt->get_result()->fetch_row()[0] >= (int) $event['capacity']) {
                throw new EventRegistrationException(EventRegistrationException::EVENT_FULL);
            }
        }

        if ($existing !== null) {                                   // a cancelled registration is reactivated
            $registration_id = (int) $existing['registration_id'];
            $stmt = $db->prepare("UPDATE registrations SET status = 'registered', registered_at = NOW() WHERE registration_id = ?");
            $stmt->bind_param('i', $registration_id);
            $stmt->execute();
        } else {
            $stmt = $db->prepare('INSERT INTO registrations (student_id, event_id) VALUES (?, ?)');
            $stmt->bind_param('ii', $student_id, $event_id);
            $stmt->execute();
            $registration_id = (int) $stmt->insert_id;
        }
        $db->commit();
        return $registration_id;
    } catch (EventRegistrationException $e) {
        $db->rollback();
        throw $e;
    } catch (mysqli_sql_exception $e) {
        $db->rollback();
        if ($e->getCode() === 1062) {                               // UNIQUE (student_id, event_id): registered meanwhile
            throw new EventRegistrationException(EventRegistrationException::DUPLICATE);
        }
        throw $e;
    }
}

// Seats taken (registrations that are not cancelled) for one event
function event_seats_taken(mysqli $db, int $event_id): int
{
    $stmt = $db->prepare("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status <> 'cancelled'");
    $stmt->bind_param('i', $event_id);
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0];
}
