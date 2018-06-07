# -*- coding: utf-8 -*-

from openerp import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class translationie_project_respartner_modifications(models.Model):
	_inherit = 'res.partner'
	_name = 'res.partner'

	x_task_ids = fields.One2many(string='Tasks by x_translator_id', comodel_name='project.task', inverse_name='x_translator')
	x_task_count = fields.Integer(string='# Tasks by x_translator', compute='_compute_task_count')

	@api.multi
	def _compute_task_count(self):
		try:
			for partner in self:
				tasks = self.env['project.task'].search([('x_translator', '=', partner.id)])
				_logger.debug('tasks count: '+str(tasks))
				partner.x_task_count = len(tasks)
		except Exception as e:
			_logger.debug('Error in the _compute_task_count: ', exc_info=True)
