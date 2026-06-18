from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FundTransfer(models.Model):
    _name = 'fund.transfer'
    _description = 'Fund Transfer'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)

   
    from_project_id = fields.Many2one('fund.project', string='From Project')
    from_expense_head_id = fields.Many2one('fund.expense.head', string='From Expense Head')

 
    to_project_id = fields.Many2one('fund.project', string='To Project')
    to_expense_head_id = fields.Many2one('fund.expense.head', string='To Expense Head')

    amount = fields.Float(string='Amount', required=True)
    reason = fields.Text(string='Reason')
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
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.transfer') or 'New'
        return super().create(vals)

    @api.constrains('from_project_id', 'from_expense_head_id')
    def _check_source(self):
        for rec in self:
            if bool(rec.from_project_id) == bool(rec.from_expense_head_id):
                raise ValidationError(_('Select exactly one source: either a Project or an Expense Head.'))

    @api.constrains('to_project_id', 'to_expense_head_id')
    def _check_destination(self):
        for rec in self:
            if bool(rec.to_project_id) == bool(rec.to_expense_head_id):
                raise ValidationError(_('Select exactly one destination: either a Project or an Expense Head.'))

    def _validate_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            source = rec.from_project_id or rec.from_expense_head_id
            if not source:
                raise UserError(_('Please select a source.'))
            if rec.amount > source.available_fund:
                raise UserError(_(
                    'Transfer amount (%s) exceeds available fund (%s) in source.'
                ) % (rec.amount, source.available_fund))

          
            if rec.from_project_id and rec.to_project_id and rec.from_project_id == rec.to_project_id:
                raise UserError(_('Source and destination project cannot be the same.'))
            if rec.from_expense_head_id and rec.to_expense_head_id and rec.from_expense_head_id == rec.to_expense_head_id:
                raise UserError(_('Source and destination expense head cannot be the same.'))