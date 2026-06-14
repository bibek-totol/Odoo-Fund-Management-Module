# from odoo import models, fields, api


# class fund_management(models.Model):
#     _name = 'fund_management.fund_management'
#     _description = 'fund_management.fund_management'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

