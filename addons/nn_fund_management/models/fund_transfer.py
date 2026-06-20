from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FundTransfer(models.Model):
    _name = 'fund.transfer'
    _description = 'Fund Transfer'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)
    transfer_type = fields.Selection([
        ('project', 'Project to Project'),
        ('expense', 'Expense Head to Expense Head'),
        ('mixed_pe', 'Project to Expense Head'),
        ('mixed_ep', 'Expense Head to Project'),
    ], string='Transfer Type', required=True, default='project')

    from_project_id = fields.Many2one('fund.project', string='From Project')
    from_expense_head_id = fields.Many2one('fund.expense.head', string='From Expense Head')

    to_project_id = fields.Many2one('fund.project', string='To Project')
    to_expense_head_id = fields.Many2one('fund.expense.head', string='To Expense Head')

    amount = fields.Float(string='Amount', required=True)
    reason = fields.Text(string='Reason')
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    date = fields.Date(string='Date', default=fields.Date.today)
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Filename')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Transfer amount must be greater than zero.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update(self._normalize_requested_by_vals(vals))
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fund.transfer') or 'New'
        recs = super().create(vals_list)
        for rec in recs:
            rec._check_company_consistency()
        return recs

    def write(self, vals):
        self._check_write_allowed(vals, {
            'state', 'transfer_type', 'from_project_id', 'from_expense_head_id',
            'to_project_id', 'to_expense_head_id', 'amount', 'company_id',
            'requested_by',
        })
        res = super().write(vals)
        self._check_company_consistency()
        return res

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

    @api.constrains(
        'transfer_type', 'from_project_id', 'from_expense_head_id',
        'to_project_id', 'to_expense_head_id',
    )
    def _check_transfer_type_matches_endpoints(self):
        for rec in self:
            valid = {
                'project': bool(rec.from_project_id and rec.to_project_id and not rec.from_expense_head_id and not rec.to_expense_head_id),
                'expense': bool(rec.from_expense_head_id and rec.to_expense_head_id and not rec.from_project_id and not rec.to_project_id),
                'mixed_pe': bool(rec.from_project_id and rec.to_expense_head_id and not rec.from_expense_head_id and not rec.to_project_id),
                'mixed_ep': bool(rec.from_expense_head_id and rec.to_project_id and not rec.from_project_id and not rec.to_expense_head_id),
            }
            if not valid.get(rec.transfer_type):
                raise ValidationError(_('Selected source and destination must match the transfer type.'))

    @api.constrains(
        'from_project_id', 'from_expense_head_id', 'to_project_id',
        'to_expense_head_id', 'company_id',
    )
    def _check_company_consistency(self):
        for rec in self:
            holders = (
                rec.from_project_id | rec.to_project_id,
                rec.from_expense_head_id | rec.to_expense_head_id,
            )
            for holder_group in holders:
                for holder in holder_group:
                    if holder.company_id != rec.company_id:
                        raise ValidationError(_('Transfer source and destination companies must match the transfer company.'))

    def _lock_submit_balance_source(self):
        self._lock_records(self.mapped('from_project_id'))
        self._lock_records(self.mapped('from_expense_head_id'))

    def _validate_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            source = rec.from_project_id or rec.from_expense_head_id
            if not source:
                raise UserError(_('Please select a source.'))
            rec._check_company_consistency()
            rec._check_transfer_type_matches_endpoints()
            if rec.amount > source.available_fund:
                raise UserError(_(
                    'Transfer amount (%s) exceeds available fund (%s) in source.'
                ) % (rec.amount, source.available_fund))

          
            if rec.from_project_id and rec.to_project_id and rec.from_project_id == rec.to_project_id:
                raise UserError(_('Source and destination project cannot be the same.'))
            if rec.from_expense_head_id and rec.to_expense_head_id and rec.from_expense_head_id == rec.to_expense_head_id:
                raise UserError(_('Source and destination expense head cannot be the same.'))

    def _on_cancelled(self):
        for rec in self:
            destination = rec.to_project_id or rec.to_expense_head_id
            if destination and destination.available_fund < 0:
                raise UserError(_(
                    'This approved transfer cannot be cancelled because %s has already used or reserved these funds.'
                ) % destination.name)
