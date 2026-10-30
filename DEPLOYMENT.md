# StudentHub – deployment notes

These notes describe how to put the integrated portal (`studenthub/`) on an Apache + PHP + MariaDB server (for example
XAMPP on a lab machine or a Linux VPS). They were written for this project; the production steps below were **not**
carried out on a real public server as part of the coursework – the application was tested with PHP's built-in server.

## 1. Server
- PHP 8.1+ with `mysqli`, `fileinfo`, `mbstring`; MariaDB 10.4+ or MySQL 8.
- Apache with `mod_rewrite` optional; `AllowOverride All` (or the equivalent rules in the virtual host) so that
  `studenthub/uploads/.htaccess` takes effect: it denies HTTP access to the poster folder and switches PHP off there.
- **HTTPS** (e.g. Let's Encrypt). The session cookie is marked `Secure` automatically when the request is HTTPS.

## 2. Files
- Make `studenthub/` the document root of the virtual host (the other folders – `database/`, `tests/`, `tools/`,
  `Practical-*`, `evidence/` – must **not** be served).
- The web server user needs write access only to the poster folder (`studenthub/uploads/` or `STUDENTHUB_UPLOAD_DIR`);
  ideally place that folder outside the document root and set `STUDENTHUB_UPLOAD_DIR` to it.
- `display_errors = Off`, `log_errors = On` in `php.ini` (the portal also sets these at run time); keep the PHP error log
  outside the document root – the portal writes database and API errors there, never to visitors.

## 3. Database
- Create a dedicated database user with only `SELECT, INSERT, UPDATE, DELETE` on `studenthub_db` for the application, and
  run the schema / migrations with an administrative account:
  ```sql
  CREATE USER 'studenthub'@'localhost' IDENTIFIED BY '<strong password>';
  GRANT SELECT, INSERT, UPDATE, DELETE ON studenthub_db.* TO 'studenthub'@'localhost';
  ```
- New installation: `database/studenthub_demo.sql` (or the schema part of it without the demo rows). Existing database:
  apply the missing migrations `database/migrations/001_…` – `005_…` in order, after a `mysqldump` backup.
- Set the connection through environment variables in the virtual host (`SetEnv DB_HOST …`, `DB_USER`, `DB_PASS`,
  `DB_NAME`, `STUDENTHUB_TIMEZONE`, `STUDENTHUB_SESSION_TIMEOUT`, `STUDENTHUB_UPLOAD_DIR`) – never in a file inside the
  document root.

## 4. Accounts
- Create the first administrator on the server with `php tools/create_demo_user.php --db=studenthub_db --username=… --email=… --role=admin`
  (the password is prompted, stored only as a bcrypt hash). Do not create demo accounts on a public server.

## 5. Operation
- Back up `studenthub_db` regularly with `mysqldump --single-transaction` and keep the dumps outside the web root
  (they contain password hashes and personal data). Back up the poster folder as well.
- Review the Admin Console audit log (security blocks, refused sign-ins, rejected uploads) and the PHP error log.
- Before an update: back up, apply new migrations, run `python tests/run_all.py` against a copy, then deploy the files.

## 6. Known limitations relevant to deployment
- No rate limiting of sign-in attempts (put the site behind a reverse proxy / fail2ban rule if it is public).
- The Admin Console loads Bootstrap from a CDN; host it locally if the CDN must not be used.
- No e-mail is sent (inquiry answers and password resets are not implemented).
