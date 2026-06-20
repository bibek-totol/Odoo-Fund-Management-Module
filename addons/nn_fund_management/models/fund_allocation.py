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

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Allocation amount must be greater than zero.'),
    ]

    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update(self._normalize_requested_by_vals(vals))
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fund.allocation') or 'New'
        recs = super().create(vals_list)
        for rec in recs:
            rec._check_company_consistency()
        return recs

    def write(self, vals):
        self._check_write_allowed(vals, {
            'state', 'fund_account_id', 'project_id', 'expense_head_id',
            'amount', 'company_id', 'requested_by',
        })
        res = super().write(vals)
        self._check_company_consistency()
        return res

   
    @api.constrains('project_id', 'expense_head_id')
    def _check_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(_(
                    'You must select either a Project or an Expense Head, not both and not neither.'
                ))

    @api.constrains('fund_account_id', 'project_id', 'expense_head_id', 'company_id')
    def _check_company_consistency(self):
        for rec in self:
            target = rec.project_id or rec.expense_head_id
            if rec.fund_account_id and rec.fund_account_id.company_id != rec.company_id:
                raise ValidationError(_('Fund account company must match the allocation company.'))
            if target and target.company_id != rec.company_id:
                raise ValidationError(_('Project or expense head company must match the allocation company.'))

    def _lock_submit_balance_source(self):
        self._lock_records(self.fund_account_id)

   
    def _validate_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            rec._check_company_consistency()
            available = rec.fund_account_id.available_balance
            if rec.amount > available:
                raise UserError(_(
                    'Requested amount (%s) exceeds available unassigned balance (%s).'
                ) % (rec.amount, available))

    def _on_cancelled(self):
        for rec in self:
            target = rec.project_id or rec.expense_head_id
            if target and target.available_fund < 0:
                raise UserError(_(
                    'This approved allocation cannot be cancelled because %s has already used or reserved these funds.'
                ) % target.name)
