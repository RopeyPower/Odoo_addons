# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class res_company_invoice_mod(models.Model):
	_inherit = "res.company"
	
	tax_clearance_code = fields.Char(string="Tax Clearance Access Number")