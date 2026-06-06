# Parking Management System

A Django-based parking management system designed for managing parking businesses and public parking lots.  
The project is being developed step by step as a real product: first the core parking management application, then customer registration and access control, then frontend UI, then a public homepage for product introduction and registration, and finally deployment on a VPS with a real domain.

## Project Overview

Parkino is a parking management system that helps manage vehicles, parking lots, parking spots, parking sessions, tariffs, payments, receipts, and customer access.

The current focus is on completing the main product that customers will use after login. The system now supports a customer-based structure, meaning each customer can have their own parking lots, vehicles, tariffs, sessions, payments, and receipts.

In the future, the project will include a complete frontend design, a product homepage, registration flow, and deployment on the purchased VPS and domain.

## Product Direction

The final product plan is:

1. Complete the main parking management product
2. Complete customer registration, approval, login, and access control
3. Apply a modern frontend theme to the product dashboard and internal pages
4. Build a public homepage for introducing the product
5. Add registration and login links to the homepage
6. Deploy the project on a VPS
7. Connect the project to the domain `parkino.shop`

## Features Implemented So Far

### Core Parking Management

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

### Customer-Based Multi-Tenant Structure

- Customer model added
- Customer approval status: pending, approved, rejected
- Customer activation handling
- CustomerUser model added
- Customer users can have roles such as owner, admin, and operator
- Each customer can have multiple parking lots
- Vehicles are linked to a customer
- Parking lots are linked to a customer
- Tariffs are linked to a customer
- Parking spots are connected to a customer through their parking lot
- Parking sessions are validated so the selected vehicle and parking spot belong to the same customer
- Tariffs are calculated based on the vehicle type and the related customer
- Customer-based filtering added for dashboard data

### Customer Registration and Access Flow

- Public homepage added
- Customer request form added
- Customer can submit parking business information
- Customer can choose username and password during request registration
- User account is created automatically but remains inactive until approval
- CustomerUser record is created automatically and linked to the customer
- Customer request status page added
- Login page added
- Logout flow added
- Customer user becomes active after the customer is approved in the admin panel
- Dashboard access is protected
- Unauthenticated users are redirected to login
- Approved customer users can access their own dashboard
- Superuser can view overall system data

### Request Form Validation

- Username must be unique
- Username must use English letters, numbers, or underscore
- Email must be unique
- Phone number must be unique
- Phone number must be numeric
- Phone number must be 11 digits
- Password must be at least 8 characters
- Password must include at least one uppercase English letter
- Password must include at least one number
- Password and password confirmation must match

### Dashboard and Product Pages

- Basic dashboard view added
- Dashboard shows total spots, available spots, occupied spots, open sessions, closed sessions, and today income
- Active sessions table added to dashboard
- Dashboard data is filtered by the logged-in customer
- Base dashboard template added for internal product pages
- Vehicle management views added
- Vehicle list page added
- Vehicle create page added
- Vehicle edit page added
- Vehicle pages only show and manage vehicles for the logged-in customer

### History and Signals

- Delete history tracking for sessions, payments, and receipts
- Django signals for saving deleted records into history tables
- Customer tracking added to delete history records
- Parking spot is freed when an active session is deleted
- History models registered in Django Admin

### Django Admin Panel

- Customized Django Admin panel
- Admin filters, search fields, pagination, and editable fields
- Admin display customization for plate numbers and receipt previews
- Admin site header and index title customization
- Inline parking spot management inside parking lots
- Parking session admin filters and search
- Payment admin filters, search, and read-only fields
- Receipt admin filters, search, read-only fields, and preview display
- History models registered in the Django Admin panel
- Customer and CustomerUser registered in admin
- Customer status can be edited from the admin list
- Admin panel updated for customer-based data management

## Main Models

### Customer

Stores customer or parking business information such as parking name, owner name, phone, email, address, request status, activation status, request creation time, and approval time.

### CustomerUser

Connects Django users to a customer and defines their role inside that customer account.

Roles include:

- Owner
- Admin
- Operator

### Vehicle

Stores vehicle information such as plate number, owner name, owner phone, vehicle type, color, and related customer.

### ParkingLot

Stores parking lot information such as name, total capacity, and related customer.  
Each customer can have multiple parking lots.

### ParkingSpot

Stores parking spot information including parking lot, spot code, level, and occupation status.

### Tariff

Stores pricing rules based on customer and vehicle type, including first-hour price, additional-hour price, daily price, and active status.

### ParkingSession

Stores vehicle parking sessions, including entry time, exit time, duration, status, selected spot, selected vehicle, and calculated fee.

### Payment

Stores payment information for parking sessions, including amount, payment method, payment status, payment time, and related parking session.

### Receipt

Stores generated receipt information, including receipt number, issue time, calculated fee, related session, related payment, and receipt content.

### History Models

The project includes history models for deleted parking sessions, payments, and receipts:

- ParkingSessionHistory
- PaymentHistory
- ReceiptHistory

These models keep important deleted data for tracking and audit purposes.

## Current URL Structure

Current main routes include:

- `/` — Public homepage
- `/request/` — Customer request registration form
- `/request/status/` — Customer request status page
- `/login/` — Login page
- `/logout/` — Logout route
- `/dashboard/` — Customer dashboard
- `/vehicles/` — Vehicle list
- `/vehicles/add/` — Add vehicle
- `/vehicles/<id>/edit/` — Edit vehicle
- `/admin/` — Django admin panel

## Admin Panel

The Django Admin panel has been customized for the current development phase.

Current admin improvements include:

- Custom list displays for all main models
- Search fields for vehicles, parking spots, sessions, payments, receipts, customers, and customer users
- Filters for customer, vehicle type, spot status, session status, payment status, and receipt information
- Pagination for large admin lists
- Editable tariff and payment fields where appropriate
- Editable customer status in customer admin list
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
- A parking spot becomes free when an active parking session is deleted.
- A vehicle cannot have more than one open parking session at the same time.
- A parking session must use a vehicle and spot belonging to the same customer.
- Duration is calculated automatically after exit.
- Parking fee is calculated automatically based on the active tariff for that customer and vehicle type.
- A payment record is created automatically when a session is closed.
- A receipt is created only after the payment is completed.
- Deleted sessions, payments, and receipts are stored in history tables.
- Customer request creates an inactive user account.
- Customer approval activates related user accounts.

## Technologies Used

- Python
- Django
- PostgreSQL
- Django Admin
- Django Signals
- Django Authentication
- Django Templates
- python-decouple

## Current Development Status

The project currently includes:

- Main backend models
- Core business logic
- Customer-based multi-tenant structure
- Customer request registration flow
- User creation and approval-based activation
- Login and logout flow
- Customer-aware dashboard
- Base dashboard template
- Vehicle management pages
- Delete history tracking
- Customized Django Admin panel

The project is currently focused on completing the internal product pages that customers will use after login.

## Next Development Steps

Next planned steps:

- Complete internal product pages based on the Navigation Design
- Parking lot list, create, and edit pages
- Parking spot list, create, and edit pages
- Tariff list, create, and edit pages
- Parking session pages
- Record vehicle entry
- Record vehicle exit
- Payment list and detail pages
- Receipt list and detail pages
- Basic reports
- User and role management pages
- Apply final frontend theme to internal product pages
- Build public homepage with final frontend design
- Prepare deployment on VPS
- Connect the project to `parkino.shop`

## Future Plans

Planned future features include:

- Operator shift management
- Daily, weekly, and monthly reports
- Revenue reports
- Entry and exit reports
- Parking occupancy reports
- Operator performance reports
- Customer-facing product homepage
- Package purchase system
- Payment gateway integration
- REST API using Django REST Framework
- Deployment on VPS
- Domain connection
- SSL setup
- Production database setup
- Backup system

## Deployment Plan

The project has a purchased VPS and domain for future deployment:

- VPS: irVPS3 Linux
- Domain: parkino.shop

Deployment is not active yet. It will be handled after the main product and frontend are completed.

## Setup

### 1. Clone the project

```bash
git clone <repository-url>
cd Parking_System
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a .env file

Create a file named `.env` in the project root and add the following variables:

```env
SECRET_KEY=your-secret-key
DB_NAME=your-database-name
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-database-password
```

### 5. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

### 8. Open the project

```text
http://127.0.0.1:8000/
```

### 9. Open the admin panel

```text
http://127.0.0.1:8000/admin/
```

## Basic Usage Flow

1. A customer opens the homepage.
2. The customer submits a request using the registration form.
3. The system creates a Customer, inactive User, and CustomerUser.
4. The admin reviews the request in Django Admin.
5. The admin changes the customer status to approved.
6. The related user account becomes active.
7. The customer logs in using the selected username and password.
8. The customer accesses the dashboard.
9. The customer can manage their own vehicles and later other parking data.
10. Each customer only sees data related to their own account.

## Author

- Group Members: SaroHosseini, Ali Azarang, Mani Lotfolahnasabi
- Course: Software Engineering
- Project: Parking System
