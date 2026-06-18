{
    'name': "Fund Management",

    'summary': "Money Management for funding and investment purposes",

    'description': """
Fund Management System

This module provides a complete fund management workflow for organizations.

Main Features:
------------------
* Fund Accounts Management
* Incoming Fund Tracking
* Fund Allocation to Projects
* Expense Head Management
* Fund Requisition Workflow
* Bill Management Against Approved Requisitions
* Fund Transfer Between Projects and Expense Heads
* Multi-Level Approval (GM and MD)
* Balance Tracking (Available, Held, Assigned, Spent)
* Audit Trail and Transaction History
* Role-Based Security and Access Control
* Dashboard and Reporting

""",

    'author': "NN Services & Engineering Ltd.",
    'website': "https://www.nnsel.com/",

    'category': 'Accounting',
    'version': '0.1',

    'depends': ['base', 'mail'],

    'data': [
        'security/fund_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/fund_account_views.xml',
        'views/fund_project_views.xml',
        'views/fund_expense_head_views.xml',
        'views/fund_incoming_views.xml',
        'views/fund_allocation_views.xml',
        'views/fund_requisition_views.xml',
        'views/fund_bill_views.xml',
        'views/fund_transfer_views.xml',
        'views/fund_approval_config_views.xml',
        'views/menus/fund_menus.xml',
        'views/fund_dashboard_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
}
