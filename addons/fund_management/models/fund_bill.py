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
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.bill') or 'New'
        return super().create(vals)

    @api.constrains('requisition_id', 'project_id', 'expense_head_id')
    def _check_requisition_match(self):
        
        for rec in self:
            if rec.requisition_id.project_id and rec.project_id != rec.requisition_id.project_id:
                raise ValidationError(_("Project does not match the requisition's project."))
            if rec.requisition_id.expense_head_id and rec.expense_head_id != rec.requisition_id.expense_head_id:
                raise ValidationError(_("Expense Head does not match the requisition's expense head."))

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            if rec.requisition_id.state != 'approved':
                raise UserError(_('Requisition must be approved to post bills.'))

          
            other_billed = sum(
                rec.requisition_id.bill_ids.filtered(
                    lambda b: b.state == 'confirmed' and b.id != rec.id
                ).mapped('amount')
            )
            if other_billed + rec.amount > rec.requisition_id.amount:
                raise UserError(_(
                    'Total billed (%s) would exceed requisition amount (%s).'
                ) % (other_billed + rec.amount, rec.requisition_id.amount))

            rec.state = 'confirmed'



               
    
    def action_cancel(self):
        for rec in self:
            if rec.state == 'confirmed' and rec.requisition_id.state == 'closed':
                raise UserError(_('You cannot cancel a bill against a closed requisition. Reopen the requisition first.'))
            rec.state = 'cancelled'

   
    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('You cannot delete a confirmed bill. Cancel it instead.'))
        return super().unlink()