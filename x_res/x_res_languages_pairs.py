# -*- coding: utf-8 -*-

from openerp import models, fields, api

class x_res_languages_pairs(models.Model):
	_name = 'x_res.languages.pairs'
	_description = 'Language Pairs'
	
	x_from = fields.Many2one(comodel_name='x_res.languages', string='From', ondelete='set null')
	x_to = fields.Many2one(comodel_name='x_res.languages', string='To', ondelete='set null')
	x_translator = fields.Many2one(comodel_name='res.partner', string='Translators with this language pair', ondelete='set null')

