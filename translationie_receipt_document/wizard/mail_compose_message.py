# -*- coding: utf-8 -*-
from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
import logging

_logger = logging.getLogger(__name__)

class MailComposer(models.TransientModel):
	_inherit = 'mail.compose.message'

	@api.multi
	def onchange_template_id(self, template_id, composition_mode, model, res_id):
		try:
			values = super(MailComposer, self).onchange_template_id(template_id, composition_mode, model, res_id)
			_logger.debug("mail values: " + str(values))
			#check if mail template is the receipt mail template
			ir_values = self.env['ir.values']
			receipt_template = ir_values.get_default('sale.config.settings', 'receipt_mail_template')
			_logger.debug("Receipt template: " + str(receipt_template) + " template: " + str(template_id))
			if template_id == receipt_template and model == 'sale.order':
				#if it is the receipt template we have to attach the receipts from the Sale Order payment to the email.
				_logger.debug("Template is Receipt Template")
				_logger.debug("res_id:" + str(res_id))
				res = self.env[model].browse(res_id)
				attachment_list = [id for id in res.x_receipt_attachments.ids]
				_logger.debug("attachment_list: " + str(attachment_list))
				values['value']['attachment_ids'] = [(5,), (6, 0, attachment_list)]
				_logger.debug("new values: " + str(values))
			return values
		except Exception:
			_loger.error("Error composing mail", exc_info=True)