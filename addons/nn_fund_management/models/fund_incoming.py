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
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.incoming') or 'New'
        return super().create(vals)

    def action_confirm(self):
       
        if not self.user_has_groups('nn_fund_management.group_finance_user') and not self.user_has_groups('nn_fund_management.group_fund_admin'):
            raise UserError(_('Only authorized Finance Users can confirm incoming funds.'))

        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            rec.state = 'confirmed'
            
            # Log audit history
            self.env['fund.approval.history'].create({
                'res_model': rec._name,
                'res_id': rec.id,
                'document_reference': rec.name,
                'approval_level': 'confirm',
                'approver': self.env.user.id,
                'result': 'approved',
                'comment': rec.description or 'Incoming fund confirmed.',
                'new_state': 'confirmed',
                'amount': rec.amount,
                'fund_account_id': rec.fund_account_id.id,
                'currency_id': self.env.company.currency_id.id,
            })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'confirmed' and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only Fund Administrators can cancel confirmed incoming funds.'))
            rec.state = 'rejected'

    
    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('You cannot delete a confirmed incoming fund. Cancel it first.'))
        return super().unlink()

    _sql_constraints = [
        ('ref_unique_per_account', 'unique(fund_account_id, transaction_reference)', 'Transaction Reference must be unique within the same Fund Account.'),
    ]