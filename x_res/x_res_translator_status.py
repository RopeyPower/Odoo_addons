# -*- coding: utf-8 -*-

from openerp import models, fields, api

class x_res_translator_status(models.Model):
	_name = 'x_res.translator_status'
	_description = 'Translator Status'
	
	x_name = fields.Selection([('good','Green'),('acceptable','Yellow'),('poor','Amber'),('unavailable','Pink'),('blacklist','Red'),('unused','Grey')], string='Status', ondelete='set null')
	x_description = fields.Text(string='Description', ondelete='set null')

