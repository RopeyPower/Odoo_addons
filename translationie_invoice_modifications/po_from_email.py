# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import re
import logging
from decimal import Decimal
import datetime

_logger = logging.getLogger(__name__)

class quote_from_mail(models.Model):
	_inherit = 'account.invoice'
	_name = 'account.invoice'
	
	def parse_html_table(self, emailBody):
		tables = emailBody.split('<table>')
		#tables = re.findall("<table>(.+?)<\/td>", emailBody
		
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
	def message_new(self, msg_dict, custom_values=None):
		try:
			data = {}
			if isinstance(custom_values, dict):
				data = custom_values.copy()
			model = self._context.get('thread_model') or self._name
			RecordModel = self.env[model]
			fields = RecordModel.fields_get()
			name_field = RecordModel._rec_name or 'name'
			#if name_field in fields and not data.get('name'):
			#	data[name_field] = msg_dict.get('subject', '')
			
			project = self.env['project.project'].search([('name','=ilike',msg_dict.get('subject',''))])
			
			
			emailBody = msg_dict.get('body', '')
			po_lines = self.parse_html_table(emailBody)
			po_account = self.env['account.account'].search([('code','=','111100'),('name','=','Account Payable')])
			po_journal = self.env['account.journal'].search([('type','=','purchase'),('code','=','BILL')])
			
			for line in po_lines:
				translator = self.env['res.partner'].search([('email','=',line[1]),('supplier','=',True)])
				if not translator and line[1] != '_':
					translator = self.env['res.partner'].search([('email','ilike',line[1]),('supplier','=',True)])
				#_logger.debug("Email is " + str(line[1]) + " translator is " + str(translator.name))
				if translator:
					task =  project.tasks.search([('name','=ilike',line[0]),('partner_id','=',translator.id)])
					
					data[name_field] = line[0]
					data['origin'] = project.name
					

					data['partner_id'] = translator.id
					_logger.debug("Partner_id is: " + str(translator) + " email is: " + line[1])
					
					data['type'] = 'in_invoice'
					
					data['account_id'] = po_account.id
					
					data['journal_id'] = po_journal.id
					
					if line[4]:
						data['date_invoice'] = datetime.datetime.strptime(line[4], '%d/%m/%Y')
						data['number'] = 'BILL/' + str(data['date_invoice'].year) + '/' + project.name
					
					existing_invoice = self.env['account.invoice'].search([('name','=',data[name_field]),('partner_id','=',translator.id)])
					
					if not existing_invoice:
						res_id = RecordModel.create(data)
					else:
						_logger.debug("Invoice already exists")
						res_id = False
					
					
					
					if res_id:
						self.create_invoice_line(line, project, task, res_id)
						if task:
							task.x_purchase_order = res_id.id
			
			sale_order = self.env['sale.order'].search([('project_id','=',project.analytic_account_id.id)])
			if sale_order.invoice_status == 'to invoice':
				sale_order.action_invoice_create()
			
			#for invoice in sale_order.invoice_ids:
			#	if invoice.state == 'draft':
			#		invoice.state = 'open'
				#invoice.invoice_validate()
			
			if project.state != 'close':
				project.state = 'close'
			#self.env['sale.advance.payment.inv'].create_invoices(sale_order)
		except Exception:
			_logger.debug("Error creating PO from email", exc_info=True)
			
	def create_invoice_line(self, line, project, task, po):
		try:
			sale_order = self.env['sale.order'].search([('project_id','=',project.analytic_account_id.id)])
			order_lines = self.env['sale.order.line'].search([('order_id','=',sale_order.id),('x_source','=',task.x_source.id),('x_target','=',task.x_target.id)])
			
			so_line_ref = False
			
			#if task:
			#	for so_line in order_lines:
			#		if 'Translation' in task.name and 'Translation' in so_line.name:
			#			so_line_ref = so_line
			#		elif 'Review' or 'Proofread' in task.name and 'Review' or ' Proofread' in so_line.name:
			#			so_line_ref = so_line
					
			product = self.env['product.product'].search([('name','=ilike','Translator Fee')])
			line_account = self.env['account.account'].search([('code','=','220000'),('name','=','Expenses')])
			qty = line[2]
			unit_price = line[3]
			
			
			data = {
				'account_id':line_account.id,
				'product_id':product.id,
				'name':product.name,
				'quantity':qty,
				'price_unit':unit_price,
				'invoice_id':po.id,
				'account_analytic_id':project.analytic_account_id.id,
				'x_source':task.x_source.id,
				'x_target':task.x_target.id,
				'uom_id':product.uom_id.id,
			}

			
			#if so_line_ref:
			#	data['sale_line_ids'] = [(4,so_line_ref.id)]
			
			po = self.env['account.invoice.line'].create(data)
			
			return po
		except Exception:
			_logger.debug("Error creating po line", exc_info=True)