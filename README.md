# NBC Digital Installation Certificate & Warranty System

A Flask + SQLite web app implementing the "Digital Installation Certificate & Mechanic Loyalty"
module from Team Ideators' NBC Idea Factory Season 10 pitch (Top 25, National).

## Features
1. Bearing code verification (live check, valid + not already used)
2. Installation record creation - mechanic auto-identified via login (no dropdown)
3. Digital certificate generation with embedded QR code (verification traceability, from the original pitch's QR-based authenticity concept)
4. Warranty tracking dashboard (active / expiring / expired) with search/filter, admin-only
5. Mechanic loyalty points (awarded per verified install), leaderboard admin-only

## Roles
- **Mechanic login** - required to create installations; name auto-fills from session
- **Admin login** - required to view the warranty dashboard and mechanic leaderboard
- (Officer / distributor / retailer roles are part of the original ecosystem pitch and are
  planned extensions, not built in this MVP - this app focuses on the installation/warranty module.)

## Stack
Python, Flask, SQLite, Bootstrap 5, vanilla JavaScript (fetch API), qrcode + Pillow

## Setup
```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python init_db.py          # creates warranty.db with sample bearings/mechanics/admin
python app.py
```
Visit http://127.0.0.1:5000

## Demo credentials (seeded by init_db.py)
- Mechanic: `rajesh` / `pass123`
- Admin: `admin` / `admin123`
