# -*- coding: utf-8 -*-

from openerp import models, fields, api
import datetime
import hashlib
import requests
import logging
from openerp.exceptions import Warning
import urllib
import urllib2
from decimal import *
import svgwrite
from wand.image import Image
import re
import unicodedata

_logger = logging.getLogger(__name__)

class translationie_realex_payment(models.Model):
	_name = 'custom_payments.realex'
	
	url = fields.Char(string='Realex url', help='Url for realex hosted payment page', default='https://hpp.sandbox.realexpayments.com/pay')
	merchant_id = fields.Char(string='Merchant ID', help='Merchant ID provided by Realex, also known as Client ID', default='translation')
	#no 3d secure details
	account = fields.Char(default='internet')
	secret = fields.Char(help='Realex Shared Secret', default='secret')
	#3d secure details
	account_3d_secure = fields.Char(help="Account name for 3d Secure transactions.", string="3d Secure Account")
	secret_3d_secure = fields.Char(help='Realex Shared Secret for 3d Secure transactions.', string="3d Secure Secret")
	
	response_url = fields.Char(string='Merchant Response Url', help='Url for Realex to respond with result of payment to.')
	hpp_version = fields.Selection([('1','No Card Management'),('2','Card Management')], string='Payment Page Version', default='1', help='[no_management] = No Card Management available on Hosted Payment Page. [management] = Card Management available on Hosted Payment Page')
	
	#receipt settings
	company_name = fields.Char(string='Company Name')
	company_address = fields.Char(string='Company Address')
	company_city = fields.Char(string='Company City')
	company_country = fields.Char(string='Company Country')
	
	#email notification settings
	sender_account = fields.Many2one(comodel_name='fetchreply.mailbox', string='Sender Account', help='Internal User Mailbox that email notifications for successful payments will be sent from', ondelete='set null')
	receiver_account = fields.Many2one(comodel_name='fetchreply.mailbox', string='Internal Receiver Account', help='Internal User Mailbox that will recieve email notifications for successful payments. (For our company not the customer)', ondelete='set null')
	
	
	def handle_response_success(self, form):
		try:
			docid = form['COMMENT2']
			document = self.env['sale.order'].sudo().search([('x_order_uid','=',docid)])
			
			realex_settings = self.env['custom_payments.realex'].sudo().browse(1)
			#check response hash
			sha1 = form['TIMESTAMP'] + '.' + form['MERCHANT_ID'] + '.' + form['ORDER_ID'] + '.' + form['RESULT'] + '.' + form['MESSAGE'] + '.' + form['PASREF'] + '.' + form['AUTHCODE']
			hash_obj = hashlib.sha1(sha1)
			hash_string = hash_obj.hexdigest()
			hash_string += '.' + realex_settings.secret
			hash_obj = hashlib.sha1(hash_string)
			sha1 = hash_obj.hexdigest()
			
			if form['SHA1HASH'] == sha1:
				journal = self.env['account.journal'].sudo().search([('code','=','BNK3'),('name','=','Credit card')])
				payment_method = self.env['account.payment.method'].sudo().search([('code','=','manual'),('payment_type','=','inbound')])
				
				TWOPLACES = Decimal(10) ** -2    
				payment_amount = Decimal(form['AMOUNT']).quantize(TWOPLACES) / 100
				time_stamp = datetime.datetime.strptime(form['TIMESTAMP'], '%Y%m%d%H%M%S').date()
				
				
				
				if document.state in ['draft','sent']:
					document.sudo().action_confirm()
					_logger.debug("CONFIRMED SALE " + document.name)
					invoice_id = document.sudo().action_invoice_create()
					
					payment_invoice = self.env['account.invoice'].sudo().search([('id','in',invoice_id)])
					_logger.debug("CREATED INVOICE " + str(payment_invoice))
					payment_invoice.signal_workflow('invoice_open')
					invoice_partner = payment_invoice.partner_id
					
				elif document.state == 'sale':
					if document.invoice_status == 'to invoice':
						invoice_id = document.sudo().action_invoice_create()
						payment_invoice = self.env['account.invoice'].sudo().search([('id','in',invoice_id)])
						_logger.debug("CREATED INVOICE " + str(payment_invoice))
						payment_invoice.signal_workflow('invoice_open')
					
					invoice_ids = [invoice.id for invoice in document.invoice_ids if invoice.state == 'open']
					payment_invoice = self.env['account.invoice'].browse(invoice_ids)
					invoice_partner = payment_invoice[0].partner_id
					_logger.debug("invoice is: " + str(payment_invoice))
				
				
				communication = document.name + ' ' + str(form['COMMENT1'])
				
				payment_data = {
					'journal_id': journal.id,
					'communication': communication,
					'payment_date': time_stamp,
					'partner_type': 'customer',
					'payment_type': 'inbound',
					'amount': payment_amount,
					'partner_id': invoice_partner.id,
					'invoice_ids': [(6, 0, payment_invoice.ids)],
					'payment_difference_handling': 'open',
				}
				
				
				if payment_method:
					payment_data['payment_method_id'] = payment_method.id
				
				payment = self.env['account.payment'].sudo().create(payment_data)
				_logger.debug("PAYMENT CREATED: " + str(payment))
				payment._compute_destination_account_id()
				payment.post()
				_logger.debug("PAYMENT POSTED")
				self.env['custom_payments.realex.statement'].sudo().record_card_payment(payment)
				_logger.debug("REALEX PAYMENT RECORDED")
				transaction_time = datetime.datetime.strptime(form['TIMESTAMP'], '%Y%m%d%H%M%S')
				time_string = transaction_time.strftime('%d/%m/%Y at %H:%M:%S')
				
				svg_data = {
						'order_name': document.name,
						'currency': document.currency_id.name,
						'customer': document.partner_id.name,
						'payment_amount': str(payment_amount),
						'time': time_string,
						'realex_order_id': form['ORDER_ID'],
						'result': form['RESULT'],
						'message': form['MESSAGE'],
						'authcode': form['AUTHCODE'],
					}
				
				
				receipt_attachment = document.create_svg_receipt(svg_data)
				_logger.debug("RECEIPT CREATED")
				
				project_url = self.get_project_url(document)
				company = self.env['res.company']._company_default_get('custom_payments.realex')
				
				
				notification_data = {
					'realex_settings': realex_settings.id,
					'order_document': document.id,
					'company': company.id,
					'project_link': project_url,
					'attachment_ids': [(4,receipt_attachment.id)],
					'order_id': str(form['ORDER_ID']),
				}
				
				notification_obj = self.env['custom_payments.realex.notification'].create(notification_data)
				notification_obj.send_customer_confirmation()
				_logger.debug("CUSTOMER NOTIFIED")
				notification_obj.send_pm_notification()
				_logger.debug("PM NOTIFIED")
				
				return_data = {
					'docid': document.x_order_uid
				}
				
				return return_data
				
				
			else:
				# return "SHA1 is wrong returned: " + str(SHA1HASH) + " should be: "  + sha1
				raise ValueError("The SHA1 returned by the HPP differs from the one calculated on our side implying someone tampered with the transaction. This transaction is considered invalid and no action has been taken to process it")
		except Exception:
			_logger.error("error receiving hpp response", exc_info=True)
	
	def handle_response_failure(self, form):
		docid = form['COMMENT2']
		document = self.env['sale.order'].sudo().search([('x_order_uid','=',docid)])
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		base_url_ssl = base_url.replace('http', 'https')
		
		realex_settings = self.env['custom_payments.realex'].sudo().browse(1)
		_logger.debug("result is: " + str(form['RESULT']))
		
		TWOPLACES = Decimal(10) ** -2    
		payment_amount = Decimal(form['AMOUNT']).quantize(TWOPLACES) / 100
		transaction_time = datetime.datetime.strptime(form['TIMESTAMP'], '%Y%m%d%H%M%S')
		time_string = transaction_time.strftime('%d/%m/%Y at %H:%M:%S')
		
		svg_data = {
						'order_name': document.name,
						'currency': document.currency_id.name,
						'customer': document.partner_id.name,
						'payment_amount': str(payment_amount),
						'time': time_string,
						'realex_order_id': form['ORDER_ID'],
						'result': form['RESULT'],
						'message': form['MESSAGE'],
						'authcode': form['AUTHCODE'],
					}
		receipt_attachment = document.create_svg_receipt(svg_data)
		
		
		reTransactionFail = r"1\d{2}"
		reBankError = r"2\d{2}"
		reRealexError = r"3\d{2}"
		
		message = []
		if form['RESULT'] == '102':
			message.append("Your payment for order: <strong>" + str(document.name).upper()  + "</strong> has been declined by your bank due to a reason we can not ascertain. Please contact your banks support centre for further information.")
		elif form['RESULT'] == '103':
			message.append("Your payment for order: <strong>" + str(document.name).upper()  + "</strong> has been declined by your bank as your card has been reported lost or stolen. Please contact your banks support centre for further information.")
		elif form['RESULT'] == '110':
			message.append("Your payment for order: <strong>" + str(document.name).upper()  + "</strong> has been declined by your bank as you have failed the 3D Secure Check.(More commonly known as Verified by visa, Mastercard SecureCode or American Express SafeKey). No transaction has been processed against your account. You may attempt this transaction again by following the link originally emailed to you.")
		elif form['RESULT'] == '101' or re.match(reTransactionFail, form['RESULT']):
			message.append("Your payment for order: <strong>" + str(document.name).upper()  + "</strong> has been declined by your bank due to either insufficient funds or incorrect card details(e.g. expiry date, card security code, etc.). No transaction has been processed against your account. You may attempt this transaction again by following the link originally emailed to you.")
		elif re.match(reBankError, form['RESULT']):
			message.append("Your payment for order: <strong>" + str(document.name).upper()  + "</strong> has not been successful. There is currently an issue with your banks system and the transaction can not be processed at this time. No charge has been made to your account. Please try again later, you can do this by following the link originally emailed to you again.")
		elif re.match(reRealexError, form['RESULT']):
			message.append("Your payment for order: <strong>" + str(document.name).upper()  + "</strong> has not been successful. There is currently an issue with the Realex system and the transaction can not be processed at this time. No charge has been made to your account. Please try again later, you can do this by following the link originally emailed to you again.")
		elif form['RESULT'] == '666':
			message.append("We are unable to process your payment for order: <strong>" + str(document.name).upper() + "</strong> at the moment. No charge has been made to your account. You may try again later by following the link that was originally emailed to you.")
			notification_data = {
					'realex_settings': realex_settings.id,
				}
			notification_obj = self.env['custom_payments.realex.notification'].create(notification_data)
			notification_obj.send_account_deactivated_notification()
		
		return_data = {
			'docid': document.x_order_uid,
			'failure_message': message,
		}
		
		return return_data
			
	def get_project_url(self, document):
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		base_url_ssl = base_url.replace('http', 'https')
		
		imd = self.env['ir.model.data']
		action_id = imd.xmlid_to_res_id('project.open_view_project_all')
		project_id = document.project_id.project_ids[0].id
		
		url = base_url_ssl + '/web#id=' + str(project_id) + '&view_type=form&model=project.project&action=' + str(action_id)
		return url
	
class translationie_realex_statement(models.Model):
	_name = 'custom_payments.realex.statement'
	
	name = fields.Char(string='Statement Name')
	batch_state = fields.Selection([('open','Open'),('close','Close')], default='open')
	batch_date = fields.Date(string='Statement Date')
	batch_payments = fields.Many2many(comodel_name='account.payment', ondelete='set null')
	
	# add a payment to the current batch file
	def record_card_payment(self, payment):
		statement_batch = self.get_current_batch()
		statement_batch.batch_payments = [(4, payment.id)]
		
	
	# check if batch for current date exists else create one and return
	def get_current_batch(self):
		current_date = datetime.date.today()
		current_batch = self.env['custom_payments.realex.statement'].search([('batch_date','=',current_date),('batch_state','=','open')])
		
		if current_batch.exists():
			return current_batch
		else:
			data = {
				'name': 'Realex Batch - ' + str(current_date),
				'batch_date': current_date
			}
			current_batch = self.env['custom_payments.realex.statement'].create(data)
			return current_batch
	
	def infer_auto_reconcile_allowed(self, payment):
		#check if auto reconciliation of a bank statement line should be allowed
		#Returns True if payment is for full order amount
		#Returns False if payment is partial, this is to prevent a situation where 50% of an invoice is paid and the automatic reconciliation process
		#reconciles the bank statement line against the unpaid 50% of the invoice when it should be reconciled against the registered payment for 50% instead
		order = self.env['sale.order'].search([('name','=',payment.communication)])
		if payment.amount != order.amount_total:
			auto_reconcile_allowed = False
		else:
			auto_reconcile_allowed = True
		return auto_reconcile_allowed
	
	@api.model
	def _close_daily_batch(self):
		_logger.debug("running daily batch management")
		try:
			current_date = datetime.date.today()
			daily_batch = self.env['custom_payments.realex.statement'].search([('batch_state','=','open')])
			for batch in daily_batch:
				batch_journal = batch.batch_payments[0].journal_id
				data = {
					'name': 'Realex Daily Batch - ' + str(batch.batch_date),
					'journal_id': batch_journal.id,
				}
				
				credit_card_statement = self.env['account.bank.statement'].create(data)
				
				for payment in batch.batch_payments:
					data = {
						'name': payment.communication,
						'journal_id': credit_card_statement.journal_id.id,
						'partner_id': payment.partner_id.id,
						'amount': payment.amount,
						'statement_id': credit_card_statement.id,
					}
					
					self.env['account.bank.statement.line'].create(data)
				
				credit_card_statement.reconciliation_widget_preprocess()
					
				#create transfer to match money transferred from card holding company account to our bank account
				#destination_journal = self.env['account.journal'].search([('code','=','BNK1'),('name','=','BankAC-WR')])
				destination_journal = self.env['account.journal'].search([('code','=','BNK1'),('type','=','bank')])
				payment_method = self.env['account.payment.method'].search([('code','=','manual'),('payment_type','=','outbound')])
				data = {
					'journal_id': credit_card_statement.journal_id.id,
					'destination_journal_id': destination_journal.id,
					'payment_date': batch.batch_date,
					'payment_type': 'transfer',
					'payment_method_id': payment_method.id,
					'amount': credit_card_statement.balance_end,
					'communication': 'Realex Daily Batch - ' + str(batch.batch_date),
				}
				batch_payment_transfer = self.env['account.payment'].create(data)
				batch_payment_transfer.post()
				batch.batch_state = 'close'
		except Exception:
			_logger.error("error closing daily realex batch", exc_info=True)

class translationie_realex_notification(models.TransientModel):
	_name = 'custom_payments.realex.notification'
	
	realex_settings = fields.Many2one(comodel_name='custom_payments.realex', ondelete='set null')
	
	order_document = fields.Many2one(comodel_name='sale.order', ondelete='set null')
	
	# Realex Receipt Variables
	company = fields.Many2one(comodel_name='res.company')
	project_link = fields.Char()
	attachment_ids = fields.Many2many(comodel_name='ir.attachment')
	order_id = fields.Char()
	
	def send_customer_confirmation(self):
		template = self.env.ref('translationie_realex_payment_integration.realex_customer_notification_email_template')
		template = self.env['mail.template'].browse(template.id)
		_logger.debug("attachments: " + str(self.attachment_ids) + " names: " + str([attachment.name for attachment in self.attachment_ids]))
		_logger.debug("attachment url is: " + str(self.attachment_ids.local_url))
		template.attachment_ids = [(6,0,self.attachment_ids.ids)]
		template.send_mail(self.id, force_send=True)
		
	def send_pm_notification(self):
		template = self.env.ref('translationie_realex_payment_integration.realex_pm_notification_email_template')
		template = self.env['mail.template'].browse(template.id)
		template.send_mail(self.id, force_send=True)
		
	def send_account_deactivated_notification(self):
		_logger.debug("account deactivated method")
		template = self.env.ref('translationie_realex_payment_integration.realex_account_deactivated_notification_email_template')
		template = self.env['mail.template'].browse(template.id)
		email_to = ''
		for mailbox in self.env['fetchreply.mailbox'].search([('active','=',True)]):
			email_to += str(mailbox.user) + ', '
		template.email_to = email_to
		template.send_mail(self.id, force_send=True)
	
class SaleOrder(models.Model):
	_inherit = "sale.order"
	
	x_order_uid = fields.Char(string='Unique Order ID', readonly=True, compute='_get_order_uid', store=True)
	x_realex_sha1 = fields.Char(readonly=True)
	x_payment_url = fields.Char(compute="_get_payment_url")
	x_deposit_url = fields.Char(compute="_get_payment_url")
	x_receipt_svg = fields.Text()
	x_amount_due = fields.Monetary(string="Amount Due", compute="_get_amnt_due")
	x_fully_paid = fields.Boolean(string="Fully Paid", compute="_get_amnt_due")
	x_deposit_allowed = fields.Boolean(compute="_check_deposit_allowed")
	
	@api.depends('x_amount_due')
	def _check_deposit_allowed(self):
		if self.x_amount_due == self.amount_total:
			deposit_allowed = True
		else:
			deposit_allowed = False
		self.x_deposit_allowed = deposit_allowed
	
	@api.depends('invoice_ids.residual','invoice_ids','invoice_ids.state')
	def _get_amnt_due(self):
		try:
			_logger.debug("recalculating amount due")
			order = self
			order.ensure_one()
			valid_invoices = [invoice for invoice in order.invoice_ids if invoice.state in ['open','paid']]
			if valid_invoices:
				total_due = 0
				invoiced_total_due = 0
				invoiced_total_amount = 0
				for invoice in valid_invoices:
					invoiced_total_due += invoice.residual
					invoiced_total_amount += invoice.amount_total
				_logger.debug("invoiced total due: " + str(invoiced_total_due) + " invoiced total amount: " + str(invoiced_total_amount))
				if invoiced_total_amount < order.amount_total:
					total_due = invoiced_total_due + (order.amount_total - invoiced_total_amount)
				elif invoiced_total_amount == order.amount_total:
					total_due = invoiced_total_due
			else:
				total_due = order.amount_total
			_logger.debug("total due is: " + str(total_due))
			if total_due <= 0:
				fully_paid = True
			else:
				fully_paid = False
			order.x_amount_due = total_due
			order.x_fully_paid = fully_paid
			
			_logger.debug("so amount due:" + str(order.x_amount_due) + " fully paid: " + str(order.x_fully_paid))
		except Exception:
			_logger.error("error getting amount due", exc_info=True)
			
	@api.multi
	def button_create_receipt(self):
		form = {
			'order_name': 't12',
			'payment_amount': '11.50',
			'currency': 'EUR',
			'time': '21/11/2017 at 17:29:36',
			'ORDER_ID': 't12_DavidDignamCustomer_20171121172936',
			'customer': 'David Dignam Customer',
			'RESULT': '00',
			'MESSAGE': '[ test system ] AUTHORISED',
			'AUTHCODE': '12345'
		}
		
		self.create_svg_receipt(form)
	
	def create_svg_receipt(self, data):
		try:
			realex = self.env['custom_payments.realex'].sudo().browse(1)
			receipt_name = data['order_name'] + '_Receipt.svg'
			receipt = svgwrite.Drawing(filename=receipt_name, size=("464px", "501px"))
			
			
			receipt.add(receipt.rect(insert=('1%','1%'),
									size=("98%","98%"),
									stroke_width="2",
									stroke="black",
									fill = "rgb(255,255,255)"))
			#styles (TODO try get add_stylesheet working, assigning classes from stylesheet does nothing currently)
			normal_size = "font-size:14pt;font-weight:normal;"
			
			
			receipt.add(receipt.text("RECEIPT", insert=('50%','9%'), text_anchor="middle", style="font-size:32px;font-weight:bold;"))
			receipt.add(receipt.text(str(realex.company_name), insert=('50%','15%'), text_anchor="middle", style=normal_size))
			order_ref = 'REF: ' + data['order_name']
			receipt.add(receipt.text(order_ref, insert=('50%','21%'), text_anchor="middle", style="font-size:16pt;font-weight:bold;"))
			receipt.add(receipt.line(start=('15%','24%'),end=('85%','24%'), stroke_width="1", stroke="black"))
			receipt.add(receipt.text("SALE TRANSACTION", insert=('50%','30%'), text_anchor="middle", style=normal_size))
			amount_line = data['payment_amount'] + ' ' + data['currency']
			receipt.add(receipt.text(amount_line, insert=('50%','37%'), text_anchor="middle", style="font-size:20pt;font-weight:bold;"))
			receipt.add(receipt.text(data['time'], insert=('50%','43%'), text_anchor="middle", style=normal_size))
			receipt.add(receipt.line(start=('15%','47%'),end=('85%','47%'), stroke_width="1", stroke="black"))
			receipt.add(receipt.text("ORDER ID:", insert=('50%','53%'), text_anchor="middle", style=normal_size))
			receipt.add(receipt.text(data['realex_order_id'], insert=('50%','58%'), text_anchor="middle", style=normal_size))
			receipt.add(receipt.line(start=('15%','62%'),end=('85%','62%'), stroke_width="1", stroke="black"))
			
			customer_name = unicodedata.normalize('NFKD', data['customer']).encode('ascii','ignore')
			receipt.add(receipt.text(customer_name, insert=('50%','68%'), text_anchor="middle", style=normal_size))
			if data['result'] == "00":
				result_colour = "green"
				message = 'Authorised'
			else:
				result_colour = "red"
				message = 'Declined'
			receipt.add(receipt.rect(insert=('15%','72%'), size=('70%','20%'), fill=result_colour))
			result_line = str(data['result']) + ' - ' + message
			receipt.add(receipt.text(result_line, insert=('50%','78%'), text_anchor="middle", fill="white", style=normal_size))
			receipt.add(receipt.text("AUTHCODE", insert=('50%','84%'), text_anchor="middle", fill="white", style=normal_size))
			receipt.add(receipt.text(data['authcode'], insert=('50%','89%'), text_anchor="middle", fill="white", style=normal_size))
			
			receipt_data = receipt.tostring().encode('base64')
			receipt_name = data['order_name'] + '_Receipt.png'
			
			#convert svg to png to save as attachement and add to email
			with Image(blob=receipt.tostring().encode('ascii'), format="svg") as image:
				png_image = image.make_blob("png")
				_logger.debug("png img is: " + str(png_image))
			
			attachment = self.env['ir.attachment'].create({
				'res_model': 'sale.order',
				'res_id': self.id,
				'name': receipt_name,
				'datas': png_image.encode('base64'),
				'datas_fname': receipt_name,
				})
			
			
			self.x_receipt_svg = receipt.tostring()
			
			return attachment
		except Exception:
			_logger.error("error creating svg", exc_info=True)
	
	@api.depends('x_order_uid')
	def _get_payment_url(self):
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		base_url_ssl = base_url.replace('http', 'https')
		_logger.debug("url is: " + str(base_url_ssl) + '/pay/?docid=' + str(self.x_order_uid))
		self.x_payment_url = base_url_ssl + '/pay/?docid=' + self.x_order_uid
		self.x_deposit_url = base_url_ssl + '/deposit/?docid=' + self.x_order_uid
	
	@api.depends('name','date_order','partner_id')
	def _get_order_uid(self):
		try:
			_order_secret = "transferendumFC"
			for order in self:
				if not order.x_order_uid:
					client = order.partner_id.name
					client = unicodedata.normalize('NFKD', client).encode('ascii','ignore')
					_logger.debug("client: " + client)
					project = str(order.name)
					date = order.date_order
					
					sha_string = client + '.' + project + '.' + date
					
					hash_object = hashlib.sha1(sha_string)
					hash_string = hash_object.hexdigest()
					hash_string += '.' + _order_secret
					hash_object = hashlib.sha1(hash_string)
					order_uid = hash_object.hexdigest()
					_logger.debug("uid is: " + order_uid)
					
					order.x_order_uid = order_uid
		except Exception:
			_logger.debug("error generating uid", exc_info=True)
	
	def get_hpp_values(self, deposit=False, secure3d=False):
		order = self
		order.ensure_one()
		
		realex_settings = self.env['custom_payments.realex'].browse(1)
		
		timestamp = str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
		project_name = ""
		if order.project_id:
			project_name = order.project_id.name
		
		order_id = project_name  + '_' + timestamp
		order_id = order_id.replace(" ", "")
		order_id = order_id.replace(".","_")
		
		if deposit:
			amount = int((order.amount_total * 0.5)  * 100)
			comment = 'deposit'
		else:
			order._get_amnt_due()
			amount = int(order.x_amount_due * 100)
			if order.x_amount_due == order.amount_total:
				comment = 'full'
			else:
				comment = 'balance'
		currency = order.currency_id.name
		
		if secure3d and realex_settings.account_3d_secure and realex_settings.secret_3d_secure:
			_logger.debug("3d secure")
			account = realex_settings.account_3d_secure
			secret = realex_settings.secret_3d_secure
		else:
			_logger.debug("no 3d secure")
			account = realex_settings.account
			secret = realex_settings.secret
		_logger.debug("account: " + str(account))
		sha1_string = timestamp + '.' + str(realex_settings.merchant_id) + '.' + order_id + '.' + str(amount) + '.' + str(currency)
		sha1_hash = self.calc_sha1_hash(sha1_string, secret)
		
		auto_settle_flag = '1'
		
		
		comment2 = order.x_order_uid
		
		TWOPLACES = Decimal(10) ** -2    
		payment_display_amount = Decimal(amount).quantize(TWOPLACES) / 100
		
		hpp_info = {
			'timestamp':timestamp,
			'order_id':order_id,
			'amount':amount,
			'currency':currency,
			'sha1':sha1_hash,
			'auto_settle':auto_settle_flag,
			'comment':comment,
			'comment2':comment2,
			'payment_display_amount': payment_display_amount,
			'account': account,
		}
			
		order.x_realex_sha1 = sha1_hash
		
		return hpp_info
	
	def calc_sha1_hash(self, sha1_string, secret):
		_logger.debug("secret: " + str(secret))
		hash_object = hashlib.sha1(sha1_string)
		hash_string = hash_object.hexdigest()
		hash_string += '.' + secret
		hash_object = hashlib.sha1(hash_string)
		sha1 = hash_object.hexdigest()
		return sha1
	
	@api.multi
	def button_pay_by_card(self):
		return self.pay_by_card()
		
	@api.multi
	def button_pay_deposit(self):
		return self.pay_by_card(deposit=True)
	
	def pay_by_card(self, deposit=False):
		try:
			_logger.debug("card payment button pressed")
			realex = self.env['custom_payments.realex'].browse(1)
			order = self
			
			url = realex.url
			
			_logger.debug("realex url is: " + str(url))
			
			hpp_info = order.get_hpp_values(deposit=deposit)
			
			
			_logger.debug("amount due is: " + str(hpp_info['amount']))
			data = {
				'TIMESTAMP': hpp_info['timestamp'],
				'MERCHANT_ID': realex.merchant_id,
				'ACCOUNT': hpp_info['account'],
				'ORDER_ID': hpp_info['order_id'],
				'AMOUNT': hpp_info['amount'],
				'CURRENCY': hpp_info['currency'],
				'SHA1HASH': hpp_info['sha1'],
				'AUTO_SETTLE_FLAG': hpp_info['auto_settle'],
				'COMMENT1': hpp_info['comment'],
				'COMMENT2': hpp_info['comment2'],
				'VAR_REF': order.project_id.name,
				'HPP_VERSION': realex.hpp_version,
				'MERCHANT_RESPONSE_URL': realex.response_url,
			}
			
			base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
			base_url_ssl = base_url.replace('http', 'https')
			referer_url = base_url_ssl + '/sale'
			_logger.debug("referer is: " + str(referer_url))
			
			headers = {
						'Content-type': 'application/x-www-form-urlencoded',
						'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
						'Referer': referer_url
					}
			#url = "http://requestbin.fullcontact.com/xnwrstxn"
			_logger.debug("raw body: " + str(data) + " type: " + str(type(data)))
			response = requests.post(url, data=data, headers=headers, verify=True)
			# content = urllib2.urlopen(url=url, data=data)
			_logger.debug("response is: " + str(response.url))
			return {
				'type': 'ir.actions.act_url',
				'url': str(response.url),
				'target': 'self',
			}
		except Exception:
			_logger.error("error posting to hpp", exc_info=True)

		
	



