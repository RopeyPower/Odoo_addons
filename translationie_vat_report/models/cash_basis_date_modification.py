# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountPartialReconcileCashBasis(models.Model):
	_inherit = 'account.partial.reconcile'
	
	def create_tax_cash_basis_entry(self, value_before_reconciliation):
		try:
			#Search in account_move if we have any taxes account move lines
			tax_group = {}
			tax_group_lines = {}
			tax_group_date = {}
			total_by_cash_basis_account = {}
			cash_basis_date = {}
			for move in (self.debit_move_id.move_id, self.credit_move_id.move_id):
				_logger.debug("Tax Group: " + str(tax_group) + "Tax Group Date: " + str(tax_group_date))
				for line in move.line_ids:
					_logger.debug("tax_ids: " + str(line.tax_ids))
					if line.tax_line_id and line.tax_line_id.use_cash_basis:
						#amount to write is the current cash_basis amount minus the one before the reconciliation
						matched_percentage = value_before_reconciliation[move.id]
						amount = (line.credit_cash_basis - line.debit_cash_basis) - (line.credit - line.debit) * matched_percentage
						#group by line account
						acc = line.account_id.id
						if tax_group.get(acc, False):
							tax_group[acc] += amount
						else:
							tax_group[acc] = amount
						
						if tax_group_lines.get(acc, False):
							tax_group_lines[acc].append(line)
						else:
							tax_group_lines[acc] = [line]
						#get line due date (which should be the date the money was received for cash based vat)
						if len(line.invoice_id.payment_ids) > 1:
							date = line.invoice_id.payment_ids[0].payment_date
						else:
							date = line.invoice_id.payment_ids.payment_date
						tax_group_date[acc] = date
						_logger.debug("tax_group_date; " + str(line.date_maturity) + " date: " + str(line.date) + " acc: " + str(acc) + " payment date: " + str(date) + " tax_ids: " + str(line.tax_ids))
						_logger.debug("partner: " + str(line.partner_id.name) + " id: " + str(line.partner_id))
						#Group by cash basis account
						acc = line.tax_line_id.cash_basis_account.id
						if total_by_cash_basis_account.get(acc, False):
							total_by_cash_basis_account[acc] += amount
						else:
							total_by_cash_basis_account[acc] = amount
						cash_basis_date[acc] = date
						if tax_group_lines.get(acc, False):
							tax_group_lines[acc].append(line)
						else:
							tax_group_lines[acc] = [line]
			
			line_to_create = []
			_logger.debug("tax_group_items: " + str(tax_group.items()))
			_logger.debug("tax group lines: " + str(tax_group_lines.items()))
			for k,v in tax_group.items():
				line = tax_group_lines[k][0]
				_logger.debug("move name; " + str(line.move_id.name) + " line name: " + str(line.name))
				line_to_create.append((0, 0, {
					'name': line.move_id.name,
					'debit': v if v > 0 else 0.0,
					'credit': abs(v) if v < 0 else 0.0,
					'account_id': k,
					'date_maturity': tax_group_date[k],
					'date': tax_group_date[k],
					'partner_id': line.partner_id.id,
					}))

			#Create counterpart vals
			for k,v in total_by_cash_basis_account.items():
				line = tax_group_lines[k][0]
				_logger.debug("move name; " + str(line.move_id.name) + " line name: " + str(line.name))
				line_to_create.append((0, 0, {
					'name': line.name,
					'debit': abs(v) if v < 0 else 0.0,
					'credit': v if v > 0 else 0.0,
					'account_id': k,
					'date_maturity': cash_basis_date[k],
					'date': cash_basis_date[k],
					'partner_id': line.partner_id.id,
					}))

			#Create move
			if len(line_to_create) > 0:
				#Check if company_journal for cash basis is set if not, raise exception
				if not self.company_id.tax_cash_basis_journal_id:
					raise UserError(_('There is no tax cash basis journal defined ' \
										'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') % \
										  (self.company_id.name))
				move = self.env['account.move'].create({
					'journal_id': self.company_id.tax_cash_basis_journal_id.id,
					'line_ids': line_to_create,
					'tax_cash_basis_rec_id': self.id,
					'ref': self.credit_move_id.move_id.name if self.credit_move_id.payment_id else self.debit_move_id.move_id.name})
				#post move
				move.post()
		except Exception:
			_logger.error("error generating cach basis move", exc_info=True)
			