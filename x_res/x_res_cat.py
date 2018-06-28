# -*- coding: utf-8 -*-

from openerp import models, fields, api

class x_res_cat(models.Model):
	_name = 'x_res.cat'
	_description = 'List of Cat Tools'
	
	x_description = fields.Text(string='Description', ondelete='set null')
	x_name = fields.Char(string='Name', ondelete='set null')
	x_package = fields.Selection([('omegaT','OmegaT'),('Trados7','Optimised BiLingual TRADOS RTF'),('Trados09','RTF (list view)'),('Xliff','Xliff 1.2'),('TradosTTX','Trados 7 TTX')],string='Globalsight Package', ondelete='set null')

