# 🍳 EGGIFY — Fresh Eggs. Smart Ordering. Better Fitness.

> **Commercial-Ready Digital Egg Ordering & Multi-Gym Wholesale Sourcing Platform**  
> Engineered for single-operator business efficiency alongside college studies.

---

## 🌟 Executive Summary & Business Concept

**EGGIFY** solves a major pain point for fitness athletes and gym-goers: accessing authentic, farm-fresh, high-bioavailability normal raw eggs directly through their gyms at wholesale-discounted prices.

### How The Model Operates:
1. **Zero Salespeople in Gyms**: Standees and posters with unique gym QR codes are placed at the gym reception desk or workout floor.
2. **Instant QR Ordering**: A gym member scans the code (e.g., `eggify.com/order?gym=GYM-GOLDS`). The web app detects their gym without mandatory account registration.
3. **Flexible Packaging**: Choose 6, 12, 18, 30 (crate), 60 (bulk), or custom quantities with live pricing and distance-based delivery.
4. **Instant UPI Payment**: Dynamic UPI QR scanner and 1-click UPI Intent links (Google Pay, PhonePe, Paytm, BHIM, Cred) with backend transaction verification.
5. **Wholesale Aggregation Engine**: The business owner logs into one centralized Admin Portal. The system aggregates all confirmed customer orders, deducts warehouse buffer stock, and calculates the exact crate requirement to procure from vetted poultry farms.
6. **Morning Fulfillment**: The owner procures fresh crates at farm rates and drops labeled batches at each partner gym front desk by 6:00 AM. Members grab their protein post-workout by showing their digital pickup pass.

---

## 🚀 Key Features

### 1. Customer-Facing Mobile-First Web Experience
- **Gym QR Auto-Detection**: Detects `?gym=GYM_CODE` from the URL, auto-selecting the gym hub.
- **Dynamic Pricing Engine**: Server-side calculations prevent client tampering.
- **Packages & Custom Quantities**:
  - Starter Pack (6 Eggs)
  - Fitness Dozen (12 Eggs)
  - Power Athlete (18 Eggs)
  - Gym Pro Crate (30 Eggs)
  - Beast Bulk Crate (60 Eggs)
  - Custom quantity selector (6 to 300 eggs)
- **Fulfillment Options**:
  - Free Gym Collection at front desk
  - Home Delivery (calculated distance-based charge)
- **Live 6-Stage Order Tracking**:
  1. *Order Received*
  2. *Payment Confirmed*
  3. *Wholesale Purchase Pending*
  4. *Eggs Purchased*
  5. *Ready for Collection*
  6. *Delivered / Collected*
- **Digital Pickup Pass**: High-res QR pass and printable invoice.

### 2. Centralized Admin Management Suite
- **Secure Authentication**: Password hashing with Werkzeug security and session validation.
- **8 KPI Real-Time Dashboard**:
  - Today's Orders
  - Total Customers
  - Total Eggs Ordered
  - Total Revenue
  - Paid vs Pending Orders
  - Wholesale Quantity Required
  - Total Delivered Orders
  - Estimated Net Profit
- **Interactive Chart.js Visualizations**: 7-day sales curve and egg volume distribution by partner gym.
- **Wholesale Procurement Engine**:
  - Auto-calculates net eggs required across all paid unfulfilled orders.
  - Multi-supplier price benchmarking.
  - 1-click batch purchase order generator.
  - Printable **Wholesale Purchase Order Slip** for poultry farmers.
- **Inventory & Wastage Management**:
  - Live stock balance (Purchased, Available, Allocated, Distributed, Damaged).
  - Damage & wastage shrinkage logger with monetary loss recalculation.
  - Low-stock warnings.
- **Gym Network & QR Poster Generator**:
  - Add and manage gyms.
  - **1-Click "Print Gym Poster"**: High-resolution, professional A4 print standee for gym noticeboards.
- **Supplier Directory**: Manage contacts, prices per egg, minimum order quantities (MOQ), and preferred vendor status.
- **Customer CRM**: Lifetime spending, total eggs consumed, and gym affiliation.
- **Financial Analytics & P&L**:
  - Breakdown of Wholesale Costs, Delivery Expenses, Packaging, Shrinkage/Damage, and Net Profit Margin.
- **Dynamic Pricing & UPI Settings**:
  - Change egg rates, package discounts, delivery fee per km, and Merchant UPI ID live from the UI.
- **1-Click WhatsApp Notifications**: Pre-formatted templates for Order Confirmation, Ready for Pickup, and Out for Delivery.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.14 / 3.11+, Flask 3.1, Jinja2 |
| **Database** | SQLite (Default Local) / PostgreSQL (Production Ready) via SQLAlchemy 2.1 |
| **Frontend** | HTML5, Tailwind CSS, FontAwesome 6, Google Outfit & Plus Jakarta Sans |
| **Interactive UI** | JavaScript (ES6+), Chart.js |
| **QR Code Engine** | Python `qrcode[pil]`, Base64 PNG image streaming |
| **Security** | Werkzeug PBKDF2 Password Hashing, Server-Side Order Signature Verification |

---

## 📂 Project Directory Structure

```
business-or-eggify/
├── app.py                     # Application factory and entrypoint
├── config.py                  # App configuration & default pricing rules
├── models.py                  # SQLAlchemy relational database models
├── seed.py                    # Database seeding script with realistic data
├── requirements.txt           # Python dependency definitions
├── README.md                  # Comprehensive documentation
├── routes/
│   ├── customer.py            # Customer-facing views, checkout, tracking
│   ├── admin.py               # Centralized admin dashboard & management
│   └── api.py                 # REST APIs, webhooks, price calculators
├── services/
│   ├── pricing.py             # Server-side pricing calculation engine
│   ├── qr_generator.py        # Gym QR & UPI payload generation
│   ├── inventory.py           # Wholesale aggregation & inventory balance
│   └── notifications.py       # WhatsApp links & admin alert generator
├── static/
│   ├── css/custom.css         # Styling, animations, print media rules
│   └── js/
│       ├── main.js            # Customer dynamic order form scripts
│       └── admin.js           # Admin AJAX modals and sidebar behavior
└── templates/
    ├── base.html              # Customer base layout
    ├── 404.html               # Not found error template
    ├── 500.html               # Internal error template
    ├── customer/
    │   ├── index.html         # Homepage: Hero, packages, how it works, gyms
    │   ├── order.html         # Mobile-first order form with QR detection
    │   ├── checkout.html      # UPI QR scanner & 1-click UPI app intent
    │   ├── confirmation.html  # Receipt, pickup pass QR, WhatsApp opt-in
    │   ├── track_lookup.html  # Public order tracking form
    │   └── track_detail.html  # 6-stage fulfillment progress bar
    └── admin/
        ├── layout.html        # Admin layout with sidebar navigation
        ├── login.html         # Secure login screen
        ├── dashboard.html     # KPI overview cards & Chart.js graphs
        ├── orders.html        # Order management & status workflow
        ├── wholesale.html     # Wholesale requirement engine & batch logger
        ├── wholesale_slip.html# Printable purchase order sheet for farms
        ├── inventory.html     # Stock levels, damage & wastage logger
        ├── gyms.html          # Gym management & QR generator
        ├── gym_poster.html    # High-resolution printable gym standee
        ├── suppliers.html     # Wholesale suppliers & price comparison
        ├── customers.html     # Customer CRM & lifetime value table
        ├── analytics.html     # Financial P&L breakdown & gym leaderboard
        └── settings.html      # Dynamic pricing & merchant UPI settings
```

---

## ⚡ Quickstart & Installation

### 1. Clone / Navigate to Directory
```bash
cd c:\Users\hp\OneDrive\Desktop\business-or-eggify
```

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Initialize & Seed Database
This creates all tables and populates sample gyms, suppliers, pricing rules, and active orders:
```bash
python seed.py
```

### 4. Run the Development Server
```bash
python app.py
```
Open your browser and navigate to:
- **Customer Store**: `http://localhost:5000`
- **Gym QR Example**: `http://localhost:5000/order?gym=GYM-GOLDS`
- **Owner Admin Portal**: `http://localhost:5000/admin/login`

---

## 🔐 Admin Portal Credentials

- **Username**: `admin`
- **Password**: `eggify@2026`

---

## 📱 How to Test Key User Flows

### Flow A: Gym Member Orders via Standee QR
1. Go to `http://localhost:5000/order?gym=GYM-GOLDS`.
2. Notice the green **"Gym Identified: Gold's Gym - Indiranagar"** banner.
3. Select the **Fitness Dozen (12 Eggs)** package or customize quantity.
4. Fill in customer name, 10-digit phone number, preferred fulfillment date/time.
5. Click **"Proceed to Pay"**.
6. On the Checkout page, scan the dynamic UPI QR code or enter a mock UTR/Transaction ID.
7. Click **"I Have Completed Payment"**.
8. View the digital receipt with pickup pass QR code.

### Flow B: Live Order Tracking
1. Go to `http://localhost:5000/track`.
2. Enter the Order ID (e.g. `EGG-261120-101`) and mobile number `9876511111`.
3. View the real-time 6-stage fulfillment bar.

### Flow C: Admin Wholesale Procurement
1. Login to `http://localhost:5000/admin`.
2. See the **Action Required: Wholesale Procurement Needed** banner.
3. Click **"Execute Wholesale Purchase"**.
4. Review the supplier comparison and click **"Confirm Purchase Batch"**.
5. Observe orders automatically advancing to **Eggs Purchased** and stock updating.
6. Click **Slip** to view or print the official wholesale purchase order for the poultry farm.

### Flow D: Print Gym Standee Poster
1. In Admin, go to **Gyms & QR Posters**.
2. Click **"Print Gym QR Poster"** next to any partner gym.
3. A print-ready A4 poster appears with the gym's specific QR code, EGGIFY logo, and instructions.
