from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


_WARN_THRESHOLD = 0.90


class FundRequisition(models.Model):
    _name = 'fund.requisition'
    _description = 'Fund Requisition'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'
    state = fields.Selection(selection_add=[('closed', 'Closed')])

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)
    project_id = fields.Many2one('fund.project', string='Project')
    expense_head_id = fields.Many2one('fund.expense.head', string='Expense Head')
    amount = fields.Float(string='Requested Amount', required=True)
    purpose = fields.Text(string='Purpose')
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    required_date = fields.Date(string='Required Date')
    attachment = fields.Binary(string='Supporting Attachment')
    attachment_name = fields.Char(string='Attachment Filename')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    bill_ids = fields.One2many('fund.bill', 'requisition_id', string='Bills')
    billed_amount = fields.Float(string='Billed Amount', compute='_compute_billed')
    released_amount = fields.Float(string='Released Amount', copy=False, default=0.0, readonly=True)
    remaining_amount = fields.Float(string='Remaining Billable Amount', compute='_compute_billed')

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Requisition amount must be greater than zero.'),
        ('released_non_negative', 'CHECK(released_amount >= 0)', 'Released amount cannot be negative.'),
    ]

    @api.depends('bill_ids.amount', 'bill_ids.state', 'amount', 'released_amount')
    def _compute_billed(self):
        for rec in self:
            rec.billed_amount = sum(
                rec.bill_ids.filtered(lambda b: b.state in ('posted', 'paid')).mapped('amount')
            )
            rec.remaining_amount = max(rec.amount - rec.billed_amount - rec.released_amount, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update(self._normalize_requested_by_vals(vals))
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fund.requisition') or 'New'
        recs = super().create(vals_list)
        for rec in recs:
            rec._check_company_consistency()
        return recs

    def write(self, vals):
        self._check_write_allowed(vals, {
            'state', 'project_id', 'expense_head_id', 'amount',
            'company_id', 'released_amount', 'requested_by',
        })
        res = super().write(vals)
        self._check_company_consistency()
        return res

    @api.constrains('project_id', 'expense_head_id')
    def _check_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(_('Select either a Project or an Expense Head, not both.'))

    @api.constrains('project_id', 'expense_head_id', 'company_id')
    def _check_company_consistency(self):
        for rec in self:
            holder = rec.project_id or rec.expense_head_id
            if holder and holder.company_id != rec.company_id:
                raise ValidationError(_('Project or expense head company must match the requisition company.'))

    def _lock_submit_balance_source(self):
        self._lock_records(self.mapped('project_id'))
        self._lock_records(self.mapped('expense_head_id'))

    def _validate_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            holder = rec.project_id or rec.expense_head_id
            if not holder:
                raise UserError(_('Please select a Project or Expense Head.'))
            rec._check_company_consistency()
            if rec.amount > holder.available_fund:
                raise UserError(_(
                    'Requested amount (%s) exceeds available fund (%s) for %s.'
                ) % (rec.amount, holder.available_fund, holder.name))
    def _check_near_exhaustion(self):
        for rec in self:
            if rec.amount <= 0 or rec.state not in ('approved',):
                continue
            ratio = rec.billed_amount / rec.amount
            if ratio >= _WARN_THRESHOLD:
                pct = int(ratio * 100)
                rec._schedule_activity(
                    user_id=rec.requested_by.id,
                    summary=_('Requisition %s%% Used: %s') % (pct, rec.name),
                    note=_(
                        'Requisition <b>%s</b> has reached <b>%s%%</b> of its approved amount.<br/>'
                        'Approved: %s &nbsp;|&nbsp; Billed so far: %s &nbsp;|&nbsp; Remaining: %s'
                    ) % (
                        rec.name, pct,
                        rec.amount, rec.billed_amount, rec.remaining_amount,
                    ),
                )
    def action_close(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Only approved requisitions can be closed.'))
            rec._check_current_user_is_requester_or_admin()
            rec.with_context(fund_internal_write=True).released_amount = max(rec.amount - rec.billed_amount, 0.0)
            rec.with_context(fund_internal_write=True).state = 'closed'
            rec._log_approval('close', 'closed', 'Requisition closed. Remaining funds released.', 'approved', 'closed')

    def action_reopen(self):
        for rec in self:
            if rec.state != 'closed':
                raise UserError(_('Only closed requisitions can be reopened.'))
            if not self.env.user.has_group('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only Fund Administrators can reopen closed requisitions.'))
            holder = rec.project_id or rec.expense_head_id
            rec._lock_records(holder)
            if rec.released_amount > holder.available_fund:
                raise UserError(_('The released amount is no longer available and cannot be reserved again.'))
            rec.with_context(fund_internal_write=True).released_amount = 0.0
            rec.with_context(fund_internal_write=True).state = 'approved'
            rec._log_approval('reopen', 'reopened', 'Requisition reopened.', 'closed', 'approved')
