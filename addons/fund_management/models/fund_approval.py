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

    approval_comment = fields.Text(
        string='Comment', copy=False,
        help='Enter a comment before approving or rejecting.',
    )

    
    approval_history_ids = fields.One2many(
        'fund.approval.history',
        compute='_compute_approval_history',
        string='Approval History',
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
        config = Config.search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not config:
            config = Config.search([], limit=1)
        if not config:
            raise UserError(_(
                'No approval configuration found.'
                'Please create one in Configuration → Approval Settings.'
            ))
        return config

   
    def _log_approval(self, level, result, comment=''):
        self.env['fund.approval.history'].create({
            'res_model': self._name,
            'res_id': self.id,
            'approval_level': level,
            'approver': self.env.user.id,
            'result': result,
            'comment': comment or 'No comment provided.',
        })

    

    def action_submit(self):
      
        for rec in self:
            if rec.state != 'draft':
                continue
            rec._validate_submit()        
            rec.state = 'submitted'

    def action_gm_approve(self):
       
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted records can be GM-approved.'))

            config = rec._get_approval_config()
            if self.env.user != config.gm_approver_id:
                raise UserError(_('Only the configured GM approver can approve at this level.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot approve your own request.'))

            rec._log_approval('gm', 'approved', rec.approval_comment or '')
            rec.approval_comment = False
            rec.state = 'gm_approved'

    def action_md_approve(self):
      
        for rec in self:
            if rec.state != 'gm_approved':
                raise UserError(_('GM approval must be completed before MD approval.'))

            config = rec._get_approval_config()
            if self.env.user != config.md_approver_id:
                raise UserError(_('Only the configured MD approver can approve at this level.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot approve your own request.'))

            rec._log_approval('md', 'approved', rec.approval_comment or '')
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

            if self.env.user != approver:
                raise UserError(_('Only the current-level approver can reject.'))
            if not config.allow_self_approval and rec.requested_by == self.env.user:
                raise UserError(_('You cannot reject your own request.'))

            rec._log_approval(level, 'rejected', rec.approval_comment or '')
            rec.approval_comment = False
            rec.state = 'rejected'
            rec._on_rejected()             

    def action_cancel(self):
      
        for rec in self:
            if rec.state not in ('draft', 'submitted', 'gm_approved'):
                raise UserError(_('Only draft or pending records can be cancelled.'))
            rec.state = 'cancelled'
            rec._on_cancelled()            


    def _validate_submit(self):
        """Override to check that enough money is available."""
        pass

    def _on_approved(self):
        """Override to perform actions when fully approved."""
        pass

    def _on_rejected(self):
        """Override to release holds if needed."""
        pass

    def _on_cancelled(self):
        """Override to release holds if needed."""
        pass



class FundApprovalConfig(models.Model):
    
    _name = 'fund.approval.config'
    _description = 'Fund Approval Configuration'

    name = fields.Char(string='Name', default='Approval Settings', required=True)
    gm_approver_id = fields.Many2one('res.users', string='GM Approver', required=True)
    md_approver_id = fields.Many2one('res.users', string='MD Approver', required=True)
    allow_self_approval = fields.Boolean(
        string='Allow Self Approval',
        default=False,
        help='Check this to allow users to approve their own requests.',
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company.id, required=True,
    )

    _sql_constraints = [
        ('company_unique', 'unique(company_id)',
         'Only one approval configuration per company is allowed.'),
    ]



class FundApprovalHistory(models.Model):

    _name = 'fund.approval.history'
    _description = 'Fund Approval History'
    _order = 'date desc'

    res_model = fields.Char(string='Document Model', required=True)
    res_id = fields.Integer(string='Document ID', required=True)

    approval_level = fields.Selection([
        ('gm', 'General Manager'),
        ('md', 'Managing Director'),
    ], string='Approval Level')

    approver = fields.Many2one('res.users', string='Approver')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    result = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Result')
    comment = fields.Text(string='Comment')