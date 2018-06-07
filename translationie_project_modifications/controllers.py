# -*- coding: utf-8 -*-
from openerp import http

# class TranslationieProjectModifications(http.Controller):
#     @http.route('/translationie_project_modifications/translationie_project_modifications/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/translationie_project_modifications/translationie_project_modifications/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('translationie_project_modifications.listing', {
#             'root': '/translationie_project_modifications/translationie_project_modifications',
#             'objects': http.request.env['translationie_project_modifications.translationie_project_modifications'].search([]),
#         })

#     @http.route('/translationie_project_modifications/translationie_project_modifications/objects/<model("translationie_project_modifications.translationie_project_modifications"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('translationie_project_modifications.object', {
#             'object': obj
#         })