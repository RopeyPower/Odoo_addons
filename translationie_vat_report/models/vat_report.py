# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class TranslationieVatReport(models.TransientModel):
	_name = 'vat.report'
	
	currency_id = fields.Many2one('res.currency', string='Currency')
	
	t1_items = fields.Many2many(comodel_name='account.move.line',relation='t1_items_rel')
	t1_amount = fields.Monetary()
	
	t2_items = fields.Many2many(comodel_name='account.move.line',relation='t2_items_rel')
	t2_amount = fields.Monetary()
	
	t3_amount = fields.Monetary()
	t4_amount = fields.Monetary()
	
	es1_items = fields.Many2many(comodel_name='account.move.line',relation='es1_items_rel')
	es1_amount = fields.Monetary()
	
	es2_items = fields.Many2many(comodel_name='account.move.line',relation='es2_items_rel')
	es2_amount = fields.Monetary()
	
	@api.multi
	def open_journal_items(self, items):
		try:
			all = self.env['vat.report'].browse([])
			_logger.debug("all items: " + str(all) + " self: " + str(self.id))
			_logger.debug("in open journal items: " + str(items))
			action = self.env.ref('account.action_account_moves_all_tree')
			# test = self.env['account.move.line'].browse(1689)
			vals = action.read()[0]
			# t1 = self.env.context.get('t1_items')
			# _logger.debug("items from context: " + str(t1))
			vals['context'] = {}
			vals['domain'] = [('id','in',items.ids)]
			return vals
		except Exception:
			_logger.error("error opening record", exc_info=True)
		# journal_treeview = self.env.ref('account.view_move_line_tree')
		# _logger.debug("treeview: " + str(journal_treeview))
		# return {
			# 'name': 'Open VAT items',
			# 'view_type': 'form',
			# 'view_mode': 'tree,form',
			# 'res_model': 'vat.report',
			# 'views': [(journal_treeview.id, 'tree')],
			# 'target': 'current',
			# 'domain': [('id','=',items[0].id)],
		# }
	
	@api.multi
	def view_t1_items(self):
		try:
			_logger.debug("opening t1_items: " + str(self.t1_items))
			return self.open_journal_items(self.t1_items)
		except Exception:
			_logger.error("error opening t1 items", exc_info=True)
	
	@api.multi
	def view_t2_items(self):
		_logger.debug("opening t2 items: " + str(self.t2_items))
		return self.open_journal_items(self.t2_items)
	
	@api.multi
	def view_es1_items(self):
		return self.open_journal_items(self.es1_items)
	
	@api.multi
	def view_es2_items(self):
		return self.open_journal_items(self.es2_items)


class AccountTax(models.Model):
	_inherit = 'account.tax'
	
	is_vat = fields.Boolean(string="Is VAT", help="This tax is a value added tax (VAT) and will be considered while generating the VAT3 report")