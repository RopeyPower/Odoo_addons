# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import Warning, UserError
import datetime
import logging

_logger = logging.getLogger(__name__)

class multipleStatusWizard(models.TransientModel):
	_name = "project.task.status.wizard"
	
	@api.multi
	def mark_complete_multiple(self):
		try:
			tasks = self.env['project.task'].browse(self._context.get('active_ids', []))
			for task in tasks:
				if  task.x_status == 'open':
					task.write({'x_completed':True, 'x_status':'complete'})
					if not task.x_purchase_order.exists():
						task._create_po(task)
		except Exception:
			_logger.error("error marking multiple tasks complete", exc_info=True)