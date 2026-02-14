# NovaMart — Flask E-Commerce (Personal Project)

A full-stack mini e-commerce application built with Flask + SQLAlchemy.

## Features
- User authentication (Register/Login/Logout) using Flask-Login
- Product catalog with search + product details page
- Session-based cart (add/remove)
- Checkout flow with demo (fake) payment
- Order creation + order history
- Stock validation and stock deduction after purchase

## Tech Stack
- Python, Flask
- SQLAlchemy (SQLite)
- Jinja2 Templates (Frontend)
- Session-based cart

## How to Run Locally
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
pip install -r requirements.txt
python app.py
