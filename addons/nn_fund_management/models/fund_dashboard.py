from odoo import models, fields, api


class FundDashboard(models.TransientModel):
    _name = 'fund.dashboard'
    _description = 'Fund Management Executive Dashboard'

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
  
    total_received = fields.Float(string='Total Received')
    unassigned_balance = fields.Float(string='Unassigned Balance')
    held_amount = fields.Float(string='Held Amount')
    assigned_amount = fields.Float(string='Assigned Amount')
    spent_amount = fields.Float(string='Spent Amount')
    
    
    pending_approval_count = fields.Integer(string='Pending Approvals', compute='_compute_lists')
    project_ids = fields.Many2many(
        'fund.project', string='Project Balances',
        relation='fund_dashboard_project_rel',
    )
    expense_head_ids = fields.Many2many(
        'fund.expense.head', string='Expense-Head Balances',
        relation='fund_dashboard_expense_rel',
    )
    recent_history_ids = fields.Many2many(
        'fund.approval.history', string='Recent Fund Movements',
        relation='fund_dashboard_history_rel',
    )

    @api.model
    def default_get(self, fields_list):
        res = super(FundDashboard, self).default_get(fields_list)
        kpis = self._get_kpis()
        res.update(kpis)
        res.update({
            'project_ids': [(6, 0, self.env['fund.project'].search([], order='name').ids)],
            'expense_head_ids': [(6, 0, self.env['fund.expense.head'].search([], order='name').ids)],
            'recent_history_ids': [(6, 0, self.env['fund.approval.history'].search([], order='date desc', limit=15).ids)],
        })
        return res

    def _get_kpis(self):
        accounts = self.env['fund.account'].search([])
        projects = self.env['fund.project'].search([])
        expense_heads = self.env['fund.expense.head'].search([])

        total_received = sum(accounts.mapped('total_received'))
        unassigned_balance = sum(accounts.mapped('available_balance'))
        assigned_amount = sum(accounts.mapped('assigned_balance'))
        held_amount = (
            sum(accounts.mapped('held_balance')) +
            sum(projects.mapped('requisition_hold')) +
            sum(projects.mapped('transfer_hold')) +
            sum(expense_heads.mapped('requisition_hold')) +
            sum(expense_heads.mapped('transfer_hold'))
        )
        spent_amount = (
            sum(projects.mapped('total_spent')) +
            sum(expense_heads.mapped('total_spent'))
        )

        return {
            'total_received': total_received,
            'unassigned_balance': unassigned_balance,
            'held_amount': held_amount,
            'assigned_amount': assigned_amount,
            'spent_amount': spent_amount,
        }

    def _compute_lists(self):
        for rec in self:
           
            alloc_count = self.env['fund.allocation'].search_count([('state', 'in', ('submitted', 'gm_approved'))])
            req_count = self.env['fund.requisition'].search_count([('state', 'in', ('submitted', 'gm_approved'))])
            trans_count = self.env['fund.transfer'].search_count([('state', 'in', ('submitted', 'gm_approved'))])
            rec.pending_approval_count = alloc_count + req_count + trans_count

    # Action methods to drill down
    def action_view_projects(self):
        return self.env.ref('nn_fund_management.action_fund_project').read()[0]

    def action_view_expense_heads(self):
        return self.env.ref('nn_fund_management.action_fund_expense_head').read()[0]

    def action_view_recent_movements(self):
        return self.env.ref('nn_fund_management.action_fund_history').read()[0]
