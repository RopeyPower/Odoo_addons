# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging
from openerp.exceptions import Warning


_logger = logging.getLogger(__name__)


class translationie_realex_payment_config(models.TransientModel):
	_inherit = 'res.config.settings'
	_name = 'custom_payments.realex.config'
	
	url = fields.Char(string='Realex url', help='Url for realex hosted payment page', default='https://hpp.sandbox.realexpayments.com/pay')
	merchant_id = fields.Char(string='Merchant ID', help='Merchant ID provided by Realex, also known as Client ID', default='translation')
	#no 3d secure details
	account = fields.Char(default='internet')
	secret = fields.Char(help='Realex Shared Secret', default='secret')
	#3d secure details
	account_3d_secure = fields.Char(help="Account name for 3d Secure transactions.", string="3d Secure Account")
	secret_3d_secure = fields.Char(help='Realex Shared Secret for 3d Secure transactions.', string="3d Secure Secret")
	
	response_url = fields.Char(string='Merchant Response Url', help='Url for Realex to respond with result of payment to.', default='https://erp.translation.ie/payment_process')
	hpp_version = fields.Selection([('1','No Card Management'),('2','Card Management')], string='Payment Page Version', default='1', help='[no_management] = No Card Management available on Hosted Payment Page. [managment] = Card Management available on Hosted Payment Page')
	
	company_name = fields.Char(string='Company Name')
	company_address = fields.Char(string='Company Address')
	company_city = fields.Char(string='Company City')
	company_country = fields.Char(string='Company Country')
	
	#email notification settings
	sender_account = fields.Many2one(comodel_name='fetchreply.mailbox', string='Sender Account', help='Internal User Mailbox that email notifications for successful payments will be sent from', ondelete='set null')
	receiver_account = fields.Many2one(comodel_name='fetchreply.mailbox', string='Internal Receiver Account', help='Internal User Mailbox that will recieve email notifications for successful payments. (For our company not the customer)', ondelete='set null')
	
	
	@api.model
	def get_default_realex_values(self, fields):
		try:
			realex = self.env['custom_payments.realex'].browse(1)
			# _logger.debug("response url: " + str(realex.response_url) + " " + str(realex))
			if realex.exists():
				url = realex.url
				merchant_id = realex.merchant_id
				account = realex.account
				secret = realex.secret
				account_3d_secure = realex.account_3d_secure
				secret_3d_secure = realex.secret_3d_secure
				response_url = realex.response_url
				hpp_version = realex.hpp_version
				company_name = realex.company_name
				company_address = realex.company_address
				company_city = realex.company_city
				company_country = realex.company_country
				sender_account = realex.sender_account
				receiver_account = realex.receiver_account
			else:
				url = 'https://hpp.sandbox.realexpayments.com/pay'
				merchant_id = 'translation',
				account = 'internet'
				secret = 'secret'
				account_3d_secure = ''
				secret_3d_secure = ''
				response_url = 'https://erp.translation.ie/payment_process'
				hpp_version = '1'
				company = self.env['res.company']._company_default_get('custom_payments.realex.config')
				company_name = company.name
				company_address = company.street
				company_city = company.city
				company_country = company.country_id.name
				sender_account = False
				receiver_account = False
			
			data = {
				'url': url,
				'merchant_id': merchant_id,
				'account': account,
				'secret': secret,
				'account_3d_secure': account_3d_secure,
				'secret_3d_secure': secret_3d_secure,
				'response_url': response_url,
				'hpp_version': hpp_version,
				'company_name': company_name,
				'company_address': company_address,
				'company_city': company_city,
				'company_country': company_country,
			}
			if sender_account:
				data['sender_account'] = sender_account.id
			if receiver_account:
				data['receiver_account'] = receiver_account.id
			
			if not realex.exists():
				self.env['custom_payments.realex'].create(data)
			
			return data
			
		except Exception:
			_logger.error("error getting realex values", exc_info=True)
	
	@api.multi
	def set_realex_values(self):
		realex = self.env['custom_payments.realex'].browse(1)
		_logger.debug("set realex is: " + str(realex))
		try:
			data = {
				'url': self.url,
				'merchant_id': self.merchant_id,
				'account': self.account,
				'secret': self.secret,
				'account_3d_secure': self.account_3d_secure,
				'secret_3d_secure': self.secret_3d_secure,
				'response_url': self.response_url,
				'hpp_version': self.hpp_version,
				'company_name': self.company_name,
				'company_address': self.company_address,
				'company_city': self.company_city,
				'company_country': self.company_country,
				'sender_account': self.sender_account.id,
				'receiver_account': self.receiver_account.id
			}
			if realex:
				_logger.debug("data is: " + str(data) + " company: " + str(self.env['res.company']._company_default_get('custom_payments.realex.config')))
				realex.write(data)
			else:
				self.env['custom_payments.realex'].create(data)
			
		except Exception:
			_logger.error("error setting realex values", exc_info=True)
	
	# @api.model
	# def get_default_realex_values(self, fields):
		# return {
			# 'url': 'https://hpp.sandbox.realexpayments.com/pay',
			# 'merchant_id': 'translation',
			# 'account': 'internet',
			# 'secret': 'secret',
			# 'response_url': 'https://erp.translation.ie/payment_processed',
			# 'hpp_version': '1'
		# }

	
	# @api.one
	# def set_realex_values(self):
		# realex = self.env['custom_payments.realex'].browse(1)
		# _logger.debug("realex is: " + str(realex))
		# if realex:
		# realex.ensure_one()
			# realex.url = self.url
			# realex.merchant_id = self.merchant_id
			# realex.account = self.account
			# realex.secret = self.secret
			# realex.response_url = self.response_url
			# realex.hpp_version = self.hpp_version
		# else:
			# data = {
			# 'url': 'https://hpp.sandbox.realexpayments.com/pay',
			# 'merchant_id': 'translation',
			# 'account': 'internet',
			# 'secret': 'secret',
			# 'response_url': 'https://erp.translation.ie/payment_processed',
			# 'hpp_version': '1'
			# }
			# self.env['custom_payments.realex'].create(data)
		
		

