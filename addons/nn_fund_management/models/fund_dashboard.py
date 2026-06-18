from odoo import models, fields, api, _


class FundDashboard(models.TransientModel):
    _name = 'fund.dashboard'
    _description = 'Fund Management Dashboard'

  
    total_received = fields.Float(string='Total Received', readonly=True)
    unassigned_balance = fields.Float(string='Unassigned Balance', readonly=True)
    held_amount = fields.Float(string='On Hold', readonly=True)
    assigned_amount = fields.Float(string='Assigned', readonly=True)
    total_spent = fields.Float(string='Total Spent', readonly=True)

    
    pending_allocations = fields.Integer(string='Pending Allocations', readonly=True)
    pending_requisitions = fields.Integer(string='Pending Requisitions', readonly=True)
    pending_transfers = fields.Integer(string='Pending Transfers', readonly=True)
    total_pending = fields.Integer(string='Total Pending Approvals', readonly=True)
    
    name = fields.Char(string='Name', default='Fund Management Dashboard')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

   
    project_ids = fields.Many2many(
        'fund.project', string='Projects',
        compute='_compute_lists',
    )
    expense_head_ids = fields.Many2many(
        'fund.expense.head', string='Expense Heads',
        compute='_compute_lists',
    )
    recent_movement_ids = fields.Many2many(
        'fund.approval.history', string='Recent Movements',
        compute='_compute_lists',
    )

   

    @api.model
    def _get_kpis(self):
      
        accounts = self.env['fund.account'].search([
            ('company_id', '=', self.env.company.id),
        ])

        total_received = sum(accounts.mapped('total_received'))
        held_amount = sum(accounts.mapped('held_balance'))
        assigned_amount = sum(accounts.mapped('assigned_balance'))
        unassigned_balance = sum(accounts.mapped('available_balance'))

      
        total_spent = sum(
            self.env['fund.bill'].search([
                ('state', '=', 'confirmed'),
                ('company_id', '=', self.env.company.id),
            ]).mapped('amount')
        )

        pending_states = ('submitted', 'gm_approved')
        pending_allocations = self.env['fund.allocation'].search_count([
            ('state', 'in', pending_states),
            ('company_id', '=', self.env.company.id),
        ])
        pending_requisitions = self.env['fund.requisition'].search_count([
            ('state', 'in', pending_states),
            ('company_id', '=', self.env.company.id),
        ])
        pending_transfers = self.env['fund.transfer'].search_count([
            ('state', 'in', pending_states),
            ('company_id', '=', self.env.company.id),
        ])

        return {
            'total_received': total_received,
            'unassigned_balance': unassigned_balance,
            'held_amount': held_amount,
            'assigned_amount': assigned_amount,
            'total_spent': total_spent,
            'pending_allocations': pending_allocations,
            'pending_requisitions': pending_requisitions,
            'pending_transfers': pending_transfers,
            'total_pending': pending_allocations + pending_requisitions + pending_transfers,
            'company_id': self.env.company.id,
            'name': _('Fund Management Dashboard (%s)') % fields.Date.today(),
        }

   

    @api.depends()
    def _compute_lists(self):
        for rec in self:
            rec.project_ids = self.env['fund.project'].search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True),
            ])
            rec.expense_head_ids = self.env['fund.expense.head'].search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True),
            ])
          
            rec.recent_movement_ids = self.env['fund.approval.history'].search(
                [], order='date desc', limit=20,
            )

   

    @api.model
    def action_open_dashboard(self):
       
        kpis = self._get_kpis()
        record = self.create(kpis)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fund Management Dashboard'),
            'res_model': 'fund.dashboard',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
            'context': self.env.context,
        }
