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

    
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

