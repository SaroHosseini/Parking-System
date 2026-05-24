# Parking Management System

A Django-based parking management system designed for managing public parking lots. This project is currently focused on the core backend structure, Django models, business logic, and Django Admin panel.

## Project Overview

This system helps manage parking operations such as vehicle registration, parking spot management, entry and exit tracking, tariff calculation, payment handling, and receipt generation.

The project is being developed step by step, starting with the core management package. In the future, it can be extended into a complete website where customers can view, purchase, and access the parking management package.

## Features Implemented So Far

- Vehicle registration
- Support for cars, motorcycles, and trucks
- Persian car plate validation
- Motorcycle plate validation
- Parking lot management
- Parking spot management
- Spot occupation tracking
- Tariff management
- First-hour pricing
- Additional-hour pricing
- Daily parking pricing
- Parking session management
- Entry and exit time tracking
- Automatic duration calculation
- Automatic parking fee calculation
- Prevention of multiple open sessions for the same vehicle
- Automatic payment creation after session exit
- Payment status management
- Receipt generation after successful payment
- Unique receipt number generation
- Receipt content generation
- Delete history tracking for sessions, payments, and receipts
- Django signals for saving deleted records into history tables
- Customized Django Admin panel
- Admin filters, search fields, pagination, and editable fields
- Admin display customization for plate numbers and receipt previews
- Admin site header and index title customization
- Inline parking spot management inside parking lots
- Parking session admin filters and search
- Payment admin filters, search, and read-only fields
- Receipt admin filters, search, read-only fields, and preview display
- History models registered in the Django Admin panel

## Main Models

### Vehicle

Stores vehicle information such as plate number, owner name, owner phone, vehicle type, and color.

### ParkingLot

Stores parking lot information such as name and total capacity.

### ParkingSpot

Stores parking spot information including parking lot, spot code, level, and occupation status.

### Tariff

Stores pricing rules based on vehicle type, including first-hour price, additional-hour price, and daily price.

### ParkingSession

Stores vehicle parking sessions, including entry time, exit time, duration, status, selected spot, and calculated fee.

### Payment

Stores payment information for parking sessions, including amount, payment method, payment status, and payment time.

### Receipt

Stores generated receipt information, including receipt number, issue time, calculated fee, related session, related payment, and receipt content.

### History Models

The project includes history models for deleted parking sessions, payments, and receipts:

- ParkingSessionHistory
- PaymentHistory
- ReceiptHistory

These models keep important deleted data for tracking and audit purposes.

## Admin Panel

The Django Admin panel has been customized and completed for the current development phase.

Current admin improvements include:

- Custom list displays for all main models
- Search fields for vehicles, parking spots, sessions, payments, and receipts
- Filters for vehicle type, spot status, session status, payment status, and receipt information
- Pagination for large admin lists
- Editable tariff and payment fields where appropriate
- Read-only calculated fields such as duration, calculated fee, payment amount, receipt number, and receipt content
- Inline parking spot management inside parking lots
- Formatted Persian plate display
- Vehicle preview display inside parking sessions
- Receipt preview display
- History model registration for deleted sessions, payments, and receipts
- Custom admin site header and index title

## Business Logic

The system includes several automatic business rules:

- A parking spot becomes occupied when a new parking session is created.
- A parking spot becomes free when the vehicle exits.
- A vehicle cannot have more than one open parking session at the same time.
- Duration is calculated automatically after exit.
- Parking fee is calculated automatically based on tariff rules.
- A payment record is created automatically when a session is closed.
- A receipt is created only after the payment is completed.
- Deleted sessions, payments, and receipts are stored in history tables.

## Technologies Used

- Python
- Django
- PostgreSQL
- Django Admin
- Django Signals
- python-decouple

## Current Development Status

The project currently includes the main backend models, core business logic, delete history tracking, and a customized Django Admin panel.

The Django Admin panel is completed for the current development phase and can be used to manage vehicles, parking lots, parking spots, tariffs, parking sessions, payments, receipts, and deleted-record history.

The next development steps are:

- Adding dashboard views
- Adding basic Django views and templates
- Adding reports
- Preparing the system for real-world usage
- Later adding REST API support
- Later building a website for selling and accessing the parking management package

## Future Plans

Planned future features include:

- Operator shift management
- Daily, weekly, and monthly reports
- Revenue reports
- Entry and exit reports
- Parking occupancy reports
- Operator performance reports
- Customer-facing website
- Login and registration system
- Package purchase system
- Payment gateway integration
- REST API using Django REST Framework
- Deployment on a real server

## Setup

### 1. Clone the project

    git clone <repository-url>
    cd Parking_System

### 2. Create and activate a virtual environment

    python -m venv .venv
    .venv\Scripts\activate

### 3. Install dependencies

    pip install -r requirements.txt

### 4. Create a .env file

Create a file named .env in the project root and add the following variables:

    SECRET_KEY=your-secret-key
    DB_NAME=your-database-name
    DB_HOST=127.0.0.1
    DB_PORT=5432
    DB_USER=postgres
    DB_PASSWORD=your-database-password

### 5. Run migrations

    python manage.py makemigrations
    python manage.py migrate

### 6. Create a superuser

    python manage.py createsuperuser

### 7. Run the development server

    python manage.py runserver

### 8. Open the admin panel

    http://127.0.0.1:8000/admin/

## Author

- Group Members: SaroHosseini, Ali Azarang, Mani Lotfolahnasabi
- Course: Software Engineering
- Project: Parking System