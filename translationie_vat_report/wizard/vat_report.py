# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class TranslationieVatReportWizard(models.TransientModel):
	_name = 'wizard.vat.report'
	company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)
	from_date = fields.Date('From date', required=True)
	to_date = fields.Date('To date', required=True)
	
	@api.multi
	def report_vat(self):
		try:
			if not self.company_id.tax_cash_basis_journal_id:
				raise UserError(_('There is no tax cash basis journal defined ' \
										'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') % \
										(self.company_id.name))
			cash_basis_journal = self.company_id.tax_cash_basis_journal_id
			sales_taxes = self.env['account.tax'].search([('type_tax_use','=','sale'),('is_vat','=',True)])
			purchase_taxes = self.env['account.tax'].search([('type_tax_use','=','purchase'),('is_vat','=',True)])
			for tax in sales_taxes:
				if tax.use_cash_basis:
					cash_basis_acc = tax.cash_basis_account
					_logger.debug("journal: " + str(cash_basis_journal.name) + " acc: " + str(cash_basis_acc.name))
					t1_items, t1_amount = self.get_vat_items(cash_basis_journal, cash_basis_acc, 'T1', self.company_id)
					_logger.debug("sales vat items: " + str(t1_items))
			
			for tax in purchase_taxes:
				if tax.use_cash_basis:
					cash_basis_acc = tax.cash_basis_account
					t2_items, t2_amount = self.get_vat_items(cash_basis_journal, cash_basis_acc, 'T2', self.company_id)
			
			t3_amount = 0
			t4_amount = 0
			
			if t1_amount - t2_amount > 0:
				t3_amount = t1_amount - t2_amount
			elif t2_amount - t1_amount > 0:
				t4_amount = t2_amount - t1_amount
			_logger.debug("t1: " + str(t1_amount) + " t2: " + str(t2_amount) + " t3: " + str(t3_amount) + " t4: " + str(t4_amount))
			
			es1_items, es1_amount = self.get_eu_service_items('es1')
			es2_items, es2_amount = self.get_eu_service_items('es2')
			
			data = {
				't1_amount': t1_amount,
				't2_amount': t2_amount,
				't3_amount': t3_amount,
				't4_amount': t4_amount,
				'es1_amount': es1_amount,
				'es2_amount': es2_amount,
			}
			
			if t1_items:
				data['t1_items'] = [(4, [item.id for item in t1_items])]
			if t2_items:
				data['t2_items'] = [(4, [item.id for item in t2_items])]
			
			if es1_items:
				_logger.debug("adding es1_items: " + str(es1_items))
				data['es1_items'] = [(4, [item.id for item in es1_items])]
			if es2_items:
				_logger.debug("adding es2_items: " + str(es2_items))
				data['es2_items'] = [(4, [item.id for item in es2_items])]
			_logger.debug("t1 items: " + str(t1_items) + " ids: " + str(t1_items.ids))
			_logger.debug("t2 items: " + str(t2_items) + " ids: " + str(t2_items.ids))
			
			vat_report_obj = self.env['vat.report'].create(data)
			# vat_report_obj.t2_items = [(6,0,t2_items.ids)]
			_logger.debug("obj t1_items: " + str(vat_report_obj.t1_items))
			_logger.debug("obj t2 items: " + str(vat_report_obj.t2_items) + " t2_items: " + str(t2_items))
			treeview_id = self.env.ref('translationie_vat_report.view_vat_report')
			# context = {'t1_items':t1_items, 't2_items':t2_items, 'es1_items': es1_items, 'es2_items': es2_items}
			return {
				'name': 'VAT Report View',
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'vat.report',
				'views': [(treeview_id.id, 'tree')],
				'target': 'current',
				'domain': [('id','=',vat_report_obj.id)],
				# 'context': context,
			}
			
		except Exception:
			_logger.error("error reporting vat", exc_info=True)
	
	def get_vat_items(self, cash_basis_journal, cash_basis_acc, tax_code, company):
		_logger.debug("from: " + str(self.from_date) + " to: " + str(self.to_date))
		vat_items = self.env['account.move.line'].search([('journal_id','=',cash_basis_journal.id),('account_id','=',cash_basis_acc.id),('company_id','=',company.id),('date','>=',self.from_date),('date','<=',self.to_date)])
		amount = 0
		if tax_code == 'T1':
			for item in vat_items:
				_logger.debug("t1 item name: " + str(item.name) + ' ' + str(item.balance) + ' id ' + str(item.id))
				amount += item.credit_cash_basis - item.debit_cash_basis
		elif tax_code == 'T2':
			for item in vat_items:
				_logger.debug("t2 item name: " + str(item.name) + ' ' + str(item.balance) + ' id ' + str(item.id))
				amount += item.debit_cash_basis - item.credit_cash_basis
		
		return vat_items, amount
	
	def get_eu_service_items(self, code):
		all_period_journal_items = self.env['account.move.line'].search([('date','>=',self.from_date),('date','<=',self.to_date)])
		eu_partners = []
		fiscal_position = ''
		if code == 'es1':
			fiscal_position = 'EU Fiscal Position'
		elif code == 'es2':
			fiscal_position = 'Vat Registered Vendor'
		for item in all_period_journal_items:
			if item.partner_id.property_account_position_id.name == fiscal_position and item.partner_id.vat:
				eu_partners.append(item.partner_id)
		
		eu_items = None
		amount = 0
		for partner in list(set(eu_partners)):
			_logger.debug("customer id is: " + str(partner))
			paid_period_items = self.env['account.move.line'].search([('partner_id','=',partner.id),('date','>=',self.from_date),('date','<=',self.to_date),('account_id','=',partner.property_account_receivable_id.id),('payment_id','!=',False)])
			# _logger.debug("customer: " + str(partner.name) + " items: " + str(paid_period_items) + " name: " + str(paid_period_items[0].name) + " acc: " + str(partner.property_account_receivable_id))
			eu_items = paid_period_items
			
		if eu_items:
			for item in eu_items:
				_logger.debug("id: " + str(item.id) + " balance: " + str(item.balance) + " balance cash basis: " + str(item.balance_cash_basis))
				amount += abs(item.balance_cash_basis)
		
		return eu_items, amount
		
				