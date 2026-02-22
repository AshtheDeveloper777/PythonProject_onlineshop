🛒 Flask E-Commerce Web Application

A full-stack E-Commerce web application built using Flask, SQLAlchemy, Flask-Login, Razorpay, and Supabase Storage.

This project includes:

User authentication (Register/Login/Logout)

Product listing & filtering

Shopping cart system

Order management

Razorpay payment integration

Mock payment option

File upload to Supabase Storage

SQLite (default) or external database support

🚀 Features
👤 User Authentication

Secure password hashing

Login & session management using Flask-Login

Protected routes with @login_required

🛍️ Product Management

Product listing

Category filtering

Search functionality

Product detail page

🛒 Cart System

Add to cart

Update quantity

Remove items

Real-time total calculation

💳 Payments

Razorpay integration (INR supported)

Signature verification for secure payment confirmation

Mock payment fallback

📦 Orders

Order creation from cart

Order history

Order detail page

Payment status tracking

☁ File Upload

Upload files to Supabase Storage bucket

Returns public URL

🛠️ Tech Stack

Backend: Flask

Database: SQLite (default) / PostgreSQL via DATABASE_URL

ORM: SQLAlchemy

Authentication: Flask-Login

Payments: Razorpay

Storage: Supabase

Security: Werkzeug password hashing