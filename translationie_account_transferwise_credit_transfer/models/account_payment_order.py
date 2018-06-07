# -*- coding: utf-8 -*-

from openerp import models, api, fields, _
from openerp.exceptions import UserError
from lxml import etree
import itertools
import logging

_logger = logging.getLogger(__name__)

class TransferwisePartnerMod(models.Model):
	_inherit = 'res.partner'
	
	x_transferwise_recipient_id = fields.Char(string='Transferwise Recipient ID')
	
	x_target_currency_code = fields.Char(string='Target Currency Code', help="Currency code for the currency the vendor is paid in.")
	
	x_transferwise_payee = fields.Boolean(string='Transferwise Payee')
	
	x_paypal_account = fields.Char(string='Paypal Account Email')
	
	x_paypal_payee = fields.Boolean(string='Paypal Payee')
	
	@api.onchange('supplier_payment_mode_id')
	def onchange_payment_mode(self):
		if self.supplier_payment_mode_id.payment_method_id.code == 'transferwise_credit_transfer':
			self.x_transferwise_payee = True
			self.x_paypal_payee = False
		elif self.supplier_payment_mode_id.payment_method_id.code == 'paypal_credit_transfer':
			self.x_paypal_payee = True
			self.x_transferwise_payee = False
		else:
			self.x_transferwise_payee = False
			self.x_paypal_payee = False

class AccountPaymentOrder(models.Model):
	_inherit = 'account.payment.order'
	
	@api.multi
	def generate_payment_file(self):
		try:
			self.ensure_one()
			if self.payment_method_id.code == 'sepa_credit_transfer':
				_logger.debug("creating SEPA file")
				return super(AccountPaymentOrder, self).generate_payment_file()
			elif self.payment_method_id.code == 'transferwise_credit_transfer':
				return self.generate_transferwise_file()
			elif self.payment_method_id.code == 'paypal_credit_transfer':
				return self.generate_paypal_file()
			else:
				return super(AccountPaymentOrder, self).generate_payment_file()
		except Exception:
			_logger.debug("error creating payment file", exc_info=True)
			
	def generate_transferwise_file(self):
		source_currency = "EUR"
		payment_ref = "translationie"
		
		csv_file = "recipientId,name,account,sourceCurrency,targetCurrency,amountCurrency,amount,paymentReference\r\n"
		try:
			for line in self.bank_line_ids:
				recipient_id = str(line.partner_id.x_transferwise_recipient_id)
				target_currency = str(line.partner_id.x_target_currency_code)
				
				amount = str(line.amount_currency)
				recipient_name = line.partner_id.name
				
				csv_file += recipient_id + ',' + recipient_name + ',' + ',' + source_currency + ',' + target_currency + ',' + source_currency + ',' + amount + ',' + payment_ref + "\r\n"
			
			file_prefix = "Transferwise_"
			filename = '%s%s.csv' % (file_prefix, self.name)
			
			return (csv_file, filename)
		except:
			_logger.debug("error creating transferwise csv file", exc_info=True)
	
	def generate_paypal_file(self):
		csv_file = ""
		try:
			for line in self.bank_line_ids:
				paypal_account = str(line.partner_id.x_paypal_account)
				target_currency = str(line.partner_id.x_target_currency_code)
				amount = str(line.amount_currency)
				
				csv_file += paypal_account + ',' + amount + ',' + target_currency + "\r\n"
			
			file_prefix = "Paypal_"
			filename = '%s%s.csv' % (file_prefix, self.name)
			
			return (csv_file, filename)
		except:
			_logger.debug("error creating paypal csv file", exc_info=True)
			
	@api.multi
	def finalize_sepa_file_creation(self, xml_root, gen_args):
		xml_string, filename = super(AccountPaymentOrder, self).finalize_sepa_file_creation(xml_root, gen_args)
		_logger.debug("xml is: " + str(xml_root))
		filename = '%s%s.xml' % (self.name, '_PAIN001')
		return (xml_string, filename)
		
