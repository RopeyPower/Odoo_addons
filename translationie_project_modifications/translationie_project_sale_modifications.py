# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import Warning, UserError
import datetime
import logging

_logger = logging.getLogger(__name__)

class translationie_project_sale_modifications(models.Model):
	_inherit = 'sale.order'
	_name = 'sale.order'
	
	x_project_status = fields.Char(compute="get_project_state", store=True)
	
	# invoice_ids = fields.Many2many(store=True)
	invoice_ids = fields.Many2many(search='x_search_invoices')
	
	tasks_ids = fields.Many2many(search='x_search_tasks')
	
	def x_search_invoices(self, operator, value):
		return [('name', operator, value)]
	
	def x_search_tasks(self, operator, value):
		return [('name', operator, value)]
	
	@api.multi
	@api.depends('invoice_ids.state','project_id.project_ids.task_ids.x_status')
	def get_project_state(self):
		_logger.debug("orders: " + str(self))
		for sale_order in self:
			try:
				# _logger.debug("orders: " + str(sale_order))
				# _logger.debug("entered method " + sale_order.name)
				customer_paid = self._check_invoiced(sale_order)
				# _logger.debug("analytic exists: " + str(sale_order.project_id))
				# _logger.debug("project exists: " + str(sale_order.project_id.project_ids))
				if sale_order.project_id:
					if sale_order.project_id.project_ids:
						task_statuses = self._check_tasks(sale_order)
						project_state = 'open'
						if customer_paid and task_statuses == 'close':
							project_state = 'close'
						elif task_statuses == 'pending' or task_statuses == 'close' and not customer_paid:
							project_state = 'pending'
						elif task_statuses == 'new':
							project_state = 'draft'

						# write project state on all linked projects that are not in state=cancelled
						for active_project in [project for project in sale_order.project_id.project_ids if project.state != 'cancelled']:
							active_project.write({'state':project_state})
						# Invalidate sale_order cache otherwise it causes it to recompute the x_paid field for some reason and something weird happens with the cache where it seems to use 
						# the sale.order cache while recomputing a field on project.task which causes a KeyError for the sale order id e.g. when get_project_state is triggered on sale.order(420,)
						# you end up with KeyError 420 when recompute in models.py is called for project.task.x_paid
							# sale_order.invalidate_cache()
							# _logger.debug("cache invalidated")
						sale_order.x_project_status = project_state
			except Exception:
				_logger.error("error setting project state", exc_info=True)

				
	@api.multi
	def _check_invoiced(self, sale_order):
		customer_paid = False
		if sale_order.invoice_status == 'invoiced' or sale_order.invoice_status == 'upselling':
				if any(x.state == 'paid' for x in sale_order.invoice_ids):
					customer_paid = True
		return customer_paid
		
	@api.multi
	def _check_tasks(self, sale_order):
		task_statuses = 'other'
		for project in sale_order.project_id.project_ids:
			if len(project.task_ids) != 0:
				if all(x.x_status == 'close' for x in project.task_ids):
					task_statuses = 'close'
				elif all(x.x_status in ['close','complete'] for x in project.task_ids):
					task_statuses = 'pending'
			else:
				task_statuses = 'new'
		return task_statuses
	
			