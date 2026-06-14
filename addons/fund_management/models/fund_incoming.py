from odoo import models, fields,api
class FundIncoming(models.Model):
    _name = 'fund.incoming'
    _description = 'Fund Incoming'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(
    default='New',
    readonly=True,
    copy=False
)
    fund_account_id = fields.Many2one('fund.account', string='Fund Account', required=True)
   date = fields.Date(
        default=fields.Date.today
    )
    amount = fields.Float(string='Amount', required=True)
    transaction_reference = fields.Char(string='Transaction Reference', required=True)
    source = fields.Char(string='Source', required=True)
    description = fields.Text(string='Detailed Description')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Filename')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company.id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.incoming') or 'New'
        return super(FundIncoming, self).create(vals)


    def action_confirm(self):
     for rec in self:

            if rec.state != 'draft':
                continue

        rec.state = 'confirmed'


        def action_cancel(self):
            for rec in self:
                rec.state = 'rejected'


        _sql_constraints = [
        ('transaction_reference_unique', 
        'unique(transaction_reference)', 
        'Transaction Reference must be unique.'),


    ]
