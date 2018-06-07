# -*- coding: utf-8 -*-

from openerp import models, fields, api

class translationie_invoice_modifications(models.Model):
	_inherit = 'account.invoice.line'
	_name = 'account.invoice.line'
	
	x_source = fields.Many2one(comodel_name='x_res.languages', string='Source', ondelete='set null')
	x_target = fields.Many2one(comodel_name='x_res.languages', string='Target', ondelete='set null')
	x_vat_amount = fields.Monetary(string='VAT Amount', compute='invoice_compute_vat_numerical_amnt', ondelete='set null')
	
	def invoice_compute_vat_numerical_amnt(self):
		for line in self:
			if line.invoice_line_tax_ids:
				tax_percent = line.invoice_line_tax_ids.amount / 100
				tax_amount = line.price_subtotal * tax_percent
				line.x_vat_amount = format(tax_amount, '.2f')

class translationie_account_invoice_modifications(models.Model):
	_inherit = 'account.invoice'
	_name = 'account.invoice'
	
	x_po_num = fields.Char(string='PO Number', ondelete='set null')
	
	@api.multi
	def set_status_open(self):
		for rec in self:
			rec.residual = rec.amount_total
			if rec.reconciled:
				rec.reconciled = False
			if rec.state == 'paid':
				rec.state = 'open'
				
	@api.multi
	def set_status_closed(self):
		for rec in self:
			if rec.reconciled:
				rec.state = 'paid'
	
	@api.multi
	def set_bank_account(self):
		for rec in self:
			try:
				if not rec.partner_bank_id:
					partner_bank = rec.partner_id.bank_ids[0]
					rec.partner_bank_id = partner_bank.id
			except Exception:
				partner_bank = rec.partner_id.bank_ids[0]
				rec.partner_bank_id = partner_bank.id