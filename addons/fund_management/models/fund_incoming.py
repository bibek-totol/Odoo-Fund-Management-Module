from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FundIncoming(models.Model):
    _name = 'fund.incoming'
    _description = 'Incoming Fund'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)
    fund_account_id = fields.Many2one('fund.account', string='Fund Account', required=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    amount = fields.Float(string='Amount', required=True)
    transaction_reference = fields.Char(string='Transaction Reference', required=True)
    source = fields.Char(string='Sender / Source', required=True)
    description = fields.Text(string='Description')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Filename')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    
    @api.model
    def create(self, vals):
       
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'fund.incoming') or 'New'
        return super().create(vals)

   
    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            rec.state = 'confirmed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'rejected'

   
    _sql_constraints = [
        ('ref_unique_per_account',
         'unique(fund_account_id, transaction_reference)',
         'Transaction Reference must be unique within the same Fund Account.'),
    ]