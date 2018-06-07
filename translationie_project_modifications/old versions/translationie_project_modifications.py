# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import Warning, UserError
import datetime
import logging

_logger = logging.getLogger(__name__)

class translationie_project_modifications(models.Model):
#     _name = 'translationie_project_modifications.translationie_project_modifications'
	_inherit = 'project.project'
	_name = 'project.project'
#     name = fields.Char()
	x_comment = fields.Text(string='Comment')
	x_description = fields.Text(string='Description')
	x_translators = fields.Many2many(comodel_name='res.partner', compute='update_project_translators' ,string='Translators', ondelete='set null', domain=[('supplier','=',True)])
	x_reviewers = fields.Many2many(comodel_name='res.partner', compute='update_project_translators', string='Reviewers', ondelete='set null', domain=[('supplier','=',True)])
	x_translators_deadline = fields.Text(string='Translators Deadlines', compute='update_project_translator_deadlines')
	x_reviewers_deadline = fields.Text(string='Reviewers Deadlines', compute='update_project_translator_deadlines')
	x_source_langs = fields.Many2many(comodel_name='x_res.languages', compute='update_source_langs', string='Source Languages', ondelete='set null')
	x_target_langs = fields.Many2many(comodel_name='x_res.languages', compute='update_target_langs', string='Target Languages', ondelete='set null')
	x_project_deadline = fields.Datetime(string='Project Deadline')
	
	state = fields.Selection(default='draft')
	
	def update_source_langs(self):
		for project in self:
			for task in project.tasks:
				if task.x_source:
					project.x_source_langs = [(4,task.x_source.id)]
	
	def update_target_langs(self):
		for project in self:
			for task in project.tasks:
				if task.x_target:
					project.x_target_langs = [(4,task.x_target.id)]
	
	def update_project_translators(self):
		for project in self:
			for task in project.tasks:
				if "Translation" in task.name:
					if task.x_translator not in project.x_translators:
						project.x_translators = [(4,task.x_translator.id)]
				else:
					if task.x_translator not in project.x_reviewers:
						project.x_reviewers = [(4,task.x_translator.id)]
					
	def update_project_translator_deadlines(self):
		for project in self:
			translator_deadlines = ' '
			reviewer_deadlines = ' '
			for task in project.tasks:
				if task.x_translator:
					initials = project.get_initials(task.x_translator.name)
					initials_timestamp = project.concat_initials(initials, task.date_deadline)
					if "Translation" in task.name:
						translator_deadlines += initials_timestamp + '\n'
					else:
						reviewer_deadlines += initials_timestamp + '\n'
			project.x_translators_deadline = translator_deadlines
			project.x_reviewers_deadline = reviewer_deadlines
	
	def button_close_project(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
			
		project = self.browse(cr, uid, ids[0], context=context)
		
		sale_order_id = self.pool['sale.order'].search(cr,uid,[('project_id','=',project.analytic_account_id.id)],context=context)
		
		project.write({'state':'close'})
		
		return {'type':'ir.actions.act_window','res_model':'sale.order','views':[[False,'form']],'res_id':sale_order_id[0],'target':'current','flags':{'action_buttons':True},}
		

	@api.multi
	def button_cancel_project(self):
		for project in self:
			project.state = 'cancelled'
	
	@api.multi
	def button_reopen_project(self):
		for project in self:
			project.state = 'draft'

	def button_view_so(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		
		project = self.browse(cr, uid, ids[0], context=context)
		
		sale_order_id = self.pool['sale.order'].search(cr,uid,[('project_id','=',project.analytic_account_id.id)],context=context)
		
		return {'type':'ir.actions.act_window','res_model':'sale.order','views':[[False,'form']],'res_id':sale_order_id[0],'target':'current','flags':{'action_buttons':True},}
	
	def get_initials(self, name):
		name_parts = name.split()
		initials = ''
		for part in name_parts:
			initials += part[0].upper()
		return initials
			
	def concat_initials(self, initials, timestamp):
		deadline = ''
		if timestamp:
			deadline = initials + ' ' + str(timestamp)
		else:
			deadline = initials
		return deadline
	
	def set_done(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {'state': 'close'}, context=context)
		sale_orders = self.pool['sale.order'].search(cr,uid,[('x_project','=',ids[0])])
		return {'type':'ir.actions.act_window','res_model':'sale.order','views':[[False,'form']],'res_id':sale_orders[0],'target':'self','flags':{'action_buttons':True},}

class translationie_project_task_modifications(models.Model):
	_inherit = 'project.task'
	_name = 'project.task'
	
	x_purchase_order = fields.Many2one(comodel_name='account.invoice', string='Purchase Order', ondelete='set null')
	x_translator = fields.Many2one(comodel_name='res.partner', string='Translator', ondelete='set null')
	x_source = fields.Many2one(comodel_name='x_res.languages', string='Source', ondelete='set null')
	x_target = fields.Many2one(comodel_name='x_res.languages', string='Target', ondelete='set null')
	x_product = fields.Many2one(comodel_name='product.product', string='Product', ondelete='set null')
	x_words = fields.Integer(string='Words', ondelete='set null')
		
	#x_project_status = fields.Selection(related='project_id.state', string="Project Status")
	user_id =  fields.Many2one(compute='_assign_user')

	def _assign_user(self):
		project = self.env['project.project'].browse(project_id)
		user_id = project.user_id
	
	@api.multi
	def button_fix_bank_account(self):
		task = self
		if task.x_purchase_order:
			po = task.x_purchase_order
			if not po.partner_bank_id:
				partner_bank = po.partner_id.bank_ids[0]
				po.partner_bank_id = partner_bank.id
	
	@api.multi
	def button_create_po(self):
		task = self
		
		#raise Warning(" po is : " + str(task.x_purchase_order.name))
		if task.x_purchase_order.exists():
			_logger.debug("trying to open: " + str(task.x_purchase_order.id))
			return {'type':'ir.actions.act_window','res_model':'account.invoice','views':[[False,'form']],'res_id':task.x_purchase_order.id,'target':'current','flags':{'action_buttons':True},}
		else:
			
			if task.sale_line_id.product_id:
				task_product = task.sale_line_id.product_id
			else:
				task_product = self.env['product.product'].search([('name','=','Translator Fee')])
			
			task_product_qty = 1
			
			rate_per_word = task_product.list_price
			
			if task.x_words:
				task_product_qty = task.x_words
			else:
				task_product_qty = task.planned_hours
			
			
			if not task.x_translator:
				raise Warning('You must assign a translator before creating a purchase order')
			else:
				task_translator = task.x_translator
				rate_per_word = task_translator.x_rate_per_word
			
			if 'Translation' in task_product.name:
				task_marker = 'TR'
			else:
				task_marker = 'PR'
			
			if task_product_qty <= 300:
				if 'Group 1' in 'translation Group 1':
					rate_per_word = 10
				elif 'Group 2' in task_product.name:
					rate_per_word = 12
				elif 'Group 3' in task_product.name:
					rate_per_word = 15
				task_product_qty = 1

			
			
			
			project = task.project_id
			
			po_name = task.name
			
			po = self.env['account.invoice']
			
			translator_ref = project.name + ' ' + str(task.x_target.x_code).upper() + ' ' + task_marker
			
			po_journal = self.env['account.journal'].search([('type','=','purchase'),('code','=','BILL')])
			
			if not po_journal:
				raise UserError("Can't find journal 'Vendor Bills' (Short Code: BILL). Are you sure it exists?")
			
			po_account = self.env['account.account'].search([('code','=','111100'),('name','=','Account Payable')])
			
			if not po_account:
				raise UserError("Can't find account 'Account Payable' (Code: 111100). Are you sue it exists?")
			
			
			po_data = {
				'name':po_name,
				'partner_id':task_translator.id,
				'reference':translator_ref,
				'origin':task.name,
				'type':'in_invoice',
				'journal_id':po_journal.id,
				'account_id':po_account.id
			}
			
			
			translator_payment_mode = task_translator.supplier_payment_mode_id
			if translator_payment_mode:
				po_data['payment_mode_id'] = translator_payment_mode.id
				
				if translator_payment_mode.payment_method_id.code == 'sepa_credit_transfer':
					translator_bank_account = self.env['res.partner.bank'].search([('partner_id','=',task_translator.id),('acc_type','=','iban')], limit=1)
					
					if translator_bank_account:
						po_data['partner_bank_id'] = translator_bank_account.id
			
			task_po = po.create(po_data)
			
			po_line = self.env['account.invoice.line']
			
			po_line_account = self.env['account.account'].search([('code','=','220000'),('name','=','Expenses')])
			
			if not po_line_account:
				raise UserError("Can't find account 'Expenses' (Code: 22000). Are you sure it exists?")
				
			#raise Warning("task: " + str(task) + " product " + task_product.name + " qty " + str(task_product_qty) + " acc " + po_line_account.name + " rate " + str(rate_per_word) + " invoice " + task_po.name + " ana acc " + project.analytic_account_id.name + " uom " + task_product.uom_id.name)
			
			po_line_data = {
				'account_id':po_line_account.id,
				'product_id':task_product.id,
				'name':task_product.name,
				'quantity':task_product_qty,
				'price_unit':rate_per_word,
				'invoice_id':task_po.id,
				'account_analytic_id':project.analytic_account_id.id,
				'uom_id':task_product.uom_id.id
			}
				
			if task.sale_line_id:
				po_line_data['sale_line_ids'] = task.sale_line_id
			
			if task.x_source:
				po_line_data['x_source'] = task.x_source.id
			
			if task.x_target:
				po_line_data['x_target'] = task.x_target.id
			
			task_po_line = po_line.create(po_line_data)
			
			
			task.write({'x_purchase_order':task_po.id})
			
			#raise Warning("task: " + str(task))
			try:
				return {'type':'ir.actions.act_window','res_model':'account.invoice','views':[[False,'form']],'res_id':task_po.id,'target':'current','flags':{'action_buttons':True},}
			except:
				_logger.debug("error opening form", exc_info=True)
			

	