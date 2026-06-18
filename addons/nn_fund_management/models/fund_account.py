from odoo import models, fields, api


class FundAccount(models.Model):
    _name = 'fund.account'
    _description = 'Fund Account'
    _order = 'name'

    name = fields.Char(string='Account Name', required=True)
    account_type = fields.Selection([
        ('bank', 'Bank Account'),
        ('cash', 'Cash Account'),
        ('other', 'Other Account'),
    ], string='Account Type', required=True)
    account_number = fields.Char(string='Account Number')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

   
    incoming_funds = fields.One2many('fund.incoming', 'fund_account_id', string='Incoming Funds')
    allocation_ids = fields.One2many('fund.allocation', 'fund_account_id', string='Allocations')


    total_received = fields.Float(
        string='Total Received',
        compute='_compute_balances', store=False,
    )
    held_balance = fields.Float(
        string='On Hold',
        compute='_compute_balances', store=False,
    )
    assigned_balance = fields.Float(
        string='Assigned',
        compute='_compute_balances', store=False,
    )
    available_balance = fields.Float(
        string='Available Unassigned',
        compute='_compute_balances', store=False,
    )

    @api.depends(
        'incoming_funds.amount', 'incoming_funds.state',
        'allocation_ids.amount', 'allocation_ids.state',
    )
    def _compute_balances(self):
       
        for acc in self:
            acc.total_received = sum(
                acc.incoming_funds.filtered(
                    lambda f: f.state == 'confirmed'
                ).mapped('amount')
            )
            acc.held_balance = sum(
                acc.allocation_ids.filtered(
                    lambda a: a.state in ('submitted', 'gm_approved')
                ).mapped('amount')
            )
            acc.assigned_balance = sum(
                acc.allocation_ids.filtered(
                    lambda a: a.state == 'approved'
                ).mapped('amount')
            )
            acc.available_balance = (
                acc.total_received - acc.held_balance - acc.assigned_balance
            )