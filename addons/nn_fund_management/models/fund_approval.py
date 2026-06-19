from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


_REQUISITION_WARN_THRESHOLD = 0.90


class FundApprovalMixin(models.AbstractModel):
    _name = 'fund.approval.mixin'
    _description = 'Fund Approval Workflow'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('gm_approved', 'GM Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    requested_by = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user,
        readonly=True, tracking=True,
    )

    approval_comment = fields.Text(string='Comment', copy=False)

    approval_history_ids = fields.One2many(
        'fund.approval.history',
        compute='_compute_approval_history',
        string='Audit History',
    )

    @api.depends('state')
    def _compute_approval_history(self):
        History = self.env['fund.approval.history']
        for rec in self:
            rec.approval_history_ids = History.search([
                ('res_model', '=', rec._name),
                ('res_id', '=', rec.id),
            ])

    def _get_approval_config(self):
        Config = self.env['fund.approval.config']
        company = getattr(self, 'company_id', False) or self.env.company
        config = Config.search([('company_id', '=', company.id)], limit=1)
        if not config:
            raise UserError(_('No approval configuration found for company %s. Please create one.') % company.name)
        return config

    def _log_approval(self, level, result, comment='', previous_state='', new_state=''):
        self.ensure_one()
        amount = self.amount if hasattr(self, 'amount') else 0.0
        account_id = self.fund_account_id.id if hasattr(self, 'fund_account_id') and self.fund_account_id else False
        project_id = self.project_id.id if hasattr(self, 'project_id') and self.project_id else False
        expense_id = self.expense_head_id.id if hasattr(self, 'expense_head_id') and self.expense_head_id else False
        company = getattr(self, 'company_id', False) or self.env.company
        if not project_id and hasattr(self, 'from_project_id'):
            project = self.from_project_id or self.to_project_id
            project_id = project.id if project else False
        if not expense_id and hasattr(self, 'from_expense_head_id'):
            expense = self.from_expense_head_id or self.to_expense_head_id
            expense_id = expense.id if expense else False

        self.env['fund.approval.history'].sudo().create({
            'res_model': self._name,
            'res_id': self.id,
            'document_reference': self.name,
            'approval_level': level,
            'approver': self.env.user.id,
            'result': result,
            'comment': comment or 'No comment provided.',
            'previous_state': previous_state,
            'new_state': new_state,
            'amount': amount,
            'fund_account_id': account_id,
            'project_id': project_id,
            'expense_head_id': expense_id,
            'creator_id': self.create_uid.id,
            'submitted_by_id': self.requested_by.id,
            'currency_id': company.currency_id.id,
            'company_id': company.id,
        })

 

    def _activity_type_id(self):
       
        return self.env.ref('mail.mail_activity_data_todo').id

    def _schedule_activity(self, user_id, summary, note, date_deadline=None):
        
        if not self._is_mail_thread():
            return
        if date_deadline is None:
            date_deadline = fields.Date.today()
        self.activity_schedule(
            activity_type_id=self._activity_type_id(),
            summary=summary,
            note=note,
            user_id=user_id,
            date_deadline=date_deadline,
        )

    def _is_mail_thread(self):
       
        return hasattr(self, 'activity_ids')

    def _notify_requester(self, summary, note):
       
        self._schedule_activity(self.requested_by.id, summary, note)

    def _notify_approver(self, user, summary, note):
      
        if user:
            self._schedule_activity(user.id, summary, note)

    def _lock_records(self, records):
        records = records.exists()
        if not records:
            return
        ids = tuple(sorted(records.ids))
        self.env.cr.execute(
            'SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE' % records._table,
            [ids],
        )

    def _lock_submit_balance_source(self):
        pass

    def _check_current_user_is_requester_or_admin(self):
        self.ensure_one()
        if self.user_has_groups('nn_fund_management.group_fund_admin'):
            return
        if self.requested_by != self.env.user:
            raise UserError(_('Only the requester or a Fund Administrator can perform this action.'))

    def _check_write_allowed(self, vals, protected_fields):
        if self.env.context.get('fund_internal_write'):
            return
        if 'state' in vals:
            raise UserError(_('Status changes must use the workflow buttons.'))
        if 'requested_by' in vals and not self.user_has_groups('nn_fund_management.group_fund_admin'):
            raise UserError(_('Only Fund Administrators can change the requester.'))
        changed = set(vals) & set(protected_fields)
        if not changed:
            return
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    'You cannot modify financial fields after submission. Cancel and create a new request if values are wrong.'
                ))

    def _normalize_requested_by_vals(self, vals):
        if not self.user_has_groups('nn_fund_management.group_fund_admin') or not vals.get('requested_by'):
            vals['requested_by'] = self.env.user.id
        return vals

    

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec._check_current_user_is_requester_or_admin()
            rec._lock_submit_balance_source()
            rec._validate_submit()
            old_state = rec.state
            rec.with_context(fund_internal_write=True).state = 'submitted'
            rec._log_approval('submit', 'submitted', rec.approval_comment or '', old_state, 'submitted')

           
            config = rec._get_approval_config()
            doc_label = rec._description or rec._name
            rec._notify_approver(
                config.gm_approver_id,
                summary=_('Approval Required: %s') % rec.name,
                note=_(
                    '<b>%s</b> requires your GM approval.<br/>'
                    'Submitted by: %s<br/>Amount: %s'
                ) % (doc_label, rec.requested_by.name, getattr(rec, 'amount', '')),
            )

    def action_gm_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted records can be GM-approved.'))

            if not self.user_has_groups('nn_fund_management.group_gm_approver') and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only users in the GM Approver group can approve at this level.'))

            config = rec._get_approval_config()
            if self.env.user != config.gm_approver_id and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('You are not the assigned GM approver.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot approve your own request.'))

            old_state = rec.state
            rec._log_approval('gm', 'approved', rec.approval_comment or '', old_state, 'gm_approved')
            rec.approval_comment = False
            rec.with_context(fund_internal_write=True).state = 'gm_approved'

           
            rec._notify_approver(
                config.md_approver_id,
                summary=_('MD Approval Required: %s') % rec.name,
                note=_(
                    '<b>%s</b> has been GM-approved and now awaits your MD approval.<br/>'
                    'Requested by: %s'
                ) % (rec.name, rec.requested_by.name),
            )
           
            rec._notify_requester(
                summary=_('GM Approved: %s') % rec.name,
                note=_('Your request <b>%s</b> has been approved by the GM and is pending MD approval.') % rec.name,
            )

    def action_md_approve(self):
        for rec in self:
            if rec.state != 'gm_approved':
                raise UserError(_('GM approval must be completed before MD approval.'))

            if not self.user_has_groups('nn_fund_management.group_md_approver') and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only users in the MD Approver group can approve at this level.'))

            config = rec._get_approval_config()
            if self.env.user != config.md_approver_id and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('You are not the assigned MD approver.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot approve your own request.'))

            old_state = rec.state
            rec._log_approval('md', 'approved', rec.approval_comment or '', old_state, 'approved')
            rec.approval_comment = False
            rec.with_context(fund_internal_write=True).state = 'approved'
            rec._on_approved()

           
            rec._notify_requester(
                summary=_('Approved: %s') % rec.name,
                note=_('Your request <b>%s</b> has been fully approved (GM + MD).') % rec.name,
            )

    def action_reject(self):
        for rec in self:
            if rec.state not in ('submitted', 'gm_approved'):
                raise UserError(_('Only pending records can be rejected.'))

            config = rec._get_approval_config()
            if rec.state == 'submitted':
                level, approver = 'gm', config.gm_approver_id
                group_xmlid = 'nn_fund_management.group_gm_approver'
            else:
                level, approver = 'md', config.md_approver_id
                group_xmlid = 'nn_fund_management.group_md_approver'

            if not self.user_has_groups(group_xmlid) and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('You are not allowed to reject at this approval level.'))
            if self.env.user != approver and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only the current-level approver can reject.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot reject your own request.'))

            old_state = rec.state
            comment = rec.approval_comment or ''
            rec._log_approval(level, 'rejected', comment, old_state, 'rejected')
            rec.approval_comment = False
            rec.with_context(fund_internal_write=True).state = 'rejected'
            rec._on_rejected()

           
            level_label = _('GM') if level == 'gm' else _('MD')
            rec._notify_requester(
                summary=_('Rejected: %s') % rec.name,
                note=_(
                    'Your request <b>%s</b> was rejected at the <b>%s</b> level.<br/>'
                    'Comment: %s'
                ) % (rec.name, level_label, comment or _('No comment provided.')),
            )

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'submitted', 'gm_approved', 'approved'):
                raise UserError(_('Only draft, pending, or approved records can be cancelled.'))

            if rec.state == 'approved' and not self.user_has_groups('nn_fund_management.group_fund_admin'):
                raise UserError(_('Only Fund Administrators can cancel approved transactions.'))
            if rec.state != 'approved':
                rec._check_current_user_is_requester_or_admin()

            old_state = rec.state
            rec.with_context(fund_internal_write=True).state = 'cancelled'
            rec._log_approval('cancel', 'cancelled', rec.approval_comment or '', old_state, 'cancelled')
            rec._on_cancelled()

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancelled'):
                raise UserError(_('You cannot delete a record that has been submitted or approved. Cancel it instead.'))
        return super().unlink()

    

    def _validate_submit(self):
        pass

    def _on_approved(self):
        pass

    def _on_rejected(self):
        pass

    def _on_cancelled(self):
        pass




class FundApprovalConfig(models.Model):
    _name = 'fund.approval.config'
    _description = 'Fund Approval Configuration'

    name = fields.Char(string='Name', default='Approval Settings', required=True)
    min_amount = fields.Float(string='Min Amount', default=0.0)
    max_amount = fields.Float(string='Max Amount', default=0.0)
    gm_approver_id = fields.Many2one('res.users', string='GM Approver', required=True)
    md_approver_id = fields.Many2one('res.users', string='MD Approver', required=True)
    allow_self_approval = fields.Boolean(string='Allow Self Approval', default=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, required=True)

    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'Only one approval configuration per company is allowed.'),
        ('amount_range_check', 'CHECK(max_amount >= min_amount)', 'Maximum amount must be greater than or equal to minimum amount.'),
    ]

    @api.constrains('gm_approver_id', 'md_approver_id')
    def _check_approver_groups(self):
        for rec in self:
            if rec.gm_approver_id and not rec.gm_approver_id.has_group('nn_fund_management.group_gm_approver'):
                raise ValidationError(_('The GM approver must belong to the GM Approver group.'))
            if rec.md_approver_id and not rec.md_approver_id.has_group('nn_fund_management.group_md_approver'):
                raise ValidationError(_('The MD approver must belong to the MD Approver group.'))


class FundApprovalHistory(models.Model):
    _name = 'fund.approval.history'
    _description = 'Fund Audit History'
    _order = 'date desc'

    res_model = fields.Char(string='Document Model', required=True)
    res_id = fields.Integer(string='Document ID', required=True)
    document_reference = fields.Char(string='Reference Document')

    approval_level = fields.Selection([
        ('submit', 'Submitted'),
        ('confirm', 'Confirmed'),
        ('gm', 'General Manager'),
        ('md', 'Managing Director'),
        ('post', 'Posted'),
        ('pay', 'Paid'),
        ('close', 'Closed'),
        ('reopen', 'Reopened'),
        ('cancel', 'Cancelled'),
    ], string='Action Level')

    approver = fields.Many2one('res.users', string='Action By')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    result = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ], string='Result')

    comment = fields.Text(string='Comment')
    previous_state = fields.Char(string='Previous Status')
    new_state = fields.Char(string='New Status')

    amount = fields.Float(string='Amount')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id,
    )
    fund_account_id = fields.Many2one('fund.account', string='Fund Account')
    project_id = fields.Many2one('fund.project', string='Project')
    expense_head_id = fields.Many2one('fund.expense.head', string='Expense Head')

    creator_id = fields.Many2one('res.users', string='Record Creator')
    submitted_by_id = fields.Many2one('res.users', string='Submitted By')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
