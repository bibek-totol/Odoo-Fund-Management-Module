from odoo import models, fields, api


class FundProject(models.Model):
    _name = 'fund.project'
    _description = 'Project'
    _order = 'name'

    name = fields.Char(string='Project Name', required=True)
    code = fields.Char(string='Code', required=True, copy=False)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    
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

    
    total_allocated = fields.Float(string='Total Allocated', compute='_compute_balances')
    available_fund = fields.Float(string='Available Fund', compute='_compute_balances')
    requisition_hold = fields.Float(string='Requisition Hold', compute='_compute_balances')
    transfer_hold = fields.Float(string='Transfer Hold', compute='_compute_balances')
    approved_unspent = fields.Float(string='Approved Unspent', compute='_compute_balances')
    total_spent = fields.Float(string='Total Spent', compute='_compute_balances')
    incoming_transfers = fields.Float(string='Incoming Transfers', compute='_compute_balances')
    outgoing_transfers = fields.Float(string='Outgoing Transfers', compute='_compute_balances')

      
    released_funds = fields.Float(string='Released Funds', compute='_compute_balances')

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
                p.bill_ids.filtered(lambda b: b.state == 'confirmed').mapped('amount')
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
                   
                    hold += (req.amount - req.billed_amount)
                elif req.state == 'closed':
                    released += req.released_amount
            
            p.requisition_hold = hold
            p.released_funds = released
            
          
            p.approved_unspent = (
                p.total_allocated + p.incoming_transfers
                - p.total_spent - p.outgoing_transfers - p.released_funds
            )
            p.available_fund = (
                p.approved_unspent - p.requisition_hold - p.transfer_hold
            )