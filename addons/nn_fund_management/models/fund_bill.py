from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FundBill(models.Model):
    _name = 'fund.bill'
    _description = 'Bill Against Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Bill No', default='New', readonly=True, copy=False)
    requisition_id = fields.Many2one(
        'fund.requisition', string='Requisition', required=True,
        domain="[('state', '=', 'approved')]")

    project_id = fields.Many2one(
        'fund.project', string='Project',
        related='requisition_id.project_id', store=True, readonly=True)

    expense_head_id = fields.Many2one(
        'fund.expense.head', string='Expense Head',
        related='requisition_id.expense_head_id', store=True, readonly=True)

    amount = fields.Float(string='Bill Amount', required=True)
    vendor = fields.Char(string='Vendor / Supplier')
    date = fields.Date(string='Bill Date', default=fields.Date.today)
    description = fields.Text(string='Description')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Filename')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Bill amount must be greater than zero.'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.bill') or 'New'
        rec = super().create(vals)
        rec._check_requisition_company()
        return rec

    def write(self, vals):
        if not self.env.context.get('fund_internal_write'):
            if 'state' in vals:
                raise UserError(_('Status changes must use the workflow buttons.'))
            protected = {'requisition_id', 'amount', 'company_id'}
            if protected & set(vals):
                for rec in self:
                    if rec.state != 'draft':
                        raise UserError(_('You cannot modify bill financial values after posting.'))
        res = super().write(vals)
        self._check_requisition_company()
        return res

    @api.constrains('requisition_id', 'project_id', 'expense_head_id')
    def _check_requisition_match(self):
        for rec in self:
            if rec.requisition_id.project_id and rec.project_id != rec.requisition_id.project_id:
                raise ValidationError(_("Project does not match the requisition's project."))
            if rec.requisition_id.expense_head_id and rec.expense_head_id != rec.requisition_id.expense_head_id:
                raise ValidationError(_("Expense Head does not match the requisition's expense head."))

    @api.constrains('requisition_id', 'company_id')
    def _check_requisition_company(self):
        for rec in self:
            if rec.requisition_id and rec.requisition_id.company_id != rec.company_id:
                raise ValidationError(_('Bill company must match the requisition company.'))

    def _check_finance_user(self):
        if not self.user_has_groups('nn_fund_management.group_finance_user') and not self.user_has_groups('nn_fund_management.group_fund_admin'):
            raise UserError(_('Only authorized Finance Users can post, pay, or cancel bills.'))

    def _lock_requisition_balance(self):
        requisitions = self.mapped('requisition_id').exists()
        if requisitions:
            self.env.cr.execute(
                'SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE' % requisitions._table,
                [tuple(sorted(requisitions.ids))],
            )
        projects = self.mapped('project_id').exists()
        if projects:
            self.env.cr.execute(
                'SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE' % projects._table,
                [tuple(sorted(projects.ids))],
            )
        expenses = self.mapped('expense_head_id').exists()
        if expenses:
            self.env.cr.execute(
                'SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE' % expenses._table,
                [tuple(sorted(expenses.ids))],
            )

    def action_post(self):
        self._check_finance_user()
        for rec in self:
            if rec.state != 'draft':
                continue
            rec._lock_requisition_balance()
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            if rec.requisition_id.state != 'approved':
                raise UserError(_('Requisition must be approved to post bills.'))
            rec._check_requisition_company()

            other_billed = sum(
                rec.requisition_id.bill_ids.filtered(
                    lambda b: b.state in ('posted', 'paid') and b.id != rec.id
                ).mapped('amount')
            )
            billable_balance = rec.requisition_id.amount - rec.requisition_id.released_amount - other_billed
            if rec.amount > billable_balance:
                raise UserError(_(
                    'Bill amount (%s) exceeds remaining billable amount (%s).'
                ) % (rec.amount, billable_balance))

            old_state = rec.state
            rec.with_context(fund_internal_write=True).state = 'posted'

            # Log audit history
            self.env['fund.approval.history'].sudo().create({
                'res_model': rec._name,
                'res_id': rec.id,
                'document_reference': rec.name,
                'approval_level': 'post',
                'approver': self.env.user.id,
                'result': 'posted',
                'comment': rec.description or 'Bill posted.',
                'previous_state': old_state,
                'new_state': 'posted',
                'amount': rec.amount,
                'project_id': rec.project_id.id,
                'expense_head_id': rec.expense_head_id.id,
                'creator_id': rec.create_uid.id,
                'submitted_by_id': self.env.user.id,
                'company_id': rec.company_id.id,
                'currency_id': rec.company_id.currency_id.id,
            })
            
          
            rec.requisition_id._compute_billed()
            rec.requisition_id._check_near_exhaustion()

    def action_pay(self):
        self._check_finance_user()
        for rec in self:
            if rec.state != 'posted':
                raise UserError(_('Only posted bills can be paid.'))
            old_state = rec.state
            rec.with_context(fund_internal_write=True).state = 'paid'
            self.env['fund.approval.history'].sudo().create({
                'res_model': rec._name,
                'res_id': rec.id,
                'document_reference': rec.name,
                'approval_level': 'pay',
                'approver': self.env.user.id,
                'result': 'paid',
                'comment': rec.description or 'Bill paid.',
                'previous_state': old_state,
                'new_state': 'paid',
                'amount': rec.amount,
                'project_id': rec.project_id.id,
                'expense_head_id': rec.expense_head_id.id,
                'creator_id': rec.create_uid.id,
                'submitted_by_id': self.env.user.id,
                'company_id': rec.company_id.id,
                'currency_id': rec.company_id.currency_id.id,
            })

    def action_cancel(self):
        self._check_finance_user()
        for rec in self:
            if rec.state not in ('draft', 'posted', 'paid'):
                raise UserError(_('Only draft, posted, or paid bills can be cancelled.'))
            if rec.state in ('posted', 'paid') and rec.requisition_id.state == 'closed':
                raise UserError(_('You cannot cancel a bill against a closed requisition. Reopen the requisition first.'))
            rec._lock_requisition_balance()
            old_state = rec.state
            rec.with_context(fund_internal_write=True).state = 'cancelled'
            self.env['fund.approval.history'].sudo().create({
                'res_model': rec._name,
                'res_id': rec.id,
                'document_reference': rec.name,
                'approval_level': 'cancel',
                'approver': self.env.user.id,
                'result': 'cancelled',
                'comment': rec.description or 'Bill cancelled.',
                'previous_state': old_state,
                'new_state': 'cancelled',
                'amount': rec.amount,
                'project_id': rec.project_id.id,
                'expense_head_id': rec.expense_head_id.id,
                'creator_id': rec.create_uid.id,
                'submitted_by_id': self.env.user.id,
                'company_id': rec.company_id.id,
                'currency_id': rec.company_id.currency_id.id,
            })

    def unlink(self):
        for rec in self:
            if rec.state in ('posted', 'paid'):
                raise UserError(_('You cannot delete a posted or paid bill. Cancel it instead.'))
        return super().unlink()
