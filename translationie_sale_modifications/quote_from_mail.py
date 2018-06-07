# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import re
import logging
from decimal import Decimal
import datetime

_logger = logging.getLogger(__name__)

class quote_from_mail(models.Model):
	_inherit = 'sale.order'
	_name = 'sale.order'
	
		
	def parse_email(self, emailBody):
		#List of fields parse_email will look for when parsing email body
		emailFields=['Name','Phone','Email','Job','Translation_Rate_Group','Quantity','From','To','Pm','Comments','Date']
		dict={}
		emailBody = emailBody
		for line in emailBody.split('</p>'):
			for field in emailFields:
				if field in line.strip():
					split_line = line.split(':', 1)
					if len(split_line)>1:
						dict[field]=split_line[1].strip()

		return dict
		
	def parse_html_table(self, emailBody):
		tables = emailBody.split('<table>')
		
		rows = tables[1].split('</tr>')
		
		_logger.debug('row1 is: ' + rows[0] + ' row2 is: ' + rows[1])
		
		row_tds = []
		
		for row in rows:
			tds = re.findall("<td>(.+?)<\/td>", row)
			if len(tds) > 0:
				row_tds.append(tds)
		#tds = re.findall("<td>(.+?)<\/td>", tables[1])
		#for td in tds.groups():
		_logger.debug("td is: " + str(row_tds))
		
		return row_tds
		
	@api.model
	def create_order_lines(self, res_id, dict, source_lang, target_lang):
		order_line_obj = self.env['sale.order.line']
		product_obj = self.env['product.product']
		
		tax_obj = self.env['account.tax']
		sale_tax = tax_obj.search([('type_tax_use','=ilike','sale'),('amount','=',23.0000)])
		#product_tax = tax_obj.browse(sale_tax)

		translation_product = product_obj.search([('name','ilike',dict.get('Translation_Rate_Group'))], limit=1)
		proofread_product = product_obj.search([('name','=like','Proofread')])
		pm_product = product_obj.search([('name','=like','Project Management')])
		#postage_products = product_obj.search(cr,uid,[('name','=like','Postage')])
		
		#translation_product = None
		#proofread_product = None
		#pm_product = None
		#postage_product = None
		
		#if translation_products:
		#	translation_product = product_obj.browse(translation_products)
		
		#if proofread_products:
		#	proofread_product = product_obj.browse(proofread_products)
		
		#if pm_products:
		#	pm_product = product_obj.browse(pm_products)
		
		#if postage_products:
			#postage_product = product_obj.browse(cr,uid,postage_products,context=context)
		if len(sale_tax) > 1:
			sale_tax = sale_tax[0]
		
		if translation_product:
			translation_order_line = order_line_obj.create({'product_id':translation_product.id,'name':translation_product.name,'product_uom_qty':dict.get('Quantity'),'price_unit':translation_product.list_price,'order_id':res_id.id,'tax_id':[(4,sale_tax.id)],'x_source':source_lang.id,'x_target':target_lang.id})
		
		if proofread_product and target_lang.x_name != 'English':
			proofread_order_line = order_line_obj.create({'product_id':proofread_product.id,'name':proofread_product.name,'product_uom_qty':dict.get('Quantity'),'price_unit':proofread_product.list_price,'order_id':res_id.id,'tax_id':[(4,sale_tax.id)],'x_source':source_lang.id,'x_target':target_lang.id})
		
		if pm_product:
			pm_order_line = order_line_obj.create({'product_id':pm_product.id,'name':pm_product.name,'product_uom_qty':1,'price_unit':pm_product.list_price,'order_id':res_id.id,'tax_id':[(4,sale_tax.id)]})
		
		#if postage_product:
			#postage_order_line = order_line_obj.create(cr,uid,{'product_id':postage_product.id,'name':postage_product.name,'product_uom_qty':1,'price_unit':postage_product.list_price,'order_id':res_id},context=context)
	
	@api.model
	def message_new(self, msg_dict, custom_values=None):
		try:
			data = {}
			if isinstance(custom_values, dict):
				data = custom_values.copy()
			model = self._context.get('thread_model') or self._name
			#model_pool = self.env[model]
			#fields = model_pool.fields_get(cr, uid, context=context)
			#if 'name' in fields and not data.get('name'):
			#	data['name'] = msg_dict.get('subject', '')
			RecordModel = self.env[model]
			fields = RecordModel.fields_get()
			name_field = RecordModel._rec_name or 'name'
			if name_field in fields and not data.get('name'):
				data[name_field] = msg_dict.get('subject', '')
			
			#so_obj = self.env['sale.order']
			
			emailBody = msg_dict.get('body', '')
			_dict = self.parse_email(emailBody)
			
			customer_name = _dict.get('Name')
			customer_email = _dict.get('Email')
			
			customer = self.check_customer(customer_email, customer_name, _dict.get('Phone'))
			
			#partner = self.env['res.partner']
			#customers = partner.search([('email','=ilike',customer_email)])
				
			#if not len(customers) > 0 or "@" not in customer_email:
			#	account_obj = self.env['account.account']
			#	debtor_acc = account_obj.search([('code','=like','101200')])
			#	creditor_acc = account_obj.search([('code','=like','111100')])
			#	
			#	customer = partner.create({'name':customer_name,'customer':True,'supplier':False,'notify_email':'none','email':customer_email,'property_account_payable_id':creditor_acc[0],'property_account_receivable_id':debtor_acc[0],'phone':_dict.get('Phone'),'is_company':False})
			#else:
			#	customer = customers[0]
				
			data['partner_id'] = customer.id
			data['partner_invoice_id'] = customer.id
			data['partner_shipping_id'] = customer.id
				
			project_obj = self.env['project.project']
			
			lang_dict = self.get_language(_dict)
			
			#lang_obj = self.env['x_res.languages']
			
			#lang_from = lang_obj.search([('x_name','=ilike',_dict.get('From'))])
			#lang_to = lang_obj.search([('x_name','=ilike',_dict.get('To'))])
			
			#lang_missing_desc = ""
				
			#if not lang_from:
			#	lang_from = lang_obj.browse(1)
			#	lang_missing_desc = _dict.get('From')
			#else:
			#	lang_from = lang_obj.browse(lang_from[0])
			#if not lang_to:
			#	lang_to = lang_obj.browse(1)
			#	lang_missing_desc += " to " + _dict.get('To')
			#else:
			#	lang_to = lang_obj.browse(lang_to[0])
			#if lang_missing_desc:
			#	data['x_missing_lang'] = 'languages may not have been added correctly: ' + lang_missing_desc
			
			project_manager = self.env['res.users'].search([('email','ilike',_dict.get('Pm'))])
			
			if not project_manager:
				project_manager = self.env['res.users'].browse(self.env.uid)
				
			quote_project = project_obj.create({'partner_id':customer.id,'user_id':project_manager.id,'name':_dict.get('Job'),'use_tasks':True,'use_timesheets':False,'x_description':_dict.get('Comments')})
				
			#quote_project_obj = project_obj.browse(quote_project)
			quote_analytic_acc = quote_project.analytic_account_id
				
			data['project_id'] = quote_analytic_acc.id
			data['user_id'] = project_manager.id
			
			_logger.debug("Raw Date is: " + str(_dict.get('Date')))
			if _dict.get('Date'):
				order_date = datetime.datetime.strptime(_dict.get('Date'), '%Y-%m-%d %H:%M:%S')
				data['date_order'] = order_date
				_logger.debug("order_date is: " + str(order_date))
			
			
			res_id = RecordModel.create(data)
			_logger.debug("res_id is: " + str(res_id))
			
			if res_id:
				if '<table>' in emailBody:
					line_info = self.parse_html_table(emailBody)
					quantity = self.calculate_quantity(line_info)
					self.copy_order_lines(line_info, res_id)
					res_id.write({'state':'sale'})
				else:
					self.create_order_lines(res_id, _dict, lang_dict['From'], lang_dict['To'])
					quantity = _dict.get('Quantity')
				
				
				#set quotation variables
				#this_so = self.browse(res_id)
				if lang_dict:
					lang_sentence = '{} to {}'.format(lang_dict['From'].x_name, lang_dict['To'].x_name)
				else:
					lang_sentence = ''
					
				
				
				
				quantity_sentence = self.set_quantity_sentence(quantity)
				
				
				res_id.write({'x_languages_fragment':lang_sentence,'x_biz_word_count':quantity_sentence})
				
			
			return res_id.id
		except Exception:
			_logger.debug("Error creating Quote", exc_info=True)
	
	def create_project(self, customer, pm, _dict, line_info=None):
		data = {
			'partner_id':customer.id,
			'user_id':pm.id,
			'name':_dict.get('Job'),
			'use_tasks':True,
			'use_timesheets':False,
			'x_description':_dict.get('Comments')
		}
		
		project = self.env['project.project'].create(data)
		
		return project
				
	
	def calculate_quantity(self, line_info):
		quantity = 0
		for line in line_info:
			quantity += Decimal(line[1])
		return quantity
	
	def get_language(self, dict):
		if dict.get('From') and dict.get('To'):
			lang_obj = self.env['x_res.languages']
			
			lang_from = lang_obj.search([('x_name','=ilike',dict.get('From'))])
			lang_to = lang_obj.search([('x_name','=ilike',dict.get('To'))])
			return {'From':lang_from, 'To':lang_to}
	
	def set_quantity_sentence(self, quantity):
		try:
			quantity = int(quantity)
		except ValueError:
			quantity = 0
		
		if quantity > 300:
			quantity_sentence = quantity
		else:
			quantity_sentence = 'Minimum Translation'
		
		return quantity_sentence
	
	def check_customer(self, email, name, phone):
		partner = self.env['res.partner']
		customers = partner.search([('email','=ilike',email)])
		
		if not len(customers) > 0 or "@" not in email:
			customer = self.create_customer(email, name, phone)
		else:
			customer = customers[0]
		
		return customer
		
	def create_customer(self, email, name, phone, context={}):
		account_obj = self.env['account.account']
		debtor_acc = account_obj.search([('code','=like','101200')])
		creditor_acc = account_obj.search([('code','=like','111100')])
		
		data = {
			'name':name,
			'customer':True,
			'supplier':False,
			'notify_email':'none',
			'email':email,
			'phone':phone,
			'property_account_payable_id':creditor_acc[0],
			'property_account_receivable_id':debtor_acc[0],
			'is_company':False,
		}
		
		customer = self.env['res.partner'].create(data)
		return customer
		
		
	def copy_order_lines(self, line_info, res_id):
		task_count = 0
		for line in line_info:
			#get product
			product = self.env['product.product'].search([('name','=ilike',line[0])])
			_logger.debug("product should be " + line[0] + " product is " + str(product))
			quantity = line[1]
			lang_from = self.env['x_res.languages'].search([('x_name','=like',line[3])])
			lang_to = self.env['x_res.languages'].search([('x_name','=like',line[4])])
			
			unit_price = Decimal(line[2])
			



			data = {
				'product_id':product.id,
				'name':product.name,
				'x_source':lang_from.id,
				'x_target':lang_to.id,
				'product_uom_qty':quantity,
				'price_unit':unit_price,
				'order_id':res_id.id,
				
			}
			
			if "VAT 23.00%" in line[5]:
				sale_tax = self.env['account.tax'].search([('type_tax_use','=ilike','sale'),('amount','=',23.0000)])
				data['tax_id'] = [(4,sale_tax.id)]

				
			order_line = self.env['sale.order.line'].create(data)
			_logger.debug("product type is: " + str(product.type))
			if product.type == 'service':
				if len(line) == 7:
					translator = self.env['res.partner'].search([('email','=',line[6])])
				else:
					translator = None
				task = self.create_order_line_task(product, order_line, res_id.project_id.project_ids, translator)
				task_count = task_count + 1
				_logger.debug("task count is: " + str(task_count))
				res_id.write({'tasks_ids':[(4,task.id)]})
			res_id.write({'tasks_count':task_count})
			_logger.debug("tasks_count is:" + str(res_id.tasks_count))
			
	def create_order_line_task(self, product, order_line, project, translator):
		try:
			if 'Translation' in product.name:
				task_marker = 'Translation'
			else:
				task_marker = 'Proofread'
			
			task_name = '%s - %s: %s to %s' % (project.name or '', task_marker, order_line.x_source.x_name, order_line.x_target.x_name)
			
			_logger.debug("project is: " + project.name)
			
			data = {
				'name': task_name,
				'x_source': order_line.x_source.id,
				'x_target': order_line.x_target.id,
				'partner_id': project.partner_id.id,
				'sale_line_id': order_line.id,
				'planned_hours': order_line.product_uom_qty,
				'x_words': order_line.product_uom_qty,
				'project_id': project.id
			}
			
			if translator:
				if len(translator) > 1:
					data['x_translator'] = translator[0].id
				else:
					data['x_translator'] = translator.id
			
			task = self.env['project.task'].create(data)
			return task
		except Exception:
			_logger.debug("Error creating task", exc_info=True)
