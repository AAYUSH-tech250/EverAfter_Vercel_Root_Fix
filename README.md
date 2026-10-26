# EverAfter Wedding Planner (Django)

## Features
- Multi-page wedding planner with clear text-labelled navigation and buttons.
- Owner, Guest, and Attendance Viewer registration.
- Owner account creates its own wedding; wedding records are scoped to that owner.
- Unique wedding invitation code, shown in Wedding Details.
- Guests join by code and can RSVP, choose functions, state attendee count, and provide travel/arrival details.
- Attendance Viewer joins with the same code and sees only guest/family name, RSVP status, function attendance and confirmed people—not contact, travel, or private notes.
- Invitation image or PDF upload in Wedding Details.
- Per-function attendance summary and guest list.
- Persistent Django login session: 14 days, does not expire just because the browser closes. Explicit logout ends it.
- SQLite local database; media uploaded under `media/`.

## Run locally (Windows)
1. Install Python 3.11+.
2. Extract this ZIP and open a terminal in the `wedding_planner` folder.
3. Create/activate a virtual environment:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
5. Apply database migrations (includes the included migration):
   ```bat
   python manage.py migrate
   ```
   If you change models in development, run `python manage.py makemigrations` then `python manage.py migrate`.
6. Run the site:
   ```bat
   python manage.py runserver
   ```
7. Visit http://127.0.0.1:8000/ and create an Owner account first.
8. Owner opens Wedding Details and shares the displayed wedding invitation code.
9. Guests choose Guest during signup and enter that code. Rahul (or another attendance-only user) chooses Attendance Viewer and enters the same code.

## Important
This is a development project. Before public deployment, set a strong secret key via environment variables, `DEBUG=False`, allowed hosts, HTTPS, secure file upload validation, production database, backups and access review. The app has not been run in this environment because Django could not be installed here; run the commands above locally and report any traceback for further fixes.
