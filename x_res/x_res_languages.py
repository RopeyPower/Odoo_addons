# -*- coding: utf-8 -*-

from openerp import models, fields, api

class x_res_languages(models.Model):
	_name = 'x_res.languages'
	_description = 'Translation Languages'
	
	x_name = fields.Char(string='Name', ondelete='set null')
	x_code = fields.Char(string='Language Code', ondelete='set null')
	x_group = fields.Selection([('group1','1'),('group2','2'),('group3','3'),('group4','4')], string='Language Group', ondelete='set null')
	x_minimum = fields.Float(string='Minimum Charge', ondelete='set null')
	x_minimum_urgency = fields.Float(string='Minimum Urgency Charge', ondelete='set null')#
	x_standard = fields.Float(string='Standard Rate', ondelete='set null')

