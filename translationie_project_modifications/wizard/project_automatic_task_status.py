# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import Warning, UserError
import datetime
import logging

_logger = logging.getLogger(__name__)

class autoTaskStatus(models.TransientModel):
	_name = 'project.auto.task.state'
	
	@api.multi
	def automatic_set_task_state(self):
		_logger.debug("setting task states for projects: " + str(self))
		try:
			projects = self.env['project.project'].browse(self._context.get('active_ids', []))
			task_status_sequence = {'none':0,'draft':1,'open':2,'complete':3,'close':4}
			for project in projects:
				old_project_state = project.state
				for task in project.task_ids:
					if task.x_status:
						old_sequence = task_status_sequence[task.x_status]
					else:
						old_sequence = 0
					
					if task.x_translator != False and old_project_state == 'close':
						if task.x_purchase_order and task.x_purchase_order.state == 'paid':
							new_status = 'close'
						else:
							new_status = 'complete'
						task.x_completed = True
					elif task.x_translator != False:
						new_status = 'open'
					else:
						new_status = 'draft'
						
					new_sequence = task_status_sequence[new_status]
					_logger.debug("new status is: " + new_status)
					if new_sequence > old_sequence:
						_logger.debug("writing new status: " + new_status)
						task.x_status = new_status
		except Exception:
			_logger.error("error setting task automatically", exc_info=True)