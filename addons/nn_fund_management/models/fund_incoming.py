from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    _sql_constraints = [
        ('ref_unique_per_account', 'unique(fund_account_id, transaction_reference)', 'Transaction Reference must be unique within the same Fund Account.'),
        ('amount_positive', 'CHECK(amount > 0)', 'Incoming fund amount must be greater than zero.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fund.incoming') or 'New'
        recs = super().create(vals_list)
        for rec in recs:
            rec._check_company_consistency()
        return recs

    def write(self, vals):
        if not self.env.context.get('fund_internal_write'):
            if 'state' in vals:
                raise UserError(_('Status changes must use the workflow buttons.'))
            protected = {'fund_account_id', 'amount', 'transaction_reference', 'company_id'}
            if protected & set(vals):
                for rec in self:
                    if rec.state != 'draft':
                        raise UserError(_('You cannot modify confirmed or cancelled incoming fund values.'))
        res = super().write(vals)
        self._check_company_consistency()
        return res

    @api.constrains('fund_account_id', 'company_id')
    def _check_company_consistency(self):
        for rec in self:
            if rec.fund_account_id and rec.fund_account_id.company_id != rec.company_id:
                raise ValidationError(_('Fund account company must match the incoming fund company.'))

    def _lock_fund_account(self):
        accounts = self.mapped('fund_account_id').exists()
        if accounts:
            self.env.cr.execute(
                'SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE' % accounts._table,
                [tuple(sorted(accounts.ids))],
            )

    def action_confirm(self):
       
        if not self.env.user.has_group('nn_fund_management.group_finance_user') and not self.env.user.has_group('nn_fund_management.group_fund_admin'):
            raise UserError(_('Only authorized Finance Users can confirm incoming funds.'))

        for rec in self:
            if rec.state != 'draft':
                continue
            rec._lock_fund_account()
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            rec._check_company_consistency()
            old_state = rec.state
            rec.with_context(fund_internal_write=True).state = 'confirmed'
            
            # Log audit history
            self.env['fund.approval.history'].sudo().create({
                'res_model': rec._name,
                'res_id': rec.id,
                'document_reference': rec.name,
                'approval_level': 'confirm',
                'approver': self.env.user.id,
                'result': 'approved',
                'comment': rec.description or 'Incoming fund confirmed.',
                'previous_state': old_state,
                'new_state': 'confirmed',
                'amount': rec.amount,
                'fund_account_id': rec.fund_account_id.id,
                'creator_id': rec.create_uid.id,
                'submitted_by_id': self.env.user.id,
                'company_id': rec.company_id.id,
                'currency_id': rec.company_id.currency_id.id,
            })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'confirmed' and not self.env.user.has_group('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only Fund Administrators can cancel confirmed incoming funds.'))
            if rec.state not in ('draft', 'confirmed'):
                raise UserError(_('Only draft or confirmed incoming funds can be cancelled.'))
            old_state = rec.state
            new_state = 'cancelled' if old_state == 'confirmed' else 'rejected'
            rec.with_context(fund_internal_write=True).state = new_state
            self.env['fund.approval.history'].sudo().create({
                'res_model': rec._name,
                'res_id': rec.id,
                'document_reference': rec.name,
                'approval_level': 'cancel',
                'approver': self.env.user.id,
                'result': 'cancelled',
                'comment': rec.description or 'Incoming fund cancelled.',
                'previous_state': old_state,
                'new_state': new_state,
                'amount': rec.amount,
                'fund_account_id': rec.fund_account_id.id,
                'creator_id': rec.create_uid.id,
                'submitted_by_id': self.env.user.id,
                'company_id': rec.company_id.id,
                'currency_id': rec.company_id.currency_id.id,
            })

    
    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('You cannot delete a confirmed incoming fund. Cancel it first.'))
        return super().unlink()
