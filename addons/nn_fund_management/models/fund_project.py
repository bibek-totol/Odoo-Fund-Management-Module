from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FundProject(models.Model):
    _name = 'fund.project'
    _description = 'Project'
    _order = 'name'

    name = fields.Char(string='Project Name', required=True)
    code = fields.Char(string='Code', required=True, copy=False)
    project_manager_id = fields.Many2one('res.users', string='Project Manager')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    
    allocation_ids = fields.One2many(
        'fund.allocation', 'project_id', string='Allocations')
    requisition_ids = fields.One2many(
        'fund.requisition', 'project_id', string='Requisitions')
    bill_ids = fields.One2many(
        'fund.bill', 'project_id', string='Bills')
    outgoing_transfer_ids = fields.One2many(
        'fund.transfer', 'from_project_id', string='Outgoing Transfers')
    incoming_transfer_ids = fields.One2many(
        'fund.transfer', 'to_project_id', string='Incoming Transfers')

    
    total_allocated = fields.Float(string='Total Allocated', compute='_compute_balances', readonly=True)
    available_fund = fields.Float(string='Available Fund', compute='_compute_balances', readonly=True)
    requisition_hold = fields.Float(string='Requisition Hold', compute='_compute_balances', readonly=True)
    transfer_hold = fields.Float(string='Transfer Hold', compute='_compute_balances', readonly=True)
    approved_unspent = fields.Float(string='Approved But Unspent', compute='_compute_balances', readonly=True)
    total_spent = fields.Float(string='Total Spent', compute='_compute_balances', readonly=True)
    incoming_transfers = fields.Float(string='Incoming Transfers', compute='_compute_balances', readonly=True)
    outgoing_transfers = fields.Float(string='Outgoing Transfers', compute='_compute_balances', readonly=True)

      
    released_funds = fields.Float(string='Released Funds', compute='_compute_balances', readonly=True)

    @api.depends(
        'allocation_ids.amount', 'allocation_ids.state',
        'requisition_ids.amount', 'requisition_ids.state', 'requisition_ids.billed_amount', 'requisition_ids.released_amount',
        'bill_ids.amount', 'bill_ids.state',
        'outgoing_transfer_ids.amount', 'outgoing_transfer_ids.state',
        'incoming_transfer_ids.amount', 'incoming_transfer_ids.state',
    )
    def _compute_balances(self):
        for p in self:
            p.total_allocated = sum(
                p.allocation_ids.filtered(lambda a: a.state == 'approved').mapped('amount')
            )
            p.total_spent = sum(
                p.bill_ids.filtered(lambda b: b.state in ('posted', 'paid')).mapped('amount')
            )
            p.transfer_hold = sum(
                p.outgoing_transfer_ids.filtered(
                    lambda t: t.state in ('submitted', 'gm_approved')
                ).mapped('amount')
            )
            p.outgoing_transfers = sum(
                p.outgoing_transfer_ids.filtered(lambda t: t.state == 'approved').mapped('amount')
            )
            p.incoming_transfers = sum(
                p.incoming_transfer_ids.filtered(lambda t: t.state == 'approved').mapped('amount')
            )
            
           
            hold = 0.0
            released = 0.0
            for req in p.requisition_ids:
                if req.state in ('submitted', 'gm_approved', 'approved'):
                   
                    hold += max(req.amount - req.billed_amount - req.released_amount, 0.0)
                elif req.state == 'closed':
                    released += req.released_amount
            
            p.requisition_hold = hold
            p.released_funds = released
            
          
            p.approved_unspent = (
                p.total_allocated + p.incoming_transfers
                - p.total_spent - p.outgoing_transfers
            )
            p.available_fund = (
                p.approved_unspent - p.requisition_hold - p.transfer_hold
            )
            if p.available_fund < 0 and abs(p.available_fund) < 0.00001:
                p.available_fund = 0.0

    @api.constrains('code', 'company_id')
    def _check_unique_code_per_company(self):
        for rec in self:
            duplicate = self.search_count([
                ('id', '!=', rec.id),
                ('code', '=', rec.code),
                ('company_id', '=', rec.company_id.id),
            ])
            if duplicate:
                raise ValidationError(_('Project code must be unique per company.'))

    def _ensure_admin_for_master_change(self):
        if not self.user_has_groups('nn_fund_management.group_fund_admin'):
            raise UserError(_('Only Fund Administrators can change project status.'))

    def action_open(self):
        self._ensure_admin_for_master_change()
        for rec in self:
            rec.state = 'open'

    def action_close(self):
        self._ensure_admin_for_master_change()
        for rec in self:
            if rec.available_fund or rec.requisition_hold or rec.transfer_hold:
                raise UserError(_('A project with remaining available or held funds cannot be closed.'))
            rec.state = 'closed'
