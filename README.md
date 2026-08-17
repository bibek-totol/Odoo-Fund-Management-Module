## Demo: https://youtu.be/C7TT_5NeUxg?si=wVlMOXBwCz-GmhVJ
# Odoo Fund Management Module

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-purple.svg)](https://www.odoo.com/)
[![License](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
[![Maintainer](https://img.shields.io/badge/Maintained%20by-NN%20Services%20%26%20Engineering-orange.svg)](https://www.nnsel.com/)

A comprehensive fund management solution for Odoo, designed to handle complex financial workflows, fund allocations, and expense tracking with multi-level approval hierarchies.

---

## Key Features

*   **Fund Accounts Management:** Centralized tracking of financial accounts.
*   **Incoming Fund Tracking:** Detailed logging and categorization of incoming capital.
*   **Strategic Allocations:** Project-specific allocations with real-time balance tracking.
*   **Expense Head Management:** Granular control over spending categories.
*   **Requisition Workflow:** Formal request system for fund utilization.
*   **Bill Management:** Direct linkage to approved requisitions for internal auditing.
*   **Internal Transfers:** Movement of funds between projects and expense heads.
*   **Multi-Level Approvals:** Integrated GM and MD approval stages.
*   **Dynamic Dashboard:** High-level overview of Available, Held, Assigned, and Spent balances.

---

## Live Demo

Experience the application in action on our live server:

*   **URL:** [https://65.1.163.216.nip.io/](https://65.1.163.216.nip.io/)
*   **Default Credentials:**
    *   **Email:** `admin`
    *   **Password:** `admin`

> [!NOTE]
> After logging in, navigate to the **Apps** section and search for **"Fund Management"** to explore the application features.

---

## Technical Specifications

### Odoo Version
*   **Base Version:** Odoo 19.0
*   **Edition:** Compatible with Community & Enterprise

### Required Dependencies
*   `base`: Core Odoo framework.
*   `mail`: Notification system and communication threads.

### Environment Prerequisites
*   Docker & Docker Compose
*   PostgreSQL 16

---

## Infrastructure & Deployment

The production instance is deployed with a professional-grade cloud architecture:

*   **Cloud Hosting:** Hosted on **AWS EC2** for scalable and reliable performance.
*   **Networking:** Configured with an **AWS Elastic IP**, providing a stable endpoint for access without the requirement of a dedicated domain name.
*   **Web Server:** **Nginx** is utilized as a high-performance reverse proxy.
*   **Security:** Full **SSL/TLS** encryption is implemented to secure all communications between the client and the server.

---

## Installation Instructions

To set up the project locally for development or testing:

### 1. Clone the Repository
```bash
git clone https://github.com/bibek-totol/Odoo-Fund-Management-Module.git
cd Odoo-Fund-Management-Module
```

### 2. Configure Environment
Create a `.env` file in the root directory and ensure the following variables are set:
```ini
POSTGRES_DB=fund(Can be anything)
POSTGRES_USER=odoo(Can be anything)
POSTGRES_PASSWORD=odoo(Can be anything)
ODOO_VERSION=19
ODOO_PORT=8069
ODOO_LONGPOLL_PORT=8072
```

### 3. Launch with Docker
```bash
docker-compose up -d
```

### 4. Access the Application
Open your browser and navigate to `http://localhost:8069`. Log in using the default credentials:
*   **Email:** `admin`
*   **Password:** `admin`

> [!TIP]
> You can change the password from **Settings -> Users & Companies -> Users** after the initial login.

---

## Configuration Steps

1.  **Initialize Module:** Navigate to **Apps**, click **Update Apps List**, search for `nn_fund_management`, and click **Activate**.
2.  **Access Control:** Ensure users are assigned to correct groups (Fund Manager, GM, MD) under **Settings > Users & Companies**.
3.  **Sequence Verification:** Check fund reference sequences under **Technical > Sequences & Identifiers**.
4.  **Demo Data:** (Optional) Load demo data during installation to explore pre-configured workflows.

---

## Testing Instructions

### Functional Testing
1.  **Fund Initialization:** Create a Fund Account and record an Incoming Fund.
2.  **Allocation Flow:** Allocate funds to a specific Project.
3.  **Requisition Lifecycle:** Create a Requisition and advance states: `Draft` -> `Locked` -> `GM Approval` -> `MD Approval`.
4.  **Bill Entry:** Create a Bill against an approved Requisition.
5.  **Dashboard Audit:** Verify balance updates across all states.

### Automated Testing
Run Odoo tests via command line:
```bash
docker exec -it odoo_app odoo -c /etc/odoo/odoo.conf -i nn_fund_management --test-enable --stop-after-init
```

---

## Assumptions

1.  The hierarchical approval structure follows User -> GM -> MD workflow.
2.  All transactions are processed in the base currency of the configured Company.
3.  Dockerized environment handles all underlying Python dependencies for Odoo 19.

---

## Known Limitations

The following advanced features are recognized as out of scope for the current version:

### 1. Configurable Approval Rules
Fixed approval sequence logic is currently implemented. Dynamic rules based on the following are reserved for future updates:
*   Request type or Expense Category.
*   Amount thresholds (e.g., Up to 50k: GM only; Above 200k: Multi-stage).
*   Company or Security Group specific sequences.

### 2. Bank Email Integration
Automatic parsing of bank transaction notifications is not implemented, including:
*   IMAP/POP3 notification ingestion.
*   Data extraction (Bank Name, Account Number, Transaction Reference).
*   Duplicate detection logic (via Message ID or Reference).
*   Automatic "Pending Verification" record creation.

---

## Author
**NN Services & Engineering Ltd.**  
[www.nnsel.com](https://www.nnsel.com/)
