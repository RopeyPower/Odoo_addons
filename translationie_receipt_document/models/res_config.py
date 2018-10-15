# -*- coding: utf-8 -*-

import logging

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class receipt_configuration(osv.TransientModel):
	_inherit = 'sale.config.settings'
	
	_columns = {
		'receipt_mail_template': fields.many2one('mail.template', "Receipt Email Template",
			help="Email template to which receipt documents should be attached"),
	}
	
	def set_receipt_template_defaults(self, cr, uid, ids, context=None):
		try:
			receipt_mail_template = self.browse(cr, uid, ids, context=context).receipt_mail_template
			res = self.pool.get('ir.values').set_default(cr, SUPERUSER_ID, 'sale.config.settings', 'receipt_mail_template', receipt_mail_template.id)
			return res
		except Exception:
			_logger.error("Error setting so tax", exc_info=True)