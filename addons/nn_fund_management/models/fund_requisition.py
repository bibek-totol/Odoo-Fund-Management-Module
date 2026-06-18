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

    bill_ids = fields.One2many('fund.bill', 'requisition_id', string='Bills')
    billed_amount = fields.Float(string='Billed Amount', compute='_compute_billed')
    released_amount = fields.Float(string='Released Amount', copy=False, default=0.0, readonly=True)
    remaining_amount = fields.Float(string='Remaining Billable Amount', compute='_compute_billed')

    @api.depends('bill_ids.amount', 'bill_ids.state', 'amount', 'released_amount')
    def _compute_billed(self):
        for rec in self:
            rec.billed_amount = sum(
                rec.bill_ids.filtered(lambda b: b.state == 'confirmed').mapped('amount')
            )
            rec.remaining_amount = rec.amount - rec.billed_amount - rec.released_amount

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.requisition') or 'New'
        return super().create(vals)

    @api.constrains('project_id', 'expense_head_id')
    def _check_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(_('Select either a Project or an Expense Head, not both.'))

    def _validate_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            holder = rec.project_id or rec.expense_head_id
            if not holder:
                raise UserError(_('Please select a Project or Expense Head.'))
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
            rec.released_amount = rec.amount - rec.billed_amount
            rec.state = 'closed'
            rec._log_approval('close', 'approved', 'Requisition closed manually. Remaining funds released.', 'approved', 'closed')

    def action_reopen(self):
        for rec in self:
            if rec.state != 'closed':
                raise UserError(_('Only closed requisitions can be reopened.'))
            rec.released_amount = 0.0
            rec.state = 'approved'
            rec._log_approval('reopen', 'submitted', 'Requisition reopened.', 'closed', 'approved')