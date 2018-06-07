# -*- coding: utf-8 -*-
from openerp import http
import logging
import datetime
import hashlib
import json
import socket
import requests
import urllib
from decimal import *
from werkzeug.exceptions import HTTPException, NotFound
from openerp.http import Response 
from openerp.http import local_redirect, request
import re

_logger = logging.getLogger(__name__)


class TranslationieRealexPaymentIntegration(http.Controller):
	#Redirect to HPP and pay full amount
	@http.route('/pay/', auth='public', website=True)
	def pay(self, docid, **kw):
		document = http.request.env['sale.order'].sudo().search([('x_order_uid','like',docid)])
		if document and not document.x_fully_paid:
			hpp_info = document.get_hpp_values(secure3d=True)
			realex_settings = http.request.env['custom_payments.realex'].sudo().browse(1)
			
			return http.request.render('translationie_realex_payment_integration.payment_page', {
				'document': document, 'hpp_info':hpp_info, 'realex':realex_settings
				})
		else:
			return http.request.render('translationie_realex_payment_integration.not_found',{})

	#Redirect to HPP and pay half
	@http.route('/deposit/', auth='public', website=True)
	def deposit(self, docid, **kw):
		# try:
		document = http.request.env['sale.order'].sudo().search([('x_order_uid','like',docid)])
		if document and document.x_deposit_allowed:
			hpp_info = document.get_hpp_values(deposit=True, secure3d=True)
			realex_settings = http.request.env['custom_payments.realex'].sudo().browse(1)
			
			
			return http.request.render('translationie_realex_payment_integration.downpayment_page', {
				'document': document, 'hpp_info':hpp_info, 'realex':realex_settings
				})
		else:
			return http.request.render('translationie_realex_payment_integration.not_found',{})
	
	#
	@http.route('/payment_success', auth='public', methods=['GET'], website=True, csrf=False)
	def success(self, **kw):
		_logger.debug("payment successful")
		realex_settings = http.request.env['custom_payments.realex'].sudo().browse(1)
		data = http.request.httprequest.args
		docid = data['docid']
		document = http.request.env['sale.order'].sudo().search([('x_order_uid','like',docid)])
		_logger.debug("data is: " + str(data))
		return http.request.render('translationie_realex_payment_integration.confirmation_page',{
			'document': document, 'receipt_info': data, 'realex': realex_settings
		})
	
	@http.route('/payment_failure', auth='public', methods=['GET'], website=True, csrf=False)
	def failure(self, **kw):
		_logger.debug("payment failure")
		data = http.request.httprequest.args
		message_data = dict(http.request.httprequest.args)
		docid = data['docid']
		document = http.request.env['sale.order'].sudo().search([('x_order_uid','like',docid)])
		_logger.debug("full data is: " + str(data))
		_logger.debug("data message is: " + str(data['failure_message']))
		message = message_data['failure_message']
		_logger.debug("message is: " + str(message))
		return http.request.render('translationie_realex_payment_integration.failure_page',{
			'document': document, 'failure_message': [line for line in message],
		})
	
	#Redirects to either "success" or "failure" controller methods based on RESULT HPP returns
	@http.route('/payment_process', auth='public', type='http', methods=['POST','GET'], website=True, csrf=False)
	def payment_process(self, **kwargs):
		form = http.request.httprequest.form
		realex = http.request.env['custom_payments.realex'].sudo().browse(1)
		_logger.debug("form data is: " + str(form))
		#NEED to set param in Odoo ir.config_parameter
		try:
			base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
			base_url_ssl = base_url.replace('http', 'https')
			reTransactionFail = r"1\d{2}"
			
			if form['RESULT'] == '00':
				url = base_url_ssl + '/payment_success'
				data = form
				data = realex.handle_response_success(data)

				return  local_redirect(url, dict(data), True, code=200)
				
			else:
				url = base_url_ssl + '/payment_failure'
				data = realex.handle_response_failure(form)
				return local_redirect(url, dict(data), True, code=200)
		except Exception:
			_logger.error("error processing payment response", exc_info=True)
	
	@http.route('/view_tasks', auth='public', type='http', methods=['GET'], csrf=False)
	def view_tasks(self, docid, **kw):
		document = http.request.env['sale.order'].sudo().search([('id','=',docid)])
		result = document.action_view_task()
		
		imd = http.request.env['ir.model.data']
		iuv = http.request.env['ir.ui.view']
		list_view_id = imd.xmlid_to_res_id('project.view_task_tree2')
		view = iuv.browse(list_view_id)
		_logger.debug("view is: " + str(view))
		return view
		
		# _logger.debug("result is: " + str(result))
		# context = {
			# 'search_default_project':1,
			# 'active_id': document.id
		# }
		# return http.request.render('project.view_task_tree2', qcontext=context)

	
	# @http.route('/payment_success', auth='public', methods=['POST','GET'], website=True, csrf=False)
	# def success(self, RESULT=None, AUTHCODE=None, MESSAGE=None, PASREF=None, AVSPOSTCODERESULT=None, AVSADDRESSRESULT=None, CVNRESULT=None, ACCOUNT=None, MERCHANT_ID=None, ORDER_ID=None, TIMESTAMP=None, AMOUNT=None, CARD_PAYMENT_BUTTON=None, MERCHANT_RESPONSE_URL=None, HPP_LANG=None, SHIPPING_CODE=None, SHIPPING_CO=None, BILLING_CODE=None, BILLING_CO=None, COMMENT1=None, COMMENT2=None, BATCHID=None, ECI=None, CAVV=None, XID=None, SHA1HASH=None):
	# def success(self, **kwargs):
		# try:
			# data = http.request.httprequest.data
			# headers = http.request.httprequest.headers
			
			# get form post data
			# form = http.request.httprequest.args
			# _logger.debug("form data; " +str(form))
			# docid = form['COMMENT2']
			# _logger.debug("docid is: " + str(docid))
			# document = http.request.env['sale.order'].sudo().search([('x_order_uid','=',docid)])
			
			# realex_settings = http.request.env['custom_payments.realex'].sudo().browse(1)
			#check response hash
			# sha1 = form['TIMESTAMP'] + '.' + form['MERCHANT_ID'] + '.' + form['ORDER_ID'] + '.' + form['RESULT'] + '.' + form['MESSAGE'] + '.' + form['PASREF'] + '.' + form['AUTHCODE']
			# hash_obj = hashlib.sha1(sha1)
			# hash_string = hash_obj.hexdigest()
			# hash_string += '.' + realex_settings.secret
			# hash_obj = hashlib.sha1(hash_string)
			# sha1 = hash_obj.hexdigest()
			
			# if form['SHA1HASH'] == sha1:
				# _logger.debug("sha1 correct")
				# journal = http.request.env['account.journal'].sudo().search([('code','=','BNK3'),('name','=','Credit card')])
				# payment_method = http.request.env['account.payment.method'].sudo().search([('code','=','manual'),('payment_type','=','inbound')])
				# document.sudo().action_confirm()
				# invoice_id = document.sudo().action_invoice_create()
				# _logger.debug("created invoice: " + str(invoice_id))
				# created_invoice = http.request.env['account.invoice'].sudo().search([('id','in',invoice_id)])
				# created_invoice.signal_workflow('invoice_open')
				
				# payment_amount = Decimal(form['AMOUNT']) / 100
				# time_stamp = datetime.datetime.strptime(form['TIMESTAMP'], '%Y%m%d%H%M%S').date()
		
				# data = {
					# 'journal_id': journal.id,
					# 'communication': document.name,
					# 'payment_date': time_stamp,
					# 'partner_type': 'customer',
					# 'payment_type': 'inbound',
					# 'amount': payment_amount,
					# 'partner_id': created_invoice.partner_id.id,
					# 'invoice_ids': [(6, 0, created_invoice.ids)],
					# 'payment_difference_handling': 'open',
				# }
				# if payment_method:
					# data['payment_method_id'] = payment_method.id
				
				# payment = http.request.env['account.payment'].sudo().create(data)
				# payment._compute_destination_account_id()
				# payment.post()
				# http.request.env['custom_payments.realex.statement'].sudo().record_card_payment(payment)
				# _logger.debug("before calculating time")
				# transaction_time = datetime.datetime.strptime(form['TIMESTAMP'], '%Y%m%d%H%M%S')
				# time_string = transaction_time.strftime('%d/%m/%Y at %H:%M:%S')
				# _logger.debug("time is: " + time_string)
				
				# receipt_info = {'result': RESULT, 'message': MESSAGE, 'authcode': AUTHCODE, 'order_id': ORDER_ID, 'timestamp': time_string, 'amount': AMOUNT}
				# _logger.debug("receipt: " + str(form))
				# return "successful payment"
				# return http.local_redirect('/payment_success', {
					# 'document': document, 'receipt_info': receipt_info, 'realex': realex_settings
				# })
				# return http.request.render('translationie_realex_payment_integration.confirmation_page',{
					# 'document': document, 'receipt_info': form, 'realex': realex_settings
				# })
			# else:
				# return "SHA1 is wrong returned: " + str(SHA1HASH) + " should be: "  + sha1
		# except Exception:
			# _logger.error("error receiving hpp response", exc_info=True)

	
