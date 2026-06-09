# Parkino Parking Management System

Parkino is a Django-based parking management system for daily parking operations: vehicle entry, parking spot control, exit registration, payment management, receipt printing, reports, users, roles, and parking settings.

The project is deployed as a demo/product preview on:

```text
https://parkino.shop
www.parkino.shop
```

The deployed site is expected to run behind SSL and CDN. The intended request path is:

```text
Visitor Browser → HTTPS → CDN Proxy → HTTPS → VPS Origin (Nginx) → Gunicorn → Django App
```

## Current Status

- Public homepage is available.
- Public request form is available.
- Login and customer dashboard are available.
- Customer-based data isolation is implemented.
- Owner and operator roles are supported.
- Operators can be limited to a specific parking lot.
- Parking lots, spots, tariffs, sessions, payments, receipts, reports, users, and settings are implemented.
- Automatic parking spot generation is implemented with per-floor customization for cars and motorcycles.
- Persian Jalali date filters are used in the dashboard filters.
- Receipt print page has frontend styling.
- Bug report modal is available inside the dashboard.
- Simple SEO support is added for public pages.
- Custom 404 page is added with the public site theme.
- `robots.txt` and `sitemap.xml` are available.

## Main Features

### Public Website

- Product homepage
- Login entry point
- Customer request form
- Contact information
- Dark and light mode
- Simple SEO meta tags
- Open Graph and Twitter card tags
- Custom 404 page
- Sitemap and robots routes

### Dashboard

- Customer dashboard summary
- Parking capacity overview
- Active sessions
- Pending payments
- Recent receipts
- Daily operation cards
- Bug report modal
- Dark and light mode

### Parking Operations

- Vehicle entry registration
- Vehicle exit registration
- Free spot selection
- Spot search and pagination
- Automatic fee calculation
- Automatic payment creation
- Receipt generation
- Receipt print view

### Parking Infrastructure

- Parking lot management
- Parking spot management
- Floor count support
- Automatic spot generation per floor
- Separate car and motorcycle spot counts
- Numeric spot ordering
- Parking lot filters and pagination

### Tariffs

- Tariff list, create, edit, and delete
- Vehicle-type-specific pricing
- First-hour price
- Additional-hour price
- Full-day price
- Active/inactive state
- Persian validation messages

### Users and Access

- Customer users with roles
- Owner, admin, and operator roles
- Operator parking-lot assignment
- Owner password reset from admin
- User password change from dashboard
- Username validation with English letters/numbers

### Reports

- Date range report
- Vehicle type split
- Payment method split
- Occupancy summary
- Latest exits table
- AJAX pagination for latest exits
- Jalali date filter input

### Admin Panel

- Custom admin URL through `ADMIN_URL`
- Customer approval workflow
- Main models registered in admin
- Bug reports visible in admin
- Jalali and Gregorian date display in admin lists
- Password reset link for customer users
- History models for deleted sessions, payments, and receipts

## SEO and Public Routes

Simple SEO is implemented for the public-facing pages:

- `/`
- `/request/`
- `/login/`
- `/robots.txt`
- `/sitemap.xml`
- Custom 404 response

The canonical production domain is:

```text
https://parkino.shop
```

Dashboard and internal operational routes are intentionally disallowed in `robots.txt`.

## Important Production Notes

Parkino is intended to run behind HTTPS on both CDN and origin.

Recommended production environment values:

```env
DEBUG=False
SITE_NAME=Parkino
SITE_URL=https://parkino.shop
ALLOWED_HOSTS=parkino.shop,www.parkino.shop
CSRF_TRUSTED_ORIGINS=https://parkino.shop,https://www.parkino.shop

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
USE_X_FORWARDED_HOST=True

SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

ADMIN_URL=your-private-admin-path/
```

`SECURE_PROXY_SSL_HEADER` is already configured in settings:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

The reverse proxy/CDN must send:

```text
X-Forwarded-Proto: https
```

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=change-this-secret
DEBUG=True

DB_NAME=parking_db
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-password

SITE_NAME=Parkino
SITE_URL=https://parkino.shop

ALLOWED_HOSTS=127.0.0.1,localhost,parkino.shop,www.parkino.shop
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,https://parkino.shop,https://www.parkino.shop

ADMIN_URL=parkino-control/
```

For production, set `DEBUG=False` and use secure values from the production notes.

## Local Setup

### 1. Create virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Create superuser

```bash
python manage.py createsuperuser
```

### 5. Run development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Useful Commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python manage.py test
python manage.py collectstatic
```

## Main URL Structure

```text
/                         Public homepage
/request/                 Customer request form
/login/                   Login
/dashboard/               Customer dashboard
/sessions/                Parking sessions
/payments/                Payments
/receipts/                Receipts
/parking-lots/            Parking lots
/parking-spots/           Parking spots
/tariffs/                 Tariffs
/reports/                 Reports
/users/                   Users and roles
/settings/                Parking settings
/robots.txt               Robots file
/sitemap.xml              Sitemap
```

Admin URL is controlled by:

```env
ADMIN_URL=parkino-control/
```

## Deployment Checklist

Before deploying or updating the VPS:

- Set `DEBUG=False`.
- Set a strong `SECRET_KEY`.
- Set production database credentials.
- Set `SITE_URL=https://parkino.shop`.
- Set `ALLOWED_HOSTS`.
- Set `CSRF_TRUSTED_ORIGINS`.
- Enable secure cookie settings.
- Confirm CDN forwards `X-Forwarded-Proto: https`.
- Run migrations.
- Run `collectstatic`.
- Configure Gunicorn or another WSGI process manager.
- Put Nginx or equivalent reverse proxy in front of the app.
- Confirm `/robots.txt`, `/sitemap.xml`, and a random 404 URL work.

## Author

Designed and developed by Saro،Ali,Mani

Project: Parking-System
