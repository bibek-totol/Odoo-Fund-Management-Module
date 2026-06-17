from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FundAllocation(models.Model):
   
    _name = 'fund.allocation'
    _description = 'Fund Allocation'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)
    fund_account_id = fields.Many2one('fund.account', string='Fund Account', required=True)
    project_id = fields.Many2one('fund.project', string='Project')
    expense_head_id = fields.Many2one('fund.expense.head', string='Expense Head')
    amount = fields.Float(string='Amount', required=True)
    purpose = fields.Text(string='Purpose')
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Filename')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )

    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'fund.allocation') or 'New'
        return super().create(vals)

   
    @api.constrains('project_id', 'expense_head_id')
    def _check_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(_(
                    'You must select either a Project or an Expense Head, not both and not neither.'
                ))

   
    def _validate_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            available = rec.fund_account_id.available_balance
            if rec.amount > available:
                raise UserError(_(
                    'Requested amount (%s) exceeds available unassigned balance (%s).'
                ) % (rec.amount, available))