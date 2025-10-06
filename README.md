College Event Management System (CEMS)
A full-featured College Event Management System (CEMS) built with Django. This application manages the entire event lifecycle from creation and HOD approval to participant registration with QR code tickets, check-ins, and feedback.

Key Features
User Roles:

Participant: Can browse approved events, register for them, and provide feedback.

Organizer: Can create, edit, and delete their own events, which are then submitted for approval. They can also view participants and access an analytics dashboard.

Head of Department (HOD): A staff user who can approve or reject events submitted by Organizers.

Approval Workflow: Events require HOD approval before they are visible to participants. Organizers are notified of the status via email.

QR Code Ticketing: For in-person events, a unique QR code is generated and emailed to the participant as a PDF ticket upon registration.

Web-Based Check-in: Organizers can use a built-in QR code scanner on the website to validate tickets and check in attendees.

Automated Emails: The system sends automated emails for registration confirmations, event status updates, and feedback requests after an event.

Feedback & Analytics: Participants can leave a star rating and comments. Organizers can view an analytics dashboard with average ratings and recent comments.

Scheduled Tasks: A background scheduler automatically marks events as "Completed" and sends out feedback requests.

Tech Stack
Backend: Django, Python

Database: SQLite 3 (for development)

Frontend: HTML, Tailwind CSS, JavaScript

Key Libraries:

django-apscheduler for scheduled tasks.

qrcode[pil] for generating QR codes.

xhtml2pdf for creating PDF tickets.

python-decouple for managing environment variables.

Getting Started
Prerequisites
Python 3.x

pip (Python package installer)

Git

Installation & Setup
Clone the Repository:

git clone <your-repo-url>
cd CollegeEventSystem

Create and Activate a Virtual Environment:

# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

Install Dependencies:

pip install -r requirements.txt

Configure Environment Variables:

Rename the .env.example file to .env.

Fill in the required values, especially EMAIL_HOST_USER and EMAIL_HOST_PASSWORD.

Run Database Migrations:

python manage.py migrate

Create a Superuser (HOD):

python manage.py createsuperuser

This user will have HOD privileges in the admin panel.

Run the Development Server:

python manage.py runserver

The application will be available at http://127.0.0.1:8000/.

Project Structure
CollegeEventSystem/
├── cems_project/         # Main Django project configuration
├── events/               # The core application for event management
├── media/                # For user-uploaded files (QR codes)
├── .env                  # Environment variables
├── manage.py
└── requirements.txt
