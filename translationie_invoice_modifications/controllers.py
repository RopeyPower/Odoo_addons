# -*- coding: utf-8 -*-
from openerp import http

# class TranslationieInvoiceModifications(http.Controller):
#     @http.route('/translationie_invoice_modifications/translationie_invoice_modifications/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/translationie_invoice_modifications/translationie_invoice_modifications/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('translationie_invoice_modifications.listing', {
#             'root': '/translationie_invoice_modifications/translationie_invoice_modifications',
#             'objects': http.request.env['translationie_invoice_modifications.translationie_invoice_modifications'].search([]),
#         })

#     @http.route('/translationie_invoice_modifications/translationie_invoice_modifications/objects/<model("translationie_invoice_modifications.translationie_invoice_modifications"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('translationie_invoice_modifications.object', {
#             'object': obj
#         })