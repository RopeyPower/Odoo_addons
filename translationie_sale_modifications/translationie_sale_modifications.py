# -*- coding: utf-8 -*-

from openerp import models, fields, api
import datetime
import logging

_logger = logging.getLogger(__name__)

class translatioie_saleorder_line_modifications(models.Model):
	_inherit = 'sale.order.line'
	_name = 'sale.order.line'
	
	x_source = fields.Many2one(comodel_name='x_res.languages', string='Source', ondelete='set null')
	x_target = fields.Many2one(comodel_name='x_res.languages', string='Target', ondelete='set null')
	x_vat_amount = fields.Monetary(string='VAT Amount', compute='compute_vat_numerical_amnt', ondelete='set null')
	
	def compute_vat_numerical_amnt(self):
		for line in self:
			if line.tax_id:
				tax_percent = line.tax_id.amount / 100
				tax_amount = line.price_subtotal * tax_percent
				line.x_vat_amount = format(tax_amount, '.2f')
				
		
	@api.multi
	def _prepare_invoice_line(self, qty):
		res = super(translatioie_saleorder_line_modifications, self)._prepare_invoice_line(qty)
		res['x_source'] = self.x_source.id
		res['x_target'] = self.x_target.id
		
		return res


class translation_saleorder_modifications(models.Model):
	_inherit = 'sale.order'
	_name = 'sale.order'
	
	x_project = fields.Many2one(comodel_name='project.project', string='Project', ondelete='set null')
	x_missing_lang = fields.Text(string='Missing Language', ondelete='set null')
	x_languages_fragment = fields.Text(string='Languages', readonly=False)
	x_timeframe_fragment = fields.Text(string='Time Frame', default='2 - 3 working days', readonly=False)
	x_biz_service = fields.Char(string='Service', default='Translation, Editing, Proofreading and Certifying')
	x_biz_word_count = fields.Char(string='Word Count')
	x_biz_content_type = fields.Char(string='Content Type')
	x_biz_source_format = fields.Char(string='Source File Format', default='PDF')
	x_biz_target_format = fields.Char(string='Target File Format', default='WORD, PDF')
	x_total_translation_cost_untaxed = fields.Monetary(string='Untaxed Translation Cost', compute='sale_compute_translation_cost_untaxed', ondelete='set null')
	x_po_ids = fields.Many2many("account.invoice", string="Purchase Orders", compute="_get_pos", readonly="true", copy=False)
	x_po_count = fields.Integer(string='# of pos', compute="_get_pos", readonly=True)
	
	x_timeframe_days = fields.Integer(string='Projected Number of Days', default=3)
	x_start_date = fields.Datetime(string='Start Date')
	x_due_date = fields.Datetime(string='Due Date',compute='_calc_due_date', store=True)
	
	x_source_id = fields.Many2one('x_res.languages', related='order_line.x_source', string="Source Language")
	x_target_id = fields.Many2one('x_res.languages', related='order_line.x_target', string="target Language")
		
	# Overload to add a search field
	amount_total = fields.Monetary(search='x_search_amount_total')
	

	def x_search_amount_total(self, operator, value):
		if operator == 'like':
			operator = 'ilike'
		return [('name', operator, value)]

	@api.multi
	def action_view_task(self):
		try:
			result = super(translation_saleorder_modifications, self).action_view_task()
			_logger.debug("give me the fucking tasks")
			result['context'] = {'search_default_project':1}
			_logger.debug("result is: " + str(result))
			return result
		except Exception:
			_logger.error("Somethings fucking broken", exc_info=True)
	
	def sale_compute_translation_cost_untaxed(self):
		for sale_order in self:
			postage_cost = 0
			for line in sale_order.order_line:
				if 'Postage' in line.product_id.name:
					postage_cost += line.price_unit * line.product_uom_qty
			
			sale_order.x_total_translation_cost_untaxed = sale_order.amount_untaxed - postage_cost
	
	def x_get_languages(self):
		sources = []
		targets = []
		for sale_order in self:
			for line in sale_order.order_lines:
				if line.x_source:
					sources.append(line.x_source.name)
				if line.x_target:
					targets.append(line.x_target.name)
	
	@api.depends('x_start_date','x_timeframe_days')
	def _calc_due_date(self):
		try:
			for sale_order in self:
				projected_days = sale_order.x_timeframe_days
				time_delta = datetime.timedelta(days=projected_days)
				start_date = fields.Datetime.from_string(sale_order.x_start_date)
				if start_date:
					due_date = start_date + time_delta
					_logger.debug("date is: " + str(due_date))
					
					
					for project in sale_order.project_id.project_ids:
						project_deadline = fields.Datetime.from_string(project.x_project_deadline)
						if project_deadline != due_date:
							project.write({'x_project_deadline':due_date})
						# _logger.debug("Method project deadline: " + str(project.x_project_deadline))
					sale_order.x_due_date = due_date
		except Exception:
			_logger.error("Error setting due date", exc_info=True)
	
	@api.multi
	def action_confirm(self):
		super(translation_saleorder_modifications, self).action_confirm()
		for order in self:
			try:
				if order.x_start_date == False:
					order.x_start_date = fields.Datetime.now()
			except Exception:
				_logger.error("error setting start date", exc_info=True)
		return True
	
	@api.multi
	def _get_pos(self):
		for order in self:
			try:
				invoice_lines = self.env['account.invoice.line'].search([('account_analytic_id', '=', order.project_id.id)])
				unique_po_ids = list(set([line.invoice_id.id for line in invoice_lines if line.invoice_id.type == 'in_invoice' or line.invoice_id.type == 'in_refund']))
				_logger.debug("po list is: " + str(unique_po_ids))
				po_ids = self.env['account.invoice'].search([('id', 'in', unique_po_ids)])

				order.x_po_ids = po_ids
				order.x_po_count = len(po_ids)
			except Exception:
				_logger.debug("error getting pos", exc_info=True)
	
	@api.multi
	def action_view_pos(self):
		try:
			po_ids = self.mapped('x_po_ids')
			_logger.debug("no of pos: " + str(len(po_ids)))
			imd = self.env['ir.model.data']
			action = imd.xmlid_to_object('account.action_invoice_tree2')
			list_view_id = imd.xmlid_to_res_id('account.invoice_supplier_tree')
			form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
			
			result = {
				'name': action.name,
				'help': action.help,
				'type': action.type,
				'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
				'target': action.target,
				'context': action.context,
				'res_model': action.res_model,
			}
			
			if len(po_ids) > 1:
				result['domain'] = "[('id','in',%s)]" % po_ids.ids
			elif len(po_ids) == 1:
				result['views'] = [(form_view_id, 'form')]
				result['res_id'] = po_ids.ids[0]
			else:
				result = {'type': 'ir.actions.act_window_close'}
			_logger.debug("result is: " + str(result))
			return result
		except Exception:
			_logger.debug("error viewing pos", exc_info=True)
		
	
	@api.depends('state', 'order_line.invoice_status')
	def _get_invoiced(self):
		super(translation_saleorder_modifications, self)._get_invoiced()
		for order in self:
			try:
				invoice_ids = order.invoice_ids
				refund_ids = invoice_ids.search([('type','=','out_refund'),('origin','in', invoice_ids.mapped('number')), ('origin','!=',False)])
				_logger.debug("untouched invoices are: " + str(invoice_ids))
				invoice_ids = invoice_ids.search([('origin', 'like', order.name),('type','=','out_invoice')])
				_logger.debug("invoices: " +str(invoice_ids) + " refunds are: " + str(refund_ids))
				
				invoice_ids += refund_ids
				
				# order.update({
					# 'invoice_ids': invoice_ids.ids
				# })
				order.invoice_ids = invoice_ids
				order.invoice_count = len(invoice_ids)
				# invoice_ids = order.order_line.mapped('invoice_lines').mapped('invoice_id')
				_logger.debug("new invoices are: " + str(order.invoice_ids) + " should be " + str(invoice_ids) + " count is " + str(order.invoice_count))
			except Exception:
				_logger.error("error collating invoices", exc_info=True)
			
	
	@api.multi
	@api.depends('order_line.product_id.project_id','project_id.project_ids.task_ids')
	def _compute_tasks_ids(self):
		super(translation_saleorder_modifications, self)._compute_tasks_ids()
		for order in self:
			_logger.debug("getting tasks: " + str(order))
			task_list = order.project_id.project_ids.task_ids
			order.tasks_ids = task_list
			order.tasks_count = len(order.tasks_ids)
			_logger.debug("task list: " + str(task_list) + " count: " + str(order.tasks_count))

		
class translationie_sale_service_modifications(models.Model):
	_inherit = 'procurement.order'
	_name = 'procurement.order'
	
	def _create_service_task(self, cr, uid, procurement, context=None):
		translation_task_id = super(translationie_sale_service_modifications, self)._create_service_task(cr, uid, procurement, context=context)
		#proofread_task_id = super(translationie_sale_service_modifications, self)._create_service_task(cr, uid, procurement, context=context)
		
		project_task = self.pool['project.task']
		task = project_task.browse(cr, uid, translation_task_id, context=context)
		if 'Translation' in procurement.product_id.name:
			task_marker = 'Translation'
		else:
			task_marker = 'Proofread'
		task_name = '%s - %s: %s to %s' % (procurement.origin or '', task_marker, procurement.sale_line_id.x_source.x_name, procurement.sale_line_id.x_target.x_name)
		#task_name = "{0}:{1} {2} - {3}".format(procurement.origin or '',
		task.write({'x_source':procurement.sale_line_id.x_source.id,'x_target':procurement.sale_line_id.x_target.id,'name':task_name})
		
		return translation_task_id
		

