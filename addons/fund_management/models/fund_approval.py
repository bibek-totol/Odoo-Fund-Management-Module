from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
        config = Config.search([('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            config = Config.search([], limit=1)
        if not config:
            raise UserError(_('No approval configuration found. Please create one.'))
        return config

    def _log_approval(self, level, result, comment='', previous_state='', new_state=''):
       
        self.ensure_all()
        amount = self.amount if hasattr(self, 'amount') else 0.0
        account_id = self.fund_account_id.id if hasattr(self, 'fund_account_id') and self.fund_account_id else False
        project_id = self.project_id.id if hasattr(self, 'project_id') and self.project_id else False
        expense_id = self.expense_head_id.id if hasattr(self, 'expense_head_id') and self.expense_head_id else False

        self.env['fund.approval.history'].create({
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
        })

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec._validate_submit()
            old_state = rec.state
            rec.state = 'submitted'
            rec._log_approval('submit', 'submitted', rec.approval_comment or '', old_state, 'submitted')

    def action_gm_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted records can be GM-approved.'))
            
           
            if not self.user_has_groups('fund_management.group_gm_approver') and not self.user_has_groups('fund_management.group_fund_admin'):
                raise UserError(_('Only users in the GM Approver group can approve at this level.'))

            config = rec._get_approval_config()
            if self.env.user != config.gm_approver_id and not self.user_has_groups('fund_management.group_fund_admin'):
                raise UserError(_('You are not the assigned GM approver.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot approve your own request.'))

            old_state = rec.state
            rec._log_approval('gm', 'approved', rec.approval_comment or '', old_state, 'gm_approved')
            rec.approval_comment = False
            rec.state = 'gm_approved'

    def action_md_approve(self):
        for rec in self:
            if rec.state != 'gm_approved':
                raise UserError(_('GM approval must be completed before MD approval.'))
            
           
            if not self.user_has_groups('fund_management.group_md_approver') and not self.user_has_groups('fund_management.group_fund_admin'):
                raise UserError(_('Only users in the MD Approver group can approve at this level.'))

            config = rec._get_approval_config()
            if self.env.user != config.md_approver_id and not self.user_has_groups('fund_management.group_fund_admin'):
                raise UserError(_('You are not the assigned MD approver.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot approve your own request.'))

            old_state = rec.state
            rec._log_approval('md', 'approved', rec.approval_comment or '', old_state, 'approved')
            rec.approval_comment = False
            rec.state = 'approved'
            rec._on_approved()

    def action_reject(self):
        for rec in self:
            if rec.state not in ('submitted', 'gm_approved'):
                raise UserError(_('Only pending records can be rejected.'))
            
            config = rec._get_approval_config()
            if rec.state == 'submitted':
                level, approver = 'gm', config.gm_approver_id
            else:
                level, approver = 'md', config.md_approver_id

            if self.env.user != approver and not self.user_has_groups('fund_management.group_fund_admin'):
                raise UserError(_('Only the current-level approver can reject.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot reject your own request.'))

            old_state = rec.state
            rec._log_approval(level, 'rejected', rec.approval_comment or '', old_state, 'rejected')
            rec.approval_comment = False
            rec.state = 'rejected'
            rec._on_rejected()

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'submitted', 'gm_approved', 'approved'):
                raise UserError(_('Only draft, pending, or approved records can be cancelled.'))
            
           
            if rec.state == 'approved' and not self.user_has_groups('fund_management.group_fund_admin'):
                raise UserError(_('Only Fund Administrators can cancel approved transactions.'))
            
            old_state = rec.state
            rec.state = 'cancelled'
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
    gm_approver_id = fields.Many2one('res.users', string='GM Approver', required=True)
    md_approver_id = fields.Many2one('res.users', string='MD Approver', required=True)
    allow_self_approval = fields.Boolean(string='Allow Self Approval', default=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, required=True)

    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'Only one approval configuration per company is allowed.'),
    ]


class FundApprovalHistory(models.Model):
    _name = 'fund.approval.history'
    _description = 'Fund Audit History'
    _order = 'date desc'

    res_model = fields.Char(string='Document Model', required=True)
    res_id = fields.Integer(string='Document ID', required=True)
    document_reference = fields.Char(string='Reference Document')

    approval_level = fields.Selection([
        ('submit', 'Submitted'),
        ('gm', 'General Manager'),
        ('md', 'Managing Director'),
        ('cancel', 'Cancelled'),
    ], string='Action Level')
    
    approver = fields.Many2one('res.users', string='Action By')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    result = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Result')
    
    comment = fields.Text(string='Comment')
    previous_state = fields.Char(string='Previous Status')
    new_state = fields.Char(string='New Status')
    
   
    amount = fields.Float(string='Amount')
    fund_account_id = fields.Many2one('fund.account', string='Fund Account')
    project_id = fields.Many2one('fund.project', string='Project')
    expense_head_id = fields.Many2one('fund.expense.head', string='Expense Head')
    
    creator_id = fields.Many2one('res.users', string='Record Creator')
    submitted_by_id = fields.Many2one('res.users', string='Submitted By')