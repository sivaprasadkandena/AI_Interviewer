# AI Interviewer System

## Project Overview

The **AI Interviewer System** is an AI-powered web application that automates technical interviews. The system generates interview questions based on the **job description**, evaluates candidate answers using an AI model, and determines whether the candidate is **qualified or disqualified**.

The application also includes **user authentication, admin management, OTP-based password reset, and automated email notifications**.

---

# Key Features

### AI-Based Interview Questions

The system dynamically generates technical interview questions based on the job description provided by the candidate.

### Automated Answer Evaluation

Candidate answers are evaluated using an AI model that assigns a score between **0 and 5** based on relevance and correctness.

### Multi-Step Interview Process

Candidates answer multiple questions during the interview process.

### Automated Qualification Decision

Final results are calculated using the **average score**.

* Average Score ≥ 3 → Qualified
* Average Score < 3 → Disqualified

### Email Notifications

Candidates automatically receive an email notification with their interview result.

### User Authentication System

The platform includes:

* User registration
* Admin approval for account activation
* User login system
* Session-based authentication

### OTP-Based Password Reset

Users can reset their password through **email OTP verification**.

### Admin Dashboard

Admin users can:

* Activate or deactivate users
* Delete users
* Monitor registered users

---

# Technology Stack

Backend
Django (Python Web Framework)

AI Model
Google Gemini API

LLM Integration
LangChain

Database
SQLite

Frontend
HTML, CSS

Authentication
Django Session Authentication

Email Service
SMTP

---

# Project Structure

```id="ylhnl4"
AI_Interviewer/
│
├── AI_Interviewer/        # Django project configuration
│   ├── __pycache__/
│   ├── Include/
│   ├── Lib/
│   ├── Scripts/
│   ├── __init__.py
│   ├── asgi.py
│   ├── pyvenv.cfg
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── users/                 # Main Django app
│   ├── migrations/
│   ├── __pycache__/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
│
├── templates/             # HTML templates
│   ├── users/
│   │   ├── question.html
│   │   ├── results.html
│   │   ├── start.html
│   │   └── all_results.html
│   │
│   ├── base.html
│   ├── user_base.html
│   ├── user_homepage.html
│   ├── admin_dashboard.html
│   ├── admin_home.html
│   ├── admin_login.html
│   ├── register.html
│   ├── user_login.html
│   ├── forgot_password.html
│   ├── verify_otp.html
│   ├── reset_password.html
│   ├── index.html
│   └── home.html
│
├── static/                # Static files (CSS, JS, images)
│
├── media/                 # Uploaded files
│
├── db.sqlite3             # Database
│
├── manage.py              # Django management script
│
├── README.md              # Project documentation
│
└── req.txt                # Python dependencies
```

---

# Installation Guide

### Clone the repository

```
git clone https://github.com/Friendlysiva143/AI_Interviewer.git
```

### Navigate to the project

```
cd AI_Interviewer
```

### Create virtual environment

```
python -m venv venv
```

### Activate virtual environment

Windows

```
venv\Scripts\activate
```

Linux / Mac

```
source venv/bin/activate
```

---

### Install dependencies

```
pip install -r req.txt
```

---

### Apply database migrations

```
python manage.py migrate
```

---

### Run the server

```
python manage.py runserver
```

Open in browser:

```
http://127.0.0.1:8000/
```

---

# Interview Workflow

1. User registers on the platform.
2. Admin activates the user account.
3. User logs in to the system.
4. Candidate enters the job description.
5. The AI generates a technical interview question.
6. Candidate submits an answer.
7. AI evaluates the answer and assigns a score.
8. The process repeats for multiple questions.
9. The system calculates the average score.
10. Candidate receives Qualified or Disqualified result via email.

---

# Example AI Evaluation

Example Question

```
What is the difference between a list and a tuple in Python?
```

Example AI Evaluation Output

```
{
 "score": 4,
 "qualified": "yes"
}
```

---

# Future Improvements

* Resume parsing integration
* Voice-based interview system
* Skill extraction from job descriptions
* Adaptive interview difficulty
* Cloud deployment with Docker
* Recruiter analytics dashboard

---

# Author

Siva Prasad

---

# License

This project is created for educational and demonstration purposes.
