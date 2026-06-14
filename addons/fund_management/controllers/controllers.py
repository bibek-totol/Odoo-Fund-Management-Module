# from odoo import http


# class FundManagement(http.Controller):
#     @http.route('/fund_management/fund_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fund_management/fund_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('fund_management.listing', {
#             'root': '/fund_management/fund_management',
#             'objects': http.request.env['fund_management.fund_management'].search([]),
#         })

#     @http.route('/fund_management/fund_management/objects/<model("fund_management.fund_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fund_management.object', {
#             'object': obj
#         })

