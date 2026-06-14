from odoo import models, fields,api 
class FundAccount(models.Model):
    _name = 'fund.account'
    _description = 'Fund Account'

    name = fields.Char(string='Account Name', required=True)
    account_type = fields.Selection([
        ('bank', 'Bank Account'),
        ('cash', 'Cash Account'),
        ('other', 'Other Account'),
    ], string='Account Type', required=True)


    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company.id)
    incoming_funds = fields.One2many('fund.incoming', 'fund_account_id', string='Incoming Funds')
    account_number = fields.Char(string='Account Number', required=True)
    total_received = fields.Float(string='Total Received', compute='_compute_total_received')
   available_balance = fields.Float(string='Available Balance', compute='_compute_available_balance')
   held_balance = fields.Float(string='Held Balance', compute='_compute_held_balance')
   assigned_balance = fields.Float(string='Assigned Balance', compute='_compute_assigned_balance')

 

  @api.depends('incoming_funds.amount', 'incoming_funds.state')
  
    def _compute_total_received(self):
        for account in self:
            total = sum(account.incoming_funds.filtered.(lambda f:f.state == 'confirmed'). mapped('amount'))
            account.total_received = total

     def _compute_available_balance(self):
        for account in self:
            available = account.total_received - account.held_balance - account.assigned_balance
            account.available_balance = available

    def _compute_held_balance(self):
        for account in self:
            held = sum(account.incoming_funds.filtered(lambda f: f.state == 'held').mapped('amount'))
            account.held_balance = held

    def _compute_assigned_balance(self):
        for account in self:
            assigned = sum(account.incoming_funds.filtered(lambda f: f.state == 'assigned').mapped('amount'))
            account.assigned_balance = assigned

    



